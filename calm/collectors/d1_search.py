import asyncio
from urllib.parse import quote

import httpx

from .base import Collector, Finding, fid, notice

UA = "calm-self-audit/0.1"
SEARCH_URL = "https://api.search.brave.com/res/v1/web/search"


class D1Search(Collector):
    source = "D1"
    kinds = ("search_result",)

    async def collect(self, client: httpx.AsyncClient) -> list[Finding]:
        key = (self.config.get("keys") or {}).get("brave")
        if not key:
            self.console.print("[yellow]⚠ D1 Brave Search 无 api key（assets.yaml keys.brave），已跳过[/yellow]")
            return [notice(self.source, "Brave Search api key 未配置（keys.brave: null），D1 跳过；https://brave.com/search/api/")]

        targets = [a for a in self.config.get("assets", [])
                   if a.get("type") in ("nickname", "realname") and a.get("value")]
        if not targets:
            return [notice(self.source, "assets.yaml 中无 nickname/realname 资产，D1 跳过")]

        findings: list[Finding] = []
        for asset in targets:
            query = str(asset["value"]).strip()
            asset_type = asset.get("type")
            self.console.print(f"D1 Brave Search：查询 {asset_type}「{query}」…")
            try:
                r = await client.get(
                    SEARCH_URL,
                    headers={"X-Subscription-Token": key, "User-Agent": UA, "Accept": "application/json"},
                    params={"q": query, "count": 10, "offset": 0},
                    timeout=20.0,
                )
                if r.status_code != 200:
                    self.console.print(f"[yellow]⚠ D1 Brave Search HTTP {r.status_code} for {query}[/yellow]")
                    findings.append(notice(self.source, f"Brave Search 查询 {query} 返回 HTTP {r.status_code}"))
                    continue
                data = r.json()
                results = data.get("web", {}).get("results") or []
                for item in results:
                    title = (item.get("title") or "").strip()
                    url = (item.get("url") or "").strip()
                    desc = (item.get("description") or "").strip()
                    if not title and not url:
                        continue
                    findings.append(Finding(
                        id=fid(self.source, "search_result", f"{title}|{url}", query),
                        source=self.source, kind="search_result",
                        value=title or url,
                        snippet=desc[:280],
                        asset_type=asset_type, asset_value=query,
                        url=url or None,
                        reach="public", confidence=0.5,
                    ))
                await asyncio.sleep(1.0)
            except httpx.HTTPError as e:
                self.console.print(f"[yellow]⚠ D1 Brave Search 网络错误：{e}[/yellow]")
                findings.append(notice(self.source, f"Brave Search 查询 {query} 网络错误：{e}"))
        return findings
