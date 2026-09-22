import asyncio
import json
import shutil
from pathlib import Path

import typer
import yaml
from rich.console import Console

from collectors import (CollectorRunner, D1Search, D2Holehe, D3Hibp, D4Maigret,
                        D5Exif, append_findings, load_findings)
from linker import apply_f2f_rules, apply_rules, build_graph, chains_from_graph
from report.diff import run_diff
from report.html import write_html
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
    runner.register(D1Search(config, console))
    runner.register(D2Holehe(config, console))
    runner.register(D3Hibp(config, console))
    runner.register(D4Maigret(config, console))
    runner.register(D5Exif(config, console))
    findings = asyncio.run(runner.run())
    added, dup = append_findings(DATA_DIR / "findings.jsonl", findings)
    console.print(f"[bold]findings.jsonl：新增 {added} 条，去重跳过 {dup} 条[/bold]")


@app.command()
def report(format: str = typer.Option("markdown", "--format", help="报告格式：markdown 或 html")) -> None:
    config = _load_config()
    findings = load_findings(DATA_DIR / "findings.jsonl")
    if not findings:
        console.print("[yellow]findings.jsonl 为空，先运行 calm scan[/yellow]")
        raise typer.Exit(1)
    assets = config.get("assets") or []
    links = apply_rules(assets, findings)
    links.extend(apply_f2f_rules(findings))
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
    prev_path = DATA_DIR / "chains-prev.json"
    if chains_path.exists():
        shutil.copy(chains_path, prev_path)
    payload = {"exposure": round(exposure, 2), "chains": [c.to_dict() for c in chains],
               "links": [l.to_dict() for l in links]}
    chains_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    fmt = format.lower().strip()
    if fmt == "html":
        out_path = DATA_DIR / "report.html"
        write_html(out_path, exposure, chains, ranked, unfixable, assets)
    else:
        out_path = DATA_DIR / "report.md"
        write_report(out_path, exposure, chains, ranked, unfixable, assets)
    n_actions = sum(1 for v in ranked.values() for r in v if r.remediation.fixable)
    console.print(f"[bold]报告已写入 {out_path}，链 {len(chains)} 条，"
                  f"可断点 {n_actions} 个[/bold]")


@app.command()
def diff(
    before: Path = typer.Option(None, "--before", help="旧 chains.json 路径（默认 chains-prev.json）"),
    after: Path = typer.Option(None, "--after", help="新 chains.json 路径（默认 chains.json）"),
    output: Path = typer.Option(None, "--output", help="diff 输出路径（默认 diff.md）"),
) -> None:
    text = run_diff(DATA_DIR, before=before, after=after, out_path=output)
    console.print(f"[bold]复扫对比已写入 {DATA_DIR / (output.name if output else 'diff.md')}[/bold]")


@app.command()
def task(
    asset_type: str = typer.Option(None, "--type", help="资产类型（nickname/realname/phone）"),
    asset_value: str = typer.Option(None, "--value", help="资产值"),
    note: str = typer.Option(None, "--note", help="人工任务结果/备注"),
    list_only: bool = typer.Option(False, "--list", help="仅列出待完成任务"),
) -> None:
    text = run_task(DATA_DIR, asset_type=asset_type, asset_value=asset_value, note=note, list_only=list_only)
    console.print(text)


if __name__ == "__main__":
    app()
