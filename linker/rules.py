import re
import unicodedata
from dataclasses import dataclass, field
from typing import Optional

from collectors.base import Finding

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


def rule_same_avatar_hash(asset: dict, finding: Finding) -> Optional[Link]:
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


RULES = (rule_same_email, rule_same_nickname, rule_same_avatar_hash, rule_text_hit)


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
