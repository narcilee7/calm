from dataclasses import dataclass, field

import networkx as nx

from ..collectors.base import Finding
from ..linker.rules import Link, normalize
from ..scorer.exposure import node_exposure


@dataclass
class Chain:
    id: int
    nodes: list[str]
    findings: list[Finding] = field(default_factory=list)
    weight: float = 0.0

    def to_dict(self) -> dict:
        return {"id": self.id, "nodes": self.nodes, "weight": round(self.weight, 2),
                "findings": [f.to_dict() for f in self.findings]}


def build_graph(assets: list[dict], findings: list[Finding], links: list[Link]) -> nx.Graph:
    g = nx.Graph()
    for asset in assets:
        key = f"asset:{asset.get('type')}:{normalize(asset.get('value', ''))}"
        g.add_node(key, node_type="asset", label=str(asset.get("value")),
                   exposure=node_exposure(asset_type=asset.get("type")))
    for f in findings:
        if f.kind == "collector_notice":
            continue
        g.add_node(f"finding:{f.id}", node_type="finding", finding=f,
                   exposure=node_exposure(finding=f))
    for link in links:
        g.add_edge(link.endpoints[0], link.endpoints[1],
                   link_type=link.type, confidence=link.confidence)
    return g


def chains_from_graph(g: nx.Graph) -> list[Chain]:
    chains: list[Chain] = []
    for comp in nx.connected_components(g):
        if len(comp) < 2:
            continue
        findings = [g.nodes[n]["finding"] for n in comp
                    if g.nodes[n].get("node_type") == "finding" and "finding" in g.nodes[n]]
        weight = sum(g.nodes[n].get("exposure", 0.0) for n in comp)
        chains.append(Chain(id=0, nodes=sorted(comp), findings=findings, weight=weight))
    chains.sort(key=lambda c: c.weight, reverse=True)
    for i, c in enumerate(chains, 1):
        c.id = i
    return chains
