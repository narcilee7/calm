from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from linker.graph import Chain
    from linker.rules import Link


@dataclass
class Remediation:
    id: str
    title: str
    applies_to: list[str]
    cost_minutes: int
    breaks: list[str]
    note: str
    fixable: bool = True


@dataclass
class RankedRemediation:
    remediation: Remediation
    cut_score: float
    chains_broken: list[int] = field(default_factory=list)


def load_remediations(kb: list[dict]) -> list[Remediation]:
    return [Remediation(**item) for item in kb]


def _remediation_applies(rem: Remediation, chain: Chain) -> bool:
    for f in chain.findings:
        if f.source in rem.applies_to or f.kind in rem.applies_to:
            return True
    return False


def _remediation_breaks_chain(rem: Remediation, chain: Chain,
                              links_by_chain: dict[int, list[Link]]) -> bool:
    breakable = set(rem.breaks)
    for link in links_by_chain.get(chain.id, []):
        if link.type in breakable:
            return True
    for f in chain.findings:
        if f.kind in breakable or f.source in breakable:
            return True
    return False


def rank_remediations(rems: list[Remediation], chains: list[Chain],
                      links_by_chain: dict[int, list[Link]]) -> tuple[dict[int, list[RankedRemediation]], list[RankedRemediation]]:
    per_chain: dict[int, list[RankedRemediation]] = {c.id: [] for c in chains}
    for rem in rems:
        applies = [c for c in chains if _remediation_applies(rem, c)]
        if not applies:
            continue
        broken = [c for c in applies if _remediation_breaks_chain(rem, c, links_by_chain)]
        if not broken and rem.fixable:
            continue
        weight_sum = sum(c.weight for c in broken)
        ranked = RankedRemediation(rem, weight_sum * len(broken) / max(rem.cost_minutes, 1),
                                   [c.id for c in broken])
        for c in (broken or applies):
            per_chain[c.id].append(ranked)
    for lst in per_chain.values():
        lst.sort(key=lambda r: r.cut_score, reverse=True)
    global_rank = sorted({id(r): r for lst in per_chain.values() for r in lst}.values(),
                         key=lambda r: r.cut_score, reverse=True)
    return per_chain, global_rank
