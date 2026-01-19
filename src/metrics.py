"""
Metrics Analysis Module.

This module calculates security and efficiency metrics for the synthesized policy.
It compares the synthesized policy against the original topology and Ground Truth.

Metrics implemented:
    1. Attack Surface Reduction (ASR)
    2. Weighted Attack Surface Reduction (wASR)
    3. Lateral Movement Index (LMI)
    4. Weighted Lateral Movement Index (wLMI)
    5. Lateral Movement Index Reduction (LMI Reduction)
    6. False Blocks (FB)
    7. Heuristic False Block Rate (FBR)
    8. Policy Complexity (PC)
"""

import json
import pandas as pd
import networkx as nx
from pathlib import Path
from typing import Dict, Set, Tuple, Any

from iot_models import DeviceFactory, IoTDevice


class MetricsAnalyzer:
    """
    Analyzer class for computing security metrics of IoT Policies.
    """

    def __init__(self, topo_path: str, policy_path: str, out_filepath: str = None):
        """
        Initialize the analyzer.

        Args:
            topo_path: Path to the source topology JSON (contains Ground Truth + Noise).
            policy_path: Path to the synthesized policy CSV.
            out_filepath: Optional path to save the computed metrics as CSV.
        """
        self.topo_data = self._load_topology(Path(topo_path))
        self.policy_df = self._load_policy(Path(policy_path))

        self.out_filepath = out_filepath

        self.device_map = self._build_device_map()

        self.topo_edges = self._extract_topo_edges()
        self.ground_truth_edges = self._extract_ground_truth_edges()
        self.policy_edges = self._extract_policy_edges()

    @staticmethod
    def _load_topology(topo_path) -> Dict:
        if not topo_path.exists():
            raise FileNotFoundError(f"Topology file not found: {topo_path}")
        return json.loads(topo_path.read_text(encoding="utf-8"))

    @staticmethod
    def _load_policy(policy_path) -> pd.DataFrame:
        if not policy_path.exists():
            raise FileNotFoundError(f"Policy file {policy_path} not found.")
        return pd.read_csv(policy_path)

    def _build_device_map(self) -> Dict[str, IoTDevice]:
        """
        Pre-loads device objects to access roles/levels/criticality.
        """
        device_map = {}
        for node in self.topo_data["nodes"]:
            device = DeviceFactory.create(
                role=node["role"],
                node_id=node["id"],
                zone=node.get("zone")
            )
            device_map[node["id"]] = device

        return device_map

    def compute_all_metrics(self) -> Dict[str, Any]:
        """
        Aggregates all metrics into a dictionary.
        """
        full_topology_graph = self._build_graph_from_edges(self.topo_edges)
        policy_graph = self._build_graph_from_edges(self.policy_edges)
        full_topology_lmi = self.calculate_lmi(full_topology_graph)
        policy_lmi = self.calculate_lmi(policy_graph)
        lmi_reduction = 1 - (policy_lmi / full_topology_lmi) if full_topology_lmi > 0 else 0.0

        metrics = {
            "E_total": len(self.topo_edges),
            "E_policy": len(self.policy_edges),
            "ASR": 1 - len(self.policy_edges) / len(self.topo_edges),
            "wASR": round(self.calculate_weighted_asr(), 4),
            "LMI_full ": round(full_topology_lmi, 4),
            "LMI_policy": round(policy_lmi, 4),
            "wLMI_full": round(self.calculate_weighted_lmi(full_topology_graph), 4),
            "wLMI_policy": round(self.calculate_weighted_lmi(policy_graph), 4),
            "LMI_reduction": round(lmi_reduction, 4),
            "FB": self.calculate_false_blocks(),
            "FBR": round(self.calculate_false_block_rate(), 4),
            "PC": self.calculate_policy_complexity(),
        }

        if self.out_filepath is not None:
            self._save_metrics_csv(metrics)

        return metrics

    def _build_graph_from_edges(self, edges: Set[Tuple]) -> nx.DiGraph:
        """
        Helper to build a directed graph from a set of edges.
        """
        graph = nx.DiGraph()
        graph.add_nodes_from(self.device_map.keys())
        graph.add_edges_from([(e[0], e[1]) for e in edges])
        return graph

    def calculate_weighted_asr(self) -> float:
        """
        Weighted Attack Surface Reduction (ASR).
        Formula:
            1 - (Weighted_Policy_Surface / Weighted_Total_Surface)

        Weights are based on the criticality of the DESTINATION node.
        Allowing traffic to a Gateway is 'heavier' than to a Sensor.
        """

        def calculate_surface_weight(edge_set: Set[Tuple]) -> float:
            total_weight = 0.0
            for (_, dst, _, _) in edge_set:
                total_weight += self._get_device_criticality(dst)
            return total_weight

        full_topology_weight = calculate_surface_weight(self.topo_edges)
        policy_topology_weight = calculate_surface_weight(self.policy_edges)

        if full_topology_weight == 0:
            return 0.0

        return 1.0 - (policy_topology_weight / full_topology_weight)

    @staticmethod
    def calculate_lmi(graph: nx.DiGraph) -> float:
        """
        Returns the Lateral Movement Index for a given graph.

        Lateral Movement Index (LMI) - average fraction of the network that can be reached
        from any single compromised node.

        Calculation:
            LMI = (Sum of all reachable nodes count) / (N * (N - 1))
        """
        n_nodes = len(graph.nodes)

        if n_nodes <= 1:
            return 0.0

        total_reachable_count = 0
        max_possible_connections = n_nodes * (n_nodes - 1)

        for node in graph.nodes:
            descendants = nx.descendants(graph, node)
            total_reachable_count += len(descendants)

        return total_reachable_count / max_possible_connections

    def calculate_weighted_lmi(self, graph: nx.DiGraph) -> float:
        """
        Returns the Weighted Lateral Movement Index (wLMI) for a given graph.

        The average "Risk Mass" that can be reached from any single
        compromised node, normalized by the total possible risk mass available
        to capture in the network.

        Calculation:
            For each node i:
               Risk_Reachable_i = Sum(Criticality(d) for d in Descendants(i))
               Total_Risk_Possible_i = Sum(Criticality(all_nodes)) - Criticality(i)
               Score_i = Risk_Reachable_i / Total_Risk_Possible_i

            wLMI = Average(Score_i)
        """
        nodes = list(graph.nodes)
        n_nodes = len(nodes)

        if n_nodes <= 1:
            return 0.0

        node_crit = {n: self._get_device_criticality(n) for n in nodes}
        total_network_risk = sum(node_crit.values())

        if total_network_risk == 0:
            return 0.0

        accumulated_score = 0.0
        valid_nodes_count = 0

        for node in nodes:
            # Max risk an attacker can capture starting from here (everyone else)
            possible_risk = total_network_risk - node_crit[node]

            if possible_risk <= 0:
                continue

            descendants = nx.descendants(graph, node)
            reachable_risk = sum(node_crit[d] for d in descendants)

            accumulated_score += (reachable_risk / possible_risk)
            valid_nodes_count += 1

        if valid_nodes_count == 0:
            return 0.0

        return accumulated_score / n_nodes

    def calculate_false_blocks(self) -> int:
        """
        Returns the False Blocks (FB).

        Count of legitimate functional flows that were blocked (False Negatives).

        Calculation:
            FB = |Ground Truth edges - Policy edges|
        """
        diff = self.ground_truth_edges.difference(self.policy_edges)
        return len(diff)

    def calculate_false_block_rate(self) -> float:
        """
        Returns the Heuristic False Block Rate (FBR).

        Percentage of required flows that were broken.

        Calculation:
            FBR = FB / |Ground Truth edges|
        """
        if not self.ground_truth_edges:
            return 0.0

        fb = self.calculate_false_blocks()
        return fb / len(self.ground_truth_edges)

    def calculate_policy_complexity(self) -> int:
        """
        Returns the Policy Complexity (PC).

        Total number of rules (edges) in the policy.
        """
        return len(self.policy_edges)

    def _get_device_criticality(self, node_id: str) -> float:
        """
        Returns criticality score (0.0 - 1.0) based on device.
        """
        device = self.device_map.get(node_id)

        return getattr(device, "criticality", 0.5)

    def _extract_topo_edges(self) -> Set[Tuple]:
        """
        Extracts all edges from the topology.
        """
        edges = set()
        for e in self.topo_data["edges"]:
            edges.add((e["src"], e["dst"], e["proto"], int(e["port"])))
        return edges

    def _extract_ground_truth_edges(self) -> Set[Tuple]:
        """
        Extracts edges that are marked as functional (not noise).

        Noise edges with "extra" == 1 are excluded.
        """
        edges = set()
        for e in self.topo_data["edges"]:
            is_noise = e.get("extra", 0) == 1
            if not is_noise:
                edges.add((e["src"], e["dst"], e["proto"], int(e["port"])))
        return edges

    def _extract_policy_edges(self) -> Set[Tuple]:
        edges = set()
        for _, row in self.policy_df.iterrows():
            edges.add((row["src"], row["dst"], row["proto"], int(row["port"])))
        return edges

    def _save_metrics_csv(self, metrics: Dict):
        """
        Saves the computed metrics to a CSV file.
        """
        out_df = pd.DataFrame([metrics])

        Path(self.out_filepath).parent.mkdir(parents=True, exist_ok=True)
        out_df.to_csv(self.out_filepath, index=False)
        print(f"Metrics successfully calculated and saved to: {self.out_filepath}")
