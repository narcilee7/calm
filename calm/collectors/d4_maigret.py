import asyncio
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import httpx

from .base import Collector, Finding, fid, notice


class D4Maigret(Collector):
    source = "D4"
    kinds = ("account_registration",)

    def __init__(self, config: dict, console):
        super().__init__(config, console)
        venv_bin = Path(sys.executable).parent
        self._maigret_bin = shutil.which("maigret") or str(venv_bin / "maigret")
        if not Path(self._maigret_bin).exists():
            self._maigret_bin = None

    async def collect(self, client: httpx.AsyncClient) -> list[Finding]:
        if not self._maigret_bin:
            return [notice(self.source, "maigret 未安装（pip install maigret），D4 跳过")]

        nicknames = [a for a in self.config.get("assets", [])
                     if a.get("type") == "nickname" and a.get("value")]
        if not nicknames:
            return [notice(self.source, "assets.yaml 中无 nickname 资产，D4 跳过")]

        top_sites = int(self.config.get("settings", {}).get("maigret_top_sites") or 10)
        polite = bool(self.config.get("settings", {}).get("polite", True))
        timeout = 120 if polite else 60

        all_findings: list[Finding] = []
        for asset in nicknames:
            username = str(asset["value"]).strip()
            if not username.isascii():
                self.console.print(f"[yellow]⚠ D4 maigret 跳过非 ASCII 昵称「{username}」（多数平台仅支持 ASCII）[/yellow]")
                continue
            self.console.print(f"D4 maigret：探测昵称「{username}」在 Top {top_sites} 平台…")
            findings = await self._run_one(username, top_sites, timeout)
            all_findings.extend(findings)
            if polite:
                await asyncio.sleep(2.0)
        return all_findings

    async def _run_one(self, username: str, top_sites: int, timeout: int) -> list[Finding]:
        loop = asyncio.get_event_loop()
        with tempfile.TemporaryDirectory(prefix="calm-maigret-") as tmpdir:
            cmd = [
                self._maigret_bin,
                username,
                "--top-sites", str(top_sites),
                "--no-recursion",
                "--no-extracting",
                "--no-autoupdate",
                "--no-progressbar",
                "--no-color",
                "-J", "simple",
                "-fo", tmpdir,
            ]
            try:
                await loop.run_in_executor(
                    None,
                    lambda: subprocess.run(cmd, capture_output=True, text=True, timeout=timeout),
                )
            except subprocess.TimeoutExpired:
                self.console.print(f"[yellow]⚠ D4 maigret 探测 {username} 超时（>{timeout}s）[/yellow]")
                return [notice(self.source, f"maigret 探测 {username} 超时")]
            except Exception as e:
                return [notice(self.source, f"maigret 探测 {username} 失败：{e}")]

            report_path = Path(tmpdir) / f"report_{username}_simple.json"
            if not report_path.exists():
                return []
            try:
                data = json.loads(report_path.read_text(encoding="utf-8"))
            except Exception as e:
                return [notice(self.source, f"maigret 报告解析失败：{e}")]

            findings: list[Finding] = []
            for site_name, info in data.items():
                status = info.get("status", {})
                if status.get("status") != "Claimed":
                    continue
                url = status.get("url") or info.get("url_user") or ""
                findings.append(Finding(
                    id=fid(self.source, "account_registration", site_name, username),
                    source=self.source, kind="account_registration",
                    value=site_name,
                    snippet=f"{username} 已在 {site_name} 注册",
                    asset_type="nickname", asset_value=username,
                    url=url or None,
                    reach="public", confidence=1.0,
                ))
            return findings
