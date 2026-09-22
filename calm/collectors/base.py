import asyncio
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional


class OwnershipError(Exception):
    pass


def assert_ownership(asset: dict) -> None:
    if asset.get("type") in ("phone", "id") and asset.get("verified") is not True:
        raise OwnershipError(
            f"资产 {asset.get('type')} 未通过 ownership 验证（verified: true），按 DESIGN §10 跳过"
        )


def new_id() -> str:
    return uuid.uuid4().hex[:12]


def fid(source: str, kind: str, value: str, asset_value: Optional[str] = None,
        raw_ref: Optional[str] = None) -> str:
    key = "|".join(str(x or "") for x in (source, kind, value, asset_value, raw_ref))
    return uuid.uuid5(uuid.NAMESPACE_URL, "calm:" + key).hex[:12]


@dataclass
class Finding:
    id: str
    source: str
    kind: str
    value: str
    snippet: str = ""
    asset_type: Optional[str] = None
    asset_value: Optional[str] = None
    url: Optional[str] = None
    reach: str = "public"
    confidence: float = 1.0
    raw_ref: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "Finding":
        return cls(**d)


def notice(source: str, message: str, asset_value: Optional[str] = None,
           asset_type: Optional[str] = None) -> Finding:
    return Finding(
        id=fid(source, "collector_notice", message, asset_value), source=source, kind="collector_notice",
        value=message, snippet=message,
        asset_type=asset_type, asset_value=asset_value,
        reach="public", confidence=1.0,
    )


class Collector:
    source = "?"
    kinds: tuple[str, ...] = ()

    def __init__(self, config: dict, console: Any):
        self.config = config
        self.console = console

    async def collect(self, client: "httpx.AsyncClient") -> list[Finding]:
        raise NotImplementedError


class CollectorRunner:
    def __init__(self, config: dict, console: Any):
        self.config = config
        self.console = console
        self.collectors: list[Collector] = []

    def register(self, collector: Collector) -> None:
        self.collectors.append(collector)

    async def _run_one(self, collector: Collector,
                       client: "httpx.AsyncClient") -> tuple[str, list[Finding], Optional[str]]:
        label = f"{collector.source} ({', '.join(collector.kinds)})"
        try:
            findings = await collector.collect(client)
            return label, findings, None
        except Exception as e:
            return label, [], f"{type(e).__name__}: {e}"

    async def run(self) -> list[Finding]:
        import httpx
        sem = asyncio.Semaphore(4)
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            async def guarded(c: Collector) -> tuple[str, list[Finding], Optional[str]]:
                async with sem:
                    return await self._run_one(c, client)
            results = await asyncio.gather(*(guarded(c) for c in self.collectors))
        all_findings: list[Finding] = []
        for label, findings, err in results:
            if err:
                self.console.print(f"[yellow]⚠ {label} 失败：{err}（继续其余源）[/yellow]")
                all_findings.append(notice(label.split()[0], f"collector {label} 失败：{err}"))
            else:
                self.console.print(f"[green]✓ {label}：{len(findings)} 条发现[/green]")
                all_findings.extend(findings)
        return all_findings


def append_findings(path: Path, new: list[Finding]) -> tuple[int, int]:
    existing_ids: set[str] = set()
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                existing_ids.add(Finding.from_dict(__import__("json").loads(line)).id)
            except Exception:
                continue
    added = 0
    dup = 0
    with path.open("a", encoding="utf-8") as f:
        for finding in new:
            if finding.id in existing_ids:
                dup += 1
                continue
            f.write(__import__("json").dumps(finding.to_dict(), ensure_ascii=False) + "\n")
            existing_ids.add(finding.id)
            added += 1
    return added, dup


def load_findings(path: Path) -> list[Finding]:
    if not path.exists():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(Finding.from_dict(__import__("json").loads(line)))
        except Exception:
            continue
    return out
