"""
Module creates security policies for IoT networks.
"""

import pandas as pd
import numpy as np
import networkx as nx
from typing import Dict, List, Tuple
from pathlib import Path
from sklearn.cluster import SpectralClustering

from constants import Role
from iot_models import DeviceFactory, IoTDevice


class PolicySynthesizer:
    """
    Class that synthesizes security policies using spectral clustering and pruning rules.

    Pipeline Steps:
        1. Spectral Clustering Layer (Math Layer)
        2. Business Logic Pruning Layer (Pruning Layer)
        3. Full Pipeline Execution
    """

    # Gateway and Cloud roles are whitelisted to allow inter-cluster communication between them.
    # These roles often require broader connectivity for management and data aggregation.
    DEFAULT_WHITELIST_ROLES = {"gateway", "cloud"}

    def __init__(
        self,
        out_filepath: str,
        topo_json: Dict,
        seed: int,
        noise_scale: float,
        n_clusters: int = 4,
        whitelist_roles: List[Role] = None,
    ):
        self.out_filepath = out_filepath
        self.topo_json = topo_json
        self.nodes = topo_json["nodes"]
        self.raw_edges = topo_json["edges"]

        self.seed = seed
        self.noise_scale = noise_scale
        self.n_clusters = n_clusters
        self.whitelist_roles = whitelist_roles

        # Create NetworkX graph from topology
        self.graph = self._build_graph()

    def _build_graph(self) -> nx.MultiDiGraph:
        """
        Creates a NetworkX MultiDiGraph from the topology data.
        """
        graph = nx.MultiDiGraph()
        for node in self.nodes:
            graph.add_node(node["id"], **node)
        for edge in self.raw_edges:
            graph.add_edge(edge["src"], edge["dst"], **edge)
        return graph

    def synthesize(self) -> List[Dict]:
        """
        Executes the full policy synthesis pipeline.

        Algorithm Steps:
            1. Generate spectral clustering candidates, filtering edges based on cluster membership and whitelist roles.
            2. Apply pruning rules to remove invalid or undesirable edges:
                - Horizontal Links Pruning
                - Direct Cloud Access Pruning
                - Transitive Jumps Pruning
                - Invalid Downstream Pruning
            3. Save the final synthesized policy to a CSV file.

        More details on each pruning step are documented in their respective methods.
        """
        edges = self.generate_spectral_candidates()
        initial_count = len(self.raw_edges)

        print(f"\n--- Start filtering (Input: {initial_count}) ---")

        edges, horizontal_pruned_edges = self.prune_horizontal_links(edges)
        # NOTE: Cross-Zone Violations Pruning Temporarily Disabled.
        # The effectiveness of pruning edges between zones depends
        # heavily on the number of zones and cannot currently be performed
        # correctly without pruning a large number of legitimate connections.
        # edges, cross_zone_pruned_edges = self.prune_cross_zone_violations(edges)
        edges, direct_cloud_pruned_edges = self.prune_direct_cloud_access(edges)
        edges, transitive_jumps_pruned_edges = self.prune_transitive_jumps(edges)
        edges, invalid_downstream_pruned_edges = self.prune_invalid_downstream(edges)

        total_pruned = (
            len(horizontal_pruned_edges)
            # + len(cross_zone_pruned_edges)
            + len(direct_cloud_pruned_edges)
            + len(transitive_jumps_pruned_edges)
            + len(invalid_downstream_pruned_edges)
        )

        print(
            f"Spectral Clustering Candidates: {len(edges)}\n"
            f"1. Horizontal (Peer-to-Peer): {len(horizontal_pruned_edges)} deleted\n"
            # f"2. Cross-Zone Violations:     {len(cross_zone_pruned_edges)} deleted\n"
            f"2. Cloud Direct Access:       {len(direct_cloud_pruned_edges)} deleted\n"
            f"3. Redundant Shortcuts:       {len(transitive_jumps_pruned_edges)} deleted\n"
            f"4. Invalid Downstream:        {len(invalid_downstream_pruned_edges)} deleted\n"
            f"------------------------------------------------\n"
            f"Total deleted: {total_pruned}\n"
            f"Remained edges: {len(edges)}"
        )

        self.save_policy_csv(edges)
        return edges

    def generate_spectral_candidates(self) -> List[Dict]:
        """
        Generates candidate edges using spectral clustering.

        Algorithm:
            1. Build adjacency matrix from topology.
            2. Perform spectral clustering.
            3. Allow edges within the same cluster.
            4. Allow edges involving whitelist roles.
        """
        if self.whitelist_roles is None:
            whitelist_roles = self.DEFAULT_WHITELIST_ROLES

        node_ids = sorted([n["id"] for n in self.nodes])
        node_idx_map = {
            nid: i
            for i, nid in enumerate(node_ids)
        }
        n_nodes = len(node_ids)

        # Calculate whitelist nodes based on their roles
        whitelist_nodes = set()
        for n in self.nodes:
            if n["role"] in whitelist_roles:
                whitelist_nodes.add(n["id"])

        # Building an adjacency matrix
        adj_matrix = np.zeros((n_nodes, n_nodes))
        for edge in self.raw_edges:
            u, v = edge["src"], edge["dst"]
            if u in node_idx_map and v in node_idx_map:
                idx_u, idx_v = node_idx_map[u], node_idx_map[v]
                # The graph is considered non-oriented for clustering.
                adj_matrix[idx_u][idx_v] = 1
                adj_matrix[idx_v][idx_u] = 1

        sc = SpectralClustering(
            n_clusters=self.n_clusters,
            affinity="precomputed",  # as we provide already computed adjacency matrix
            n_init=100,  # increase the number of iterations to reduce randomness and minimize incorrect starting points
            assign_labels="discretize",  # replaces k-means with an iterative algorithm for better stability
            random_state=self.seed,  # seed for reproducibility
        )
        labels = sc.fit_predict(adj_matrix)

        node_cluster = {
            node_ids[i]: int(labels[i])
            for i in range(n_nodes)
        }

        candidates = []
        seen_edges = set()

        for edge in self.raw_edges:
            u, v = edge["src"], edge["dst"]
            proto = edge.get("proto")
            port = edge.get("port")
            edge_key = (u, v, proto, port)
            if edge_key in seen_edges:
                continue
            seen_edges.add(edge_key)

            is_intra_cluster = node_cluster.get(u) == node_cluster.get(v)
            is_whitelist = (u in whitelist_nodes or v in whitelist_nodes)

            if is_intra_cluster or is_whitelist:
                # Allow everything within the cluster or involving whitelist nodes
                candidates.append({
                    "src": u,
                    "dst": v,
                    "proto": proto,
                    "port": int(port) if port else 0,
                    "required": 1
                })

        return candidates

    def prune_horizontal_links(self, policy_edges: List[Dict]) -> Tuple[List[Dict], List[Dict]]:
        """
        Level 1 devices cannot talk to Level 1 devices directly (peer-to-peer).
        """
        valid = []
        pruned = []

        for edge in policy_edges:
            src_device = self._get_device(edge["src"])
            dst_device = self._get_device(edge["dst"])

            if src_device.level == dst_device.level and src_device.is_isolated_peer:
                pruned.append(edge)
            else:
                valid.append(edge)
        return valid, pruned

    def prune_cross_zone_violations(self, policy_edges: List[Dict]) -> Tuple[List[Dict], List[Dict]]:
        """
        TEMPORARILY DISABLED TO AVOID OVER-PRUNING.
        Zone-based access control.

        Devices from different zones cannot communicate directly,
        except for higher-level devices (L3+).
        """
        # FIXME: Add handling that will take into account the number of zones
        #  and the number of nodes 2+ for more accurate pruning.
        valid = []
        pruned = []

        for edge in policy_edges:
            src_device = self._get_device(edge["src"])
            dst_device = self._get_device(edge["dst"])

            # Check whether devices are in different zones
            if src_device.zone is not None and dst_device.zone is not None and src_device.zone != dst_device.zone:
                # Allow only if a destination device is L3 (Gateway) or higher.
                if dst_device.level >= 3:
                    valid.append(edge)
                else:
                    pruned.append(edge)
            else:
                valid.append(edge)
        return valid, pruned

    def prune_direct_cloud_access(self, policy_edges: List[Dict]) -> Tuple[List[Dict], List[Dict]]:
        """
        Prune direct access to cloud from low-level devices (L1, L2).
        """
        valid = []
        pruned = []

        for edge in policy_edges:
            u, v = edge["src"], edge["dst"]
            src_device = self._get_device(u)
            dst_device = self._get_device(v)

            if src_device.level < 3 and dst_device.role == "cloud":
                pruned.append(edge)
            else:
                valid.append(edge)
        return valid, pruned

    def prune_transitive_jumps(self, policy_edges: List[Dict]) -> Tuple[List[Dict], List[Dict]]:
        """
        Prune redundant transitive jumps in the hierarchy.

        E.g., if there's a path A -> B -> C, then A -> C is redundant.
        """
        valid = []
        pruned = []

        graph = nx.DiGraph()
        graph.add_nodes_from(self.graph.nodes(data=True))  # The same nodes as in the original graph
        graph.add_edges_from([(e["src"], e["dst"]) for e in policy_edges])  # Only the current policy edges

        for edge in policy_edges:
            src_device = self._get_device(edge["src"])
            dst_device = self._get_device(edge["dst"])

            if dst_device.level > src_device.level + 1:
                try:
                    intermediate_nodes = set(graph.successors(edge["src"])) & set(graph.predecessors(edge["dst"]))
                    found_proxy = False
                    for proxy_id in intermediate_nodes:
                        dev_p = self._get_device(proxy_id)
                        if src_device.level < dev_p.level < dst_device.level:
                            found_proxy = True
                            break

                    if found_proxy:
                        pruned.append(edge)
                        continue
                except nx.NetworkXError:
                    pass

            valid.append(edge)
        return valid, pruned

    def prune_invalid_downstream(self, policy_edges: List[Dict]) -> Tuple[List[Dict], List[Dict]]:
        """
        Prune invalid downstream control commands.
        E.g., high-level devices should not send commands to low-level read-only devices.
        """
        valid = []
        pruned = []

        for edge in policy_edges:
            src_device = self._get_device(edge["src"])
            dst_device = self._get_device(edge["dst"])

            if src_device.level > dst_device.level:
                if not dst_device.can_receive_commands:
                    pruned.append(edge)
                    continue

            valid.append(edge)
        return valid, pruned

    def save_policy_csv(self, edges: List[Dict]):
        """
        Saves the synthesized policy edges to a CSV file.
        """
        out_df = pd.DataFrame(edges)

        Path(self.out_filepath).parent.mkdir(parents=True, exist_ok=True)
        out_df.to_csv(self.out_filepath, index=False)
        print(f"Policy successfully synthesized and saved to: {self.out_filepath}")

    def _get_device(self, node_id: str) -> IoTDevice:
        """
        Creates an IoTDevice object from a node in the graph.
        """
        data = self.graph.nodes[node_id]
        return DeviceFactory.create(
            node_id=node_id,
            role=data.get("role", "unknown"),
            zone=data.get("zone"),
        )