import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Optional


@dataclass
class ChainDelta:
    key: tuple[str, ...]
    before_weight: float
    after_weight: float
    status: str  # new | broken | weakened | strengthened | stable
    findings_before: list[dict]
    findings_after: list[dict]


def _chain_key(chain: dict) -> tuple[str, ...]:
    return tuple(sorted(chain.get("nodes", [])))


def _load_chains(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _index_chains(payload: dict) -> dict[tuple[str, ...], dict]:
    return {_chain_key(c): c for c in payload.get("chains", [])}


def compare_chains(before_path: Path, after_path: Path) -> list[ChainDelta]:
    before = _index_chains(_load_chains(before_path))
    after = _index_chains(_load_chains(after_path))

    keys = set(before) | set(after)
    deltas: list[ChainDelta] = []
    for key in keys:
        b = before.get(key)
        a = after.get(key)
        bw = b.get("weight", 0.0) if b else 0.0
        aw = a.get("weight", 0.0) if a else 0.0
        if not b:
            status = "new"
        elif not a:
            status = "broken"
        elif aw < bw:
            status = "weakened"
        elif aw > bw:
            status = "strengthened"
        else:
            status = "stable"
        deltas.append(ChainDelta(
            key=key,
            before_weight=bw,
            after_weight=aw,
            status=status,
            findings_before=b.get("findings", []) if b else [],
            findings_after=a.get("findings", []) if a else [],
        ))
    order = {"broken": 0, "weakened": 1, "new": 2, "strengthened": 3, "stable": 4}
    deltas.sort(key=lambda d: (order.get(d.status, 99), -d.after_weight, -d.before_weight))
    return deltas


def _short_label(node: str) -> str:
    if node.startswith("asset:nickname:"):
        return f"昵称:{node.split(':', 2)[2]}"
    if node.startswith("asset:email:"):
        return f"邮箱:{node.split(':', 2)[2]}"
    if node.startswith("asset:avatar:"):
        return Path(node.split(":", 2)[2]).name
    if node.startswith("asset:"):
        return node.split(":", 2)[2]
    if node.startswith("finding:"):
        return "finding"
    return node


def render_diff(deltas: list[ChainDelta]) -> str:
    lines = [f"# calm 复扫对比 — {date.today().isoformat()}", ""]
    counts = {"broken": 0, "weakened": 0, "new": 0, "strengthened": 0, "stable": 0}
    for d in deltas:
        counts[d.status] = counts.get(d.status, 0) + 1
    summary = ", ".join(f"{k} {v}" for k, v in counts.items() if v)
    lines.append(f"链变化：{summary or '无变化'}")
    lines.append("")

    if not deltas:
        lines.append("暂无两次扫描数据可供对比。")
        return "\n".join(lines)

    for d in deltas:
        if d.status == "stable":
            continue
        head = ", ".join(_short_label(n) for n in d.key if n.startswith("asset:")) or "?"
        change = f"{d.before_weight:.1f} → {d.after_weight:.1f}"
        emoji = {"broken": "🟢", "weakened": "🟡", "new": "🔴", "strengthened": "🟠"}.get(d.status, "⚪")
        status_zh = {
            "broken": "已断链",
            "weakened": "已减弱",
            "new": "新增链",
            "strengthened": "增强中",
        }.get(d.status, d.status)
        lines.append(f"{emoji} {status_zh} — {head}（{change}）")
        if d.status in ("new", "strengthened"):
            for f in d.findings_after[:3]:
                lines.append(f"  + [{f.get('source')}] {f.get('kind')}「{f.get('value')}」")
        elif d.status == "broken":
            for f in d.findings_before[:3]:
                lines.append(f"  - [{f.get('source')}] {f.get('kind')}「{f.get('value')}」")
        elif d.status == "weakened":
            before_kinds = {f.get("value") for f in d.findings_before}
            after_kinds = {f.get("value") for f in d.findings_after}
            removed = before_kinds - after_kinds
            if removed:
                lines.append(f"  - 消失的发现：{', '.join(str(x) for x in removed)}")
        lines.append("")

    return "\n".join(lines)


def run_diff(data_dir: Path, before: Optional[Path] = None,
             after: Optional[Path] = None, out_path: Optional[Path] = None) -> str:
    before_path = before or data_dir / "chains-prev.json"
    after_path = after or data_dir / "chains.json"
    deltas = compare_chains(before_path, after_path)
    text = render_diff(deltas)
    out = out_path or data_dir / "diff.md"
    out.write_text(text, encoding="utf-8")
    return text
