from ..collectors.base import Finding

ASSET_SENSITIVITY = {"phone": 3, "id": 3, "realname": 3, "email": 2,
                     "nickname": 1, "avatar": 1}

REACH_SCORE = {"public": 3, "login": 2, "paid": 1}

HIGH_SENSITIVE_BREACH_FIELDS = ("password", "phone", "address", "credit", "identity", "national", "passport", "id")

BREACH_FIELD_SENSITIVITY = {
    "email": 2, "password": 3, "phone": 3, "address": 3, "credit": 3,
    "name": 3, "username": 1, "ip": 2, "birth": 3, "identity": 3,
}

NORMALIZE_K = 20.0


def node_exposure(asset_type: str | None = None, finding: Finding | None = None) -> float:
    if finding is not None:
        sensitivity = finding_sensitivity(finding)
        reach = REACH_SCORE.get(finding.reach, 1)
        conf = finding.confidence
    else:
        sensitivity = ASSET_SENSITIVITY.get(asset_type or "", 1)
        reach = REACH_SCORE["login"]
        conf = 1.0
    return sensitivity * reach * conf


def finding_sensitivity(f: Finding) -> int:
    if f.kind == "exif_gps":
        return 3
    if f.kind == "exif_device":
        return 2
    if f.kind == "account_registration":
        return 2
    if f.kind == "breach":
        blob = (f.snippet + " " + f.value).lower()
        best = 2
        for field, sens in BREACH_FIELD_SENSITIVITY.items():
            if field in blob and sens > best:
                best = sens
        for marker in HIGH_SENSITIVE_BREACH_FIELDS:
            if marker in blob:
                best = max(best, 3)
        return best
    return 1


def exposure_score(findings: list[Finding], assets: list[dict]) -> float:
    raw = sum(node_exposure(finding=f) for f in findings if f.kind != "collector_notice")
    raw += sum(node_exposure(asset_type=a.get("type")) for a in assets)
    return raw / (raw + NORMALIZE_K) * 10.0


def exposure_bar(score: float, width: int = 10) -> str:
    filled = round(score / 10.0 * width)
    return "█" * filled + "░" * (width - filled)
