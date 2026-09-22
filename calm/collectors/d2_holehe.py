import asyncio

import httpx

from .base import Collector, Finding, assert_ownership, fid, notice


def _discover_probes():
    from holehe.core import import_submodules, get_functions
    modules = import_submodules("holehe.modules")
    return get_functions(modules)


class D2Holehe(Collector):
    source = "D2"
    kinds = ("account_registration",)

    async def collect(self, client: httpx.AsyncClient) -> list[Finding]:
        try:
            probes = _discover_probes()
        except ImportError:
            self.console.print("[yellow]⚠ D2 holehe 未安装：pip install holehe（已跳过）[/yellow]")
            return [notice(self.source, "holehe 未安装，D2 跳过；pip install holehe 后重试")]
        except Exception as e:
            return [notice(self.source, f"holehe 模块发现失败：{e}")]

        emails = [a for a in self.config.get("assets", []) if a.get("type") == "email" and a.get("value")]
        if not emails:
            return [notice(self.source, "assets.yaml 中无 email 资产，D2 跳过")]

        polite = bool(self.config.get("settings", {}).get("polite", True))
        findings: list[Finding] = []
        for asset in emails:
            try:
                assert_ownership(asset)
            except Exception as e:
                self.console.print(f"[yellow]⚠ D2 {e}[/yellow]")
                continue
            email = str(asset["value"]).strip()
            self.console.print(f"D2 holehe：探测 {email} 在 {len(probes)} 个站点的注册态…")
            for probe in probes:
                out: list[dict] = []
                try:
                    await asyncio.wait_for(probe(email, client, out), timeout=5.0)
                except asyncio.TimeoutError:
                    continue
                except Exception:
                    continue
                if polite:
                    await asyncio.sleep(1.0)
                for result in out:
                    if result.get("exists") is True:
                        findings.append(Finding(
                            id=fid(self.source, "account_registration", str(result.get("name") or probe.__name__), asset["value"]), source=self.source, kind="account_registration",
                            value=result.get("name") or probe.__name__,
                            snippet=f"{email} 已在 {result.get('domain') or result.get('name')} 注册",
                            asset_type="email", asset_value=asset["value"],
                            url=(f"https://{result['domain']}" if result.get("domain") else None),
                            reach="login", confidence=1.0,
                        ))
        return findings
