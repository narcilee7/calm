import asyncio
import json
import shutil
from pathlib import Path

import typer
import yaml
from rich.console import Console

from collectors import (CollectorRunner, D2Holehe, D3Hibp, D5Exif,
                        append_findings, load_findings)
from linker import apply_rules, build_graph, chains_from_graph
from report.diff import run_diff
from report.markdown import write_report
from report.task import run_task
from scorer import exposure_score, load_remediations, rank_remediations

app = typer.Typer(add_completion=False, help="calm：人肉攻击者视角的自我隐私审计")
console = Console()
DATA_DIR = Path(".")

KB_PATH = Path(__file__).parent / "kb" / "remediation.yaml"
EXAMPLE_PATH = Path(__file__).parent / "assets.yaml.example"


@app.callback()
def main_callback(data_dir: Path = typer.Option(Path("."), "--data-dir", help="数据目录（读 assets.yaml，写 findings.jsonl 等）")) -> None:
    global DATA_DIR
    DATA_DIR = data_dir


def _load_config() -> dict:
    path = DATA_DIR / "assets.yaml"
    if not path.exists():
        console.print(f"[red]未找到 {path}，先运行 calm init[/red]")
        raise typer.Exit(1)
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


@app.command()
def init() -> None:
    target = DATA_DIR / "assets.yaml"
    if target.exists():
        console.print(f"[yellow]{target} 已存在，保持原样[/yellow]")
        return
    shutil.copy(EXAMPLE_PATH, target)
    console.print(f"[green]已从模板创建 {target}，请填写后运行 calm scan[/green]")


@app.command()
def scan() -> None:
    config = _load_config()
    runner = CollectorRunner(config, console)
    runner.register(D2Holehe(config, console))
    runner.register(D3Hibp(config, console))
    runner.register(D5Exif(config, console))
    findings = asyncio.run(runner.run())
    added, dup = append_findings(DATA_DIR / "findings.jsonl", findings)
    console.print(f"[bold]findings.jsonl：新增 {added} 条，去重跳过 {dup} 条[/bold]")


@app.command()
def report() -> None:
    config = _load_config()
    findings = load_findings(DATA_DIR / "findings.jsonl")
    if not findings:
        console.print("[yellow]findings.jsonl 为空，先运行 calm scan[/yellow]")
        raise typer.Exit(1)
    assets = config.get("assets") or []
    links = apply_rules(assets, findings)
    graph = build_graph(assets, findings, links)
    chains = chains_from_graph(graph)
    links_by_chain = {c.id: [l for l in links
                             if l.endpoints[0] in set(c.nodes) and l.endpoints[1] in set(c.nodes)]
                      for c in chains}
    kb = yaml.safe_load(KB_PATH.read_text(encoding="utf-8")) or []
    rems = load_remediations(kb)
    ranked, global_rank = rank_remediations(rems, chains, links_by_chain)
    unfixable = [r for r in global_rank if not r.remediation.fixable]
    exposure = exposure_score(findings, assets)

    chains_path = DATA_DIR / "chains.json"
    payload = {"exposure": round(exposure, 2), "chains": [c.to_dict() for c in chains],
               "links": [l.to_dict() for l in links]}
    chains_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    write_report(DATA_DIR / "report.md", exposure, chains, ranked, unfixable, assets)
    n_actions = sum(1 for v in ranked.values() for r in v if r.remediation.fixable)
    console.print(f"[bold]报告已写入 {DATA_DIR / 'report.md'}，链 {len(chains)} 条，"
                  f"可断点 {n_actions} 个[/bold]")


@app.command()
def diff() -> None:
    run_diff()


@app.command()
def task() -> None:
    run_task()


if __name__ == "__main__":
    app()
