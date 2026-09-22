import asyncio
from urllib.parse import quote

import httpx

from .base import Collector, Finding, assert_ownership, fid, notice

UA = "calm-self-audit/0.1"


class D3Hibp(Collector):
    source = "D3"
    kinds = ("breach",)

    async def collect(self, client: httpx.AsyncClient) -> list[Finding]:
        key = (self.config.get("keys") or {}).get("hibp")
        if not key:
            self.console.print("[yellow]⚠ D3 HIBP 无 api key（assets.yaml keys.hibp），已跳过[/yellow]")
            return [notice(self.source, "HIBP api key 未配置（keys.hibp: null），D3 跳过；https://haveibeenpwned.com/API/Key")]

        emails = [a for a in self.config.get("assets", []) if a.get("type") == "email" and a.get("value")]
        if not emails:
            return [notice(self.source, "assets.yaml 中无 email 资产，D3 跳过")]

        findings: list[Finding] = []
        for asset in emails:
            try:
                assert_ownership(asset)
            except Exception as e:
                self.console.print(f"[yellow]⚠ D3 {e}[/yellow]")
                continue
            email = asset["value"].strip()
            url = f"https://haveibeenpwned.com/api/v3/breachedaccount/{quote(email, safe='')}?truncateResponse=false"
            try:
                r = await client.get(url, headers={
                    "hibp-api-key": key,
                    "User-Agent": UA,
                })
                if r.status_code == 404:
                    continue
                if r.status_code != 200:
                    self.console.print(f"[yellow]⚠ D3 HIBP HTTP {r.status_code} for {email}[/yellow]")
                    findings.append(notice(self.source, f"HIBP 查询 {email} 返回 HTTP {r.status_code}"))
                    continue
                for breach in r.json():
                    data = ", ".join(breach.get("DataClasses") or [])
                    findings.append(Finding(
                        id=fid(self.source, "breach", breach.get("Name") or breach.get("Title") or "unknown", asset["value"]), source=self.source, kind="breach",
                        value=breach.get("Title") or breach.get("Name") or "unknown breach",
                        snippet=data[:200],
                        asset_type="email", asset_value=asset["value"],
                        url=f"https://haveibeenpwned.com/PwnedWebsites#{breach.get('Name')}",
                        reach="paid", confidence=1.0,
                    ))
                    await asyncio.sleep(3.0)
            except httpx.HTTPError as e:
                self.console.print(f"[yellow]⚠ D3 HIBP 网络错误：{e}[/yellow]")
                findings.append(notice(self.source, f"HIBP 查询 {email} 网络错误：{e}"))
            await asyncio.sleep(3.0)
        return findings
