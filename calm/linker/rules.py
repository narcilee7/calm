import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from ..collectors.base import Finding

PHONE_MIN_DIGITS = 7


def normalize(value: str) -> str:
    s = unicodedata.normalize("NFKC", str(value))
    return s.strip().lower()


def normalize_phone(value: str) -> str:
    return re.sub(r"\D", "", str(value))


@dataclass
class Link:
    type: str
    confidence: float
    endpoints: tuple[str, str]

    def to_dict(self) -> dict:
        return {"type": self.type, "confidence": self.confidence,
                "endpoints": list(self.endpoints)}


def rule_same_email(asset: dict, finding: Finding) -> Optional[Link]:
    if asset.get("type") != "email" or finding.kind == "collector_notice":
        return None
    fv = finding.asset_value or ""
    if fv and normalize(fv) == normalize(asset.get("value", "")):
        return Link("same_email", 1.0,
                    (f"asset:email:{normalize(asset['value'])}", f"finding:{finding.id}"))
    return None


def rule_same_nickname(asset: dict, finding: Finding) -> Optional[Link]:
    if asset.get("type") != "nickname" or finding.kind == "collector_notice":
        return None
    nick = normalize(asset.get("value", ""))
    if not nick:
        return None
    if normalize(finding.value) == nick:
        return Link("same_nickname", 1.0,
                    (f"asset:nickname:{nick}", f"finding:{finding.id}"))
    if nick in normalize(finding.snippet):
        return Link("text_hit", 0.5,
                    (f"asset:nickname:{nick}", f"finding:{finding.id}"))
    return None


def rule_same_avatar(asset: dict, finding: Finding) -> Optional[Link]:
    if asset.get("type") != "avatar" or finding.kind == "collector_notice":
        return None
    avatar_path = str(asset.get("value", ""))
    finding_path = finding.asset_value or ""
    if avatar_path and finding_path and Path(avatar_path).resolve() == Path(finding_path).resolve():
        return Link("same_avatar", 1.0,
                    (f"asset:avatar:{avatar_path}", f"finding:{finding.id}"))
    return None


def rule_text_hit(asset: dict, finding: Finding) -> Optional[Link]:
    if finding.kind == "collector_notice":
        return None
    snippet = normalize(finding.snippet) + " " + normalize(finding.value)
    if asset.get("type") == "phone":
        digits = normalize_phone(asset.get("value", ""))
        if len(digits) >= PHONE_MIN_DIGITS and digits in normalize_phone(finding.snippet + finding.value):
            return Link("text_hit", 0.9,
                        (f"asset:phone:{digits}", f"finding:{finding.id}"))
        return None
    if asset.get("type") == "realname":
        name = normalize(asset.get("value", ""))
        if name and len(name) >= 2 and name in snippet:
            conf = 1.0 if normalize(finding.value) == name else 0.6
            return Link("text_hit", conf,
                        (f"asset:realname:{name}", f"finding:{finding.id}"))
    return None


RULES = (rule_same_email, rule_same_nickname, rule_same_avatar, rule_text_hit)


def apply_rules(assets: list[dict], findings: list[Finding]) -> list[Link]:
    links: list[Link] = []
    for asset in assets:
        for finding in findings:
            for rule in RULES:
                link = rule(asset, finding)
                if link:
                    links.append(link)
                    break
    return links


def _device_key(finding: Finding) -> str:
    parts = finding.snippet.split("; ")
    model = ""
    serial = ""
    for p in parts:
        if p.startswith("Model: "):
            model = p.split(": ", 1)[1]
        elif p.startswith("Serial: "):
            serial = p.split(": ", 1)[1]
    return normalize(f"{model}|{serial}")


def _gps_key(finding: Finding) -> str:
    return normalize(finding.value) if finding.kind == "exif_gps" else ""


def rule_same_device(f1: Finding, f2: Finding) -> Optional[Link]:
    if f1.kind != "exif_device" or f2.kind != "exif_device":
        return None
    key1, key2 = _device_key(f1), _device_key(f2)
    if key1 and key1 == key2 and f1.id != f2.id:
        return Link("same_device", 1.0, (f"finding:{f1.id}", f"finding:{f2.id}"))
    return None


def rule_same_gps(f1: Finding, f2: Finding) -> Optional[Link]:
    if f1.kind != "exif_gps" or f2.kind != "exif_gps":
        return None
    key1, key2 = _gps_key(f1), _gps_key(f2)
    if key1 and key1 == key2 and f1.id != f2.id:
        return Link("same_gps", 1.0, (f"finding:{f1.id}", f"finding:{f2.id}"))
    return None


F2F_RULES = (rule_same_device, rule_same_gps)


def apply_f2f_rules(findings: list[Finding]) -> list[Link]:
    links: list[Link] = []
    findings = [f for f in findings if f.kind != "collector_notice"]
    for i, f1 in enumerate(findings):
        for f2 in findings[i + 1:]:
            for rule in F2F_RULES:
                link = rule(f1, f2)
                if link:
                    links.append(link)
                    break
    return links
