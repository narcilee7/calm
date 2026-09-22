from datetime import date
from pathlib import Path
from urllib.parse import quote

from collectors.base import Finding
from linker import Chain
from scorer import RankedRemediation, exposure_bar

SENS_LABEL = {1: "低", 2: "中", 3: "高"}


def _finding_line(f: Finding) -> str:
    conf = f.confidence
    url_part = f" ({f.url})" if f.url else ""
    return f"[{f.source}] {f.kind}「{f.value}」(conf {conf:.1f}){url_part}"


def _chain_title(chain: Chain) -> str:
    assets = [n.split(":", 2)[2] for n in chain.nodes if n.startswith("asset:")]
    top = chain.findings[0] if chain.findings else None
    head = assets[0] if assets else "?"
    head_label = Path(head).name if "/" in head else head
    if top:
        return f"{head_label} → {top.source} {top.value}"
    return head_label


def render_report(exposure: float, chains: list[Chain],
                  ranked: dict[int, list[RankedRemediation]],
                  unfixable: list[RankedRemediation],
                  assets: list[dict]) -> str:
    total_actions = sum(1 for v in ranked.values() for r in v if r.remediation.fixable)
    lines = [
        f"# calm 报告 — {date.today().isoformat()}",
        "",
        f"暴露面: {exposure_bar(exposure)} {exposure:.1f}/10 关联链: {len(chains)} 条 可断点: {total_actions} 个",
        "",
    ]
    if not chains:
        lines += ["未发现关联链。保持警惕，定期复扫。", ""]
    for chain in chains:
        lines.append(f"## 🔴 链 #{chain.id} — {_chain_title(chain)}（weight {chain.weight:.1f}）")
        lines.append("")
        asset_nodes = sorted(n for n in chain.nodes if n.startswith("asset:"))
        finding_nodes = sorted(n for n in chain.nodes if n.startswith("finding:"))
        asset_labels = [Path(n.split(":", 2)[2]).name for n in asset_nodes]
        if asset_labels:
            lines.append(f"涉及资产：{', '.join(asset_labels)}")
            lines.append("")
        grouped: dict[tuple[str, str, str], list[str]] = {}
        for n in finding_nodes:
            f = next((x for x in chain.findings if f"finding:{x.id}" == n), None)
            if not f:
                continue
            key = (f.source, f.kind, f.value)
            grouped.setdefault(key, []).append(Path(f.raw_ref or "").name or "?")
        if grouped:
            for (source, kind, value), files in grouped.items():
                files_part = f"（{len(files)} 处：{', '.join(files)}）" if len(files) > 1 else ""
                lines.append(f"- [{source}] {kind}「{value}」{files_part}")
            lines.append("")
        lines.append("修复优先级：")
        lines.append("")
        fixable = [r for r in ranked.get(chain.id, []) if r.remediation.fixable]
        for i, r in enumerate(fixable, 1):
            rem = r.remediation
            lines.append(f"{i}. {rem.title} CutScore {r.cut_score:.1f} 成本 {rem.cost_minutes}min")
        if not fixable:
            lines.append("（暂无匹配修复项，欢迎向 kb/remediation.yaml 贡献）")
        lines.append("")
    lines.append("## 🟡 不可修复项（诚实区）")
    lines.append("")
    if unfixable:
        for r in unfixable:
            lines.append(f"- {r.remediation.title}：{r.remediation.note.strip()}")
    else:
        lines.append("- 本次扫描未发现不可修复项。")
    lines.append("")
    lines.append("## 📋 人工任务（工具不爬，你来当传感器）")
    lines.append("")
    manual = [a for a in assets if a.get("type") in ("nickname", "realname", "phone") and a.get("value")]
    if manual:
        for a in manual:
            q = quote(str(a["value"]))
            lines.append(f"- 去 Bing 搜 [{a['value']}](https://www.bing.com/search?q=%22{q}%22)，检查前 3 页是否有暴露真实身份的内容 → 结果贴回 `calm task --submit`")
    else:
        lines.append("- 本次资产清单无 nickname/realname/phone，无需人工搜索任务。")
    lines.append("")
    return "\n".join(lines)


def write_report(path: Path, exposure: float, chains: list[Chain],
                 ranked: dict[int, list[RankedRemediation]],
                 unfixable: list[RankedRemediation],
                 assets: list[dict]) -> str:
    text = render_report(exposure, chains, ranked, unfixable, assets)
    path.write_text(text, encoding="utf-8")
    return text
