from pathlib import Path

import httpx

from .base import Collector, Finding, fid


def _rational_to_float(x):
    try:
        return float(x[0]) / float(x[1])
    except Exception:
        return 0.0


def _dms_to_decimal(dms, ref) -> float:
    deg = _rational_to_float(dms[0])
    minute = _rational_to_float(dms[1])
    sec = _rational_to_float(dms[2])
    val = deg + minute / 60.0 + sec / 3600.0
    if ref in (b"S", b"W", "S", "W"):
        val = -val
    return val


def _decode(v):
    if isinstance(v, bytes):
        try:
            return v.decode("utf-8", "ignore").strip("\x00")
        except Exception:
            return ""
    return v


class D5Exif(Collector):
    source = "D5"
    kinds = ("exif_gps", "exif_device")

    async def collect(self, client: httpx.AsyncClient) -> list[Finding]:
        try:
            import piexif
        except ImportError:
            self.console.print("[yellow]⚠ D5 piexif 未安装（pip install piexif），已跳过[/yellow]")
            return []

        dirs = self.config.get("settings", {}).get("exif_dirs") or []
        findings: list[Finding] = []
        for d in dirs:
            root = Path(d).expanduser()
            if not root.is_dir():
                self.console.print(f"[yellow]⚠ D5 目录不存在：{root}[/yellow]")
                continue
            for p in sorted(root.rglob("*")):
                if p.suffix.lower() not in (".jpg", ".jpeg"):
                    continue
                try:
                    exif = piexif.load(str(p))
                except Exception:
                    continue
                gps = exif.get("GPS") or {}
                lat_ref = _decode(gps.get(1, b"N"))
                lon_ref = _decode(gps.get(3, b"E"))
                if gps.get(2) and gps.get(4):
                    lat = _dms_to_decimal(gps[2], lat_ref)
                    lon = _dms_to_decimal(gps[4], lon_ref)
                    if lat and lon:
                        findings.append(Finding(
                            id=fid(self.source, "exif_gps", f"{lat:.6f},{lon:.6f}", raw_ref=str(p)), source=self.source, kind="exif_gps",
                            value=f"({lat:.6f}, {lon:.6f})",
                            snippet=f"{p.name} GPS {lat:.6f},{lon:.6f}",
                            asset_type="avatar", asset_value=str(p),
                            url=f"https://www.openstreetmap.org/?mlat={lat:.6f}&mlon={lon:.6f}#map=16/{lat:.6f}/{lon:.6f}",
                            reach="public", confidence=1.0,
                            raw_ref=str(p),
                        ))
                zeroth = exif.get("0th") or {}
                exif_ifd = exif.get("Exif") or {}
                make = _decode(zeroth.get(271, b""))
                model = _decode(zeroth.get(272, b""))
                serial = _decode(exif_ifd.get(42033, b"")) or _decode(exif_ifd.get(42034, b""))
                dt = _decode(exif_ifd.get(36867, b"")) or _decode(exif_ifd.get(36868, b""))
                if serial or dt or model:
                    snippet_parts = [f"{k}: {v}" for k, v in
                                     (("Make", make), ("Model", model), ("Serial", serial), ("DateTime", dt)) if v]
                    findings.append(Finding(
                        id=fid(self.source, "exif_device", model or make or "unknown device", raw_ref=str(p)), source=self.source, kind="exif_device",
                        value=model or make or "unknown device",
                        snippet="; ".join(snippet_parts),
                        asset_type="avatar", asset_value=str(p),
                        reach="public", confidence=1.0,
                        raw_ref=str(p),
                    ))
        return findings
