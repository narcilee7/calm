import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from ..collectors.base import load_findings


def _load_tasks(path: Path) -> list[dict]:
    if not path.exists():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except Exception:
            continue
    return out


def _assets_with_manual_tasks(config: dict, findings_file: Path) -> list[dict]:
    """返回当前资产中需要人工搜索的 asset（nickname/realname/phone）。"""
    assets = [a for a in config.get("assets", [])
              if a.get("type") in ("nickname", "realname", "phone") and a.get("value")]
    if not findings_file.exists():
        return assets

    # 如果某个 asset 已经存在 search_result finding，认为该任务已有机器结果，降低优先级但仍可人工补充
    findings = load_findings(findings_file)
    covered = {f.asset_value for f in findings if f.kind == "search_result"}
    for a in assets:
        a["machine_covered"] = a.get("value") in covered
    return sorted(assets, key=lambda a: (a.get("machine_covered", False), a.get("type"), a.get("value")))


def render_task_list(config: dict, findings_file: Path, tasks_file: Path) -> str:
    assets = _assets_with_manual_tasks(config, findings_file)
    tasks = _load_tasks(tasks_file)
    submitted = {(t.get("asset_type"), t.get("asset_value")) for t in tasks}
    lines = ["# calm 人工任务", ""]
    if not assets:
        lines.append("当前资产清单无 nickname/realname/phone，无需人工任务。")
        return "\n".join(lines)
    for a in assets:
        atype = a.get("type")
        value = a.get("value")
        covered = a.get("machine_covered", False)
        status = "✅ 已提交" if (atype, value) in submitted else "⬜ 待完成"
        hint = "（机器搜索已有结果，可人工复核）" if covered else ""
        url = f"https://www.bing.com/search?q=%22{value}%22"
        lines.append(f"- {status} [{atype}] {value} {hint}")
        lines.append(f"  去 Bing 搜：{url}")
    lines.append("")
    if tasks:
        lines.append("## 已提交记录")
        lines.append("")
        for t in tasks[-20:]:
            ts = t.get("timestamp", "")[:19]
            lines.append(f"- [{ts}] [{t.get('asset_type')}] {t.get('asset_value')}: {t.get('note')}")
    return "\n".join(lines)


def submit_task(tasks_file: Path, asset_type: str, asset_value: str,
                note: str, submitter: Optional[str] = None) -> dict:
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "asset_type": asset_type,
        "asset_value": asset_value,
        "note": note,
        "submitter": submitter or "user",
    }
    with tasks_file.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
    return record


def run_task(data_dir: Path, asset_type: Optional[str] = None,
             asset_value: Optional[str] = None, note: Optional[str] = None,
             list_only: bool = False) -> str:
    config_path = data_dir / "assets.yaml"
    config = {}
    if config_path.exists():
        import yaml
        config = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}

    findings_file = data_dir / "findings.jsonl"
    tasks_file = data_dir / "tasks.jsonl"

    if list_only or not asset_type or not asset_value or note is None:
        text = render_task_list(config, findings_file, tasks_file)
        out_path = data_dir / "tasks.md"
        out_path.write_text(text, encoding="utf-8")
        return text

    submit_task(tasks_file, asset_type, asset_value, note)
    return f"已提交：[{asset_type}] {asset_value} → {note}"
