from collections import defaultdict
from typing import Optional

from ..collectors.base import Finding


def _text(f: Finding) -> str:
    parts = [f.source, f.kind, f.value, f.snippet]
    if f.asset_type:
        parts.append(f.asset_type)
    if f.asset_value:
        parts.append(f.asset_value)
    return " ".join(str(p) for p in parts if p)


def cluster_findings(findings: list[Finding],
                     eps: float = 0.35,
                     min_samples: int = 2) -> dict[str, Optional[int]]:
    """用 TF-IDF + DBSCAN 对 finding 文本做相似度聚类。

    返回 finding.id → cluster_id 的映射；cluster_id 为 None 表示噪声点（不相似）。
    eps 越小，聚类越严格；min_samples 控制最小簇大小。
    """
    try:
        from sklearn.cluster import DBSCAN
        from sklearn.feature_extraction.text import TfidfVectorizer
    except ImportError:
        return {f.id: None for f in findings}

    candidates = [f for f in findings if f.kind != "collector_notice"]
    if len(candidates) < min_samples:
        return {f.id: None for f in findings}

    texts = [_text(f) for f in candidates]
    vectorizer = TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 4), min_df=1)
    try:
        X = vectorizer.fit_transform(texts)
    except Exception:
        return {f.id: None for f in findings}

    # DBSCAN 默认用欧氏距离；对 TF-IDF 用 cosine 时通常预计算距离矩阵
    clustering = DBSCAN(eps=eps, min_samples=min_samples, metric="cosine").fit(X)
    out: dict[str, Optional[int]] = {}
    for f in findings:
        if f.kind == "collector_notice":
            out[f.id] = None
            continue
        idx = candidates.index(f)
        label = clustering.labels_[idx]
        out[f.id] = int(label) if label >= 0 else None
    return out


def cluster_groups(findings: list[Finding],
                   eps: float = 0.35,
                   min_samples: int = 2) -> dict[int, list[Finding]]:
    labels = cluster_findings(findings, eps=eps, min_samples=min_samples)
    groups: dict[int, list[Finding]] = defaultdict(list)
    for f in findings:
        label = labels.get(f.id)
        if label is not None:
            groups[label].append(f)
    return dict(groups)
