from datetime import date
from pathlib import Path
from urllib.parse import quote

from jinja2 import Template

from collectors.base import Finding
from linker import Chain
from scorer import RankedRemediation, exposure_bar

HTML_TEMPLATE = """<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>calm 报告 — {{ report_date }}</title>
  <style>
    :root { --bg: #f8f9fa; --card: #fff; --text: #212529; --muted: #6c757d; --danger: #dc3545; --warning: #ffc107; --info: #0dcaf0; }
    body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif; background: var(--bg); color: var(--text); max-width: 900px; margin: 0 auto; padding: 2rem 1rem; line-height: 1.6; }
    h1 { font-size: 1.75rem; margin-bottom: .5rem; }
    .summary { background: var(--card); border-radius: .75rem; padding: 1.25rem; box-shadow: 0 1px 3px rgba(0,0,0,.08); margin-bottom: 1.5rem; }
    .summary .metric { font-size: 1.1rem; margin: .25rem 0; }
    .bar { font-family: monospace; letter-spacing: 2px; color: var(--danger); }
    .chain { background: var(--card); border-radius: .75rem; padding: 1.25rem; box-shadow: 0 1px 3px rgba(0,0,0,.08); margin-bottom: 1.25rem; }
    .chain h2 { font-size: 1.25rem; margin-top: 0; color: var(--danger); }
    .assets { color: var(--muted); font-size: .95rem; margin-bottom: .75rem; }
    .findings { list-style: none; padding: 0; margin: 0 0 1rem; }
    .findings li { padding: .4rem 0; border-bottom: 1px solid #eee; }
    .findings li:last-child { border-bottom: none; }
    .actions { margin-top: 1rem; }
    .actions ol { margin: .5rem 0 0 1.25rem; }
    .actions li { margin: .35rem 0; }
    .section { background: var(--card); border-radius: .75rem; padding: 1.25rem; box-shadow: 0 1px 3px rgba(0,0,0,.08); margin-bottom: 1.25rem; }
    .section h2 { font-size: 1.25rem; margin-top: 0; }
    .tag { display: inline-block; font-size: .75rem; padding: .15rem .5rem; border-radius: 999px; background: #e9ecef; color: var(--muted); margin-left: .5rem; }
    a { color: #0d6efd; text-decoration: none; }
    a:hover { text-decoration: underline; }
  </style>
</head>
<body>
  <h1>calm 报告 — {{ report_date }}</h1>
  <div class="summary">
    <div class="metric">暴露面: <span class="bar">{{ exposure_bar }}</span> {{ "%.1f"|format(exposure) }}/10</div>
    <div class="metric">关联链: {{ chains|length }} 条</div>
    <div class="metric">可断点: {{ total_actions }} 个</div>
  </div>

  {% if not chains %}
    <div class="section">
      <p>未发现关联链。保持警惕，定期复扫。</p>
    </div>
  {% endif %}

  {% for chain in chains %}
  <div class="chain">
    <h2>链 #{{ chain.id }} — {{ chain_title(chain) }}（weight {{ "%.1f"|format(chain.weight) }}）</h2>
    <div class="assets">涉及资产：{{ asset_labels(chain)|join(", ") }}</div>
    <ul class="findings">
      {% for item in chain_findings(chain) %}
      <li>
        [{{ item.source }}] {{ item.kind }}「{{ item.value }}」
        {% if item.count > 1 %}<span class="tag">{{ item.count }} 处：{{ item.files|join(", ") }}</span>{% endif %}
      </li>
      {% endfor %}
    </ul>
    <div class="actions">
      <strong>修复优先级：</strong>
      <ol>
        {% for r in ranked.get(chain.id, []) if r.remediation.fixable %}
        <li>{{ r.remediation.title }} <span class="tag">CutScore {{ "%.1f"|format(r.cut_score) }}</span> <span class="tag">成本 {{ r.remediation.cost_minutes }}min</span></li>
        {% else %}
        <li>（暂无匹配修复项）</li>
        {% endfor %}
      </ol>
    </div>
  </div>
  {% endfor %}

  <div class="section">
    <h2>不可修复项（诚实区）</h2>
    {% if unfixable %}
      <ul>
        {% for r in unfixable %}
        <li><strong>{{ r.remediation.title }}</strong>：{{ r.remediation.note.strip() }}</li>
        {% endfor %}
      </ul>
    {% else %}
      <p>本次扫描未发现不可修复项。</p>
    {% endif %}
  </div>

  <div class="section">
    <h2>人工任务（工具不爬，你来当传感器）</h2>
    {% if manual_assets %}
      <ul>
        {% for a in manual_assets %}
        <li>去 Bing 搜 <a href="https://www.bing.com/search?q=%22{{ a.value|urlencode }}%22" target="_blank">{{ a.value }}</a>，检查前 3 页是否有暴露真实身份的内容 → 结果贴回 <code>calm task --submit</code></li>
        {% endfor %}
      </ul>
    {% else %}
      <p>本次资产清单无 nickname/realname/phone，无需人工搜索任务。</p>
    {% endif %}
  </div>
</body>
</html>
"""


def _chain_title(chain: Chain) -> str:
    assets = [n.split(":", 2)[2] for n in chain.nodes if n.startswith("asset:")]
    top = chain.findings[0] if chain.findings else None
    head = assets[0] if assets else "?"
    head_label = Path(head).name if "/" in head else head
    if top:
        return f"{head_label} → {top.source} {top.value}"
    return head_label


def _asset_labels(chain: Chain) -> list[str]:
    return [Path(n.split(":", 2)[2]).name for n in chain.nodes if n.startswith("asset:")]


def _chain_findings(chain: Chain) -> list[dict]:
    grouped: dict[tuple[str, str, str], list[str]] = {}
    finding_nodes = sorted(n for n in chain.nodes if n.startswith("finding:"))
    for n in finding_nodes:
        f = next((x for x in chain.findings if f"finding:{x.id}" == n), None)
        if not f:
            continue
        key = (f.source, f.kind, f.value)
        grouped.setdefault(key, []).append(Path(f.raw_ref or "").name or "?")
    return [
        {"source": k[0], "kind": k[1], "value": k[2], "count": len(v), "files": v}
        for k, v in grouped.items()
    ]


def render_html(exposure: float, chains: list[Chain],
                ranked: dict[int, list[RankedRemediation]],
                unfixable: list[RankedRemediation],
                assets: list[dict]) -> str:
    total_actions = sum(1 for v in ranked.values() for r in v if r.remediation.fixable)
    manual_assets = [a for a in assets if a.get("type") in ("nickname", "realname", "phone") and a.get("value")]
    template = Template(HTML_TEMPLATE)
    return template.render(
        report_date=date.today().isoformat(),
        exposure=exposure,
        exposure_bar=exposure_bar(exposure),
        chains=chains,
        total_actions=total_actions,
        ranked=ranked,
        unfixable=unfixable,
        manual_assets=manual_assets,
        chain_title=_chain_title,
        asset_labels=_asset_labels,
        chain_findings=_chain_findings,
    )


def write_html(path: Path, exposure: float, chains: list[Chain],
               ranked: dict[int, list[RankedRemediation]],
               unfixable: list[RankedRemediation],
               assets: list[dict]) -> str:
    text = render_html(exposure, chains, ranked, unfixable, assets)
    path.write_text(text, encoding="utf-8")
    return text
