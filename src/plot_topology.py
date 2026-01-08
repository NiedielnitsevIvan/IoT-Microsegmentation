"""
IoT Topology Visualization Module.

This script visualizes the network topology.
Divides the topology into zones and displays them
and the nodes inside radially for improved readability and greater clarity.

It includes ADAPTIVE SCALING to handle large topologies:
    - Automatically resizes nodes, zones and fonts based on graph density.
    - "Smart Labels": Hides labels for low-level devices in dense graphs.
    - "Orbital Layout": Uses a shell/star layout within zones.
"""
import json
import math
from collections import defaultdict
from functools import cached_property
from pathlib import Path
from typing import Any, Dict, List, Tuple

import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import pandas as pd
from matplotlib.axes import Axes
from matplotlib.lines import Line2D
from matplotlib.patches import Circle, Patch

from iot_models import DeviceFactory, IoTDevice

Coordinates: np.array[np.float64, np.float64] = np.array


class TopologyVisualizer:
    """
    Class responsible for rendering the IoT network topology.

    Creates a zoned, star-layout visualization of the network graph.
    Adapts visual properties based on graph density.
    """

    def __init__(self, topo_path: str, policy_path: str, seed: int):
        self.graph = self._load_topology(Path(topo_path))
        self.policy = self._load_policy(Path(policy_path))
        self.seed = seed
        self.plot_config = self._calculate_dynamic_plot_config()

    def create_plot(
        self,
        out_path: str,
        width: int = 2400,
        height: int = 1600,
        with_labels: bool = True
    ) -> None:
        """
        Creates and saves the topology plot.
        """
        pos, zone_centers = self._compute_zoned_layout()
        plt.figure(figsize=(width / 100, height / 100))
        axes = plt.gca()

        self._draw_zones(axes, zone_centers, pos)
        self._draw_edges(pos)
        self._draw_nodes(pos)

        if with_labels:
            self._draw_smart_labels(pos)

        self._create_legend(axes)

        plt.title(f"IoT Topology Audit (nodes_count={len(self.graph.nodes)})", fontsize=18)
        plt.axis("off")
        plt.tight_layout()

        Path(out_path).parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(str(out_path), dpi=500, bbox_inches="tight")
        plt.close()
        print(f"Visualization saved to {out_path}")

    @cached_property
    def _device_map(self) -> Dict[str, IoTDevice]:
        """
        Builds a mapping from node IDs to IoTDevice instances.
        """
        device_map = {}
        for node_id, data in self.graph.nodes(data=True):
            device = DeviceFactory.create(data.get("role", "unknown"), node_id, data.get("zone"))
            device_map[node_id] = device
        return device_map

    @staticmethod
    def _load_topology(topo_path: Path) -> nx.MultiDiGraph:
        """
        Loads JSON topology into a NetworkX MultiDiGraph.
        """
        content = topo_path.read_text(encoding="utf-8")
        data = json.loads(content)
        graph = nx.MultiDiGraph()
        for node in data["nodes"]:
            graph.add_node(node["id"], **node)
        for edge in data["edges"]:
            graph.add_edge(edge["src"], edge["dst"], **edge)
        return graph

    @staticmethod
    def _load_policy(policy_path: Path) -> pd.DataFrame:
        """
        Loads the policy CSV into a DataFrame.
        """
        if policy_path and policy_path.exists():
            return pd.read_csv(policy_path)
        return pd.DataFrame()

    def _calculate_dynamic_plot_config(self) -> Dict[str, Any]:
        """
        Calculates visual properties based on the number of nodes.
        """
        nodes_count = len(self.graph.nodes)

        plot_config = {
            "node_size": 450,
            "font_size": 9,
            "edge_width": 1.5,
            "edge_alpha": 0.6,
            "layout_scale": 8.0,
            "smart_labeling": False,  # Whether to hide labels for L1 nodes in dense graphs
        }

        if nodes_count > 150:
            plot_config.update({
                "node_size": 120,
                "font_size": 4,
                "edge_width": 0.6,
                "edge_alpha": 0.4,
                "layout_scale": 16.0,
                "smart_labeling": True
            })
        elif nodes_count > 50:
            plot_config.update({
                "node_size": 300,
                "font_size": 6,
                "edge_width": 1.0,
                "edge_alpha": 0.5,
                "layout_scale": 14.0,
            })

        return plot_config

    def _compute_zoned_layout(self) -> Tuple[Dict[str, Coordinates], Dict[str, Coordinates]]:
        """
        Computes a clustered layout using an ORBITAL approach for zones.

        Returns:
            - node_positions: Dict mapping node IDs to (x, y) coordinates.
            - zone_centers: Dict mapping zone areas to their center (x, y) coordinates.
        """
        zones = self._get_zones_with_nodes()
        node_positions = {}
        zone_centers = {}
        sorted_keys = sorted([k for k in zones.keys() if k != "Core"])
        num_outer_zones = len(sorted_keys)
        radius_macro = self.plot_config["layout_scale"] if num_outer_zones > 1 else 0.0

        if "Core" in zones:
            zone_centers["Core"] = np.array([0.0, 0.0])

        for i, zone_label in enumerate(sorted_keys):
            angle = 2 * math.pi * i / num_outer_zones if num_outer_zones > 0 else 0
            cx = radius_macro * math.cos(angle)
            cy = radius_macro * math.sin(angle)
            zone_centers[zone_label] = np.array([cx, cy])

        for zone_label, nodes in zones.items():
            if not nodes:
                continue

            center = zone_centers.get(zone_label)
            subgraph = self.graph.subgraph(nodes)

            # For greater clarity, nodes are arranged radially in their zones
            # High-level devices(Hubs, NVRs, etc.) in the center,
            # low-level devices (sensors, cameras, etc.) on the outside.
            nucleus_nodes = []
            orbit_nodes = []

            for n in nodes:
                device = self._device_map[n]
                if device.level > 1:
                    nucleus_nodes.append(n)
                else:
                    orbit_nodes.append(n)

            shells = []
            if nucleus_nodes:
                shells.append(nucleus_nodes)
            if orbit_nodes:
                shells.append(orbit_nodes)

            if not shells:
                shells = [nodes]

            shell_pos = nx.shell_layout(subgraph, nlist=shells)
            k_val = 2.0 / math.sqrt(len(nodes)) if len(nodes) > 0 else 0.5

            local_pos = nx.spring_layout(
                subgraph,
                pos=shell_pos,
                fixed=None,
                k=k_val,
                seed=self.seed,
                iterations=30
            )

            if zone_label == "Core":
                # The Core zone contains only a few high-level nodes, so keep it compact.
                final_scale = 1.8
            else:
                node_count = len(nodes)
                base_scale = radius_macro * 0.35 if radius_macro > 0 else 3.0
                expansion = math.sqrt(node_count) * 0.4
                final_scale = base_scale + expansion

            for node_id, coords in local_pos.items():
                node_positions[node_id] = (coords * final_scale) + center

        return node_positions, zone_centers

    def _get_zones_with_nodes(self) -> Dict[str, List[str]]:
        """
        Groups nodes by their zone attribute.

        Returns a dictionary mapping zone labels to lists of node IDs.
        """
        zones = defaultdict(list)
        unknown_zone_label = "Infrastructure"

        for node, data in self.graph.nodes(data=True):
            zone = data.get("zone")
            role = data.get("role", "unknown")
            if role in ["cloud", "gateway"]:
                zones["Core"].append(node)
            elif zone is None:
                zones[unknown_zone_label].append(node)
            else:
                zones[f"Zone {zone}"].append(node)

        return zones

    def _draw_zones(self, axes: Axes, zone_centers: Dict[str, Coordinates], pos: Dict[str, Coordinates]) -> None:
        """
        Draws background circles.

        Draws semi-transparent circles for each zone with dynamic radius
        based on node distribution within the zone.
        """
        for i, (zone_label, center) in enumerate(zone_centers.items()):
            nodes_dists = []
            cutoff = self.plot_config["layout_scale"] * 0.6

            for node_id, coords in pos.items():
                dist = np.linalg.norm(np.array(coords) - center)
                if dist < cutoff:
                    nodes_dists.append(dist)

            radius = max(nodes_dists) + 0.5 if nodes_dists else 2.0

            if zone_label == "Core":
                radius = min(radius, 3.0)
                color = "#EEEEEE"  # Fixed light gray for Core
            else:
                golden_angle_conjugate = 0.618  # Approx. conjugate of the golden ratio
                hue = (i * golden_angle_conjugate) % 1.0
                color = mcolors.hsv_to_rgb([hue, 0.25, 0.9])

            circle = Circle(xy=center, radius=radius, color=color, alpha=0.4, zorder=0)
            axes.add_patch(circle)

            axes.text(
                center[0],
                center[1] + radius + 0.2,
                zone_label,
                fontsize=12,
                fontweight="bold",
                color="gray",
                ha="center",
                va="top",
                zorder=1
            )

    def _draw_edges(self, pos: Dict[str, Coordinates]) -> None:
        """
        Draws edges with allowed/blocked styling based on the policy.
        """
        remaining_edges = {
            (row["src"], row["dst"], row["proto"], int(row["port"]))
            for _, row in self.policy.iterrows()
        }
        all_edges = {
            (src, dst, data["proto"], int(data["port"]))
            for src, dst, data in self.graph.edges(data=True)
        }
        removed_edges = all_edges.difference(remaining_edges)

        width = self.plot_config["edge_width"]
        alpha = self.plot_config["edge_alpha"]

        if removed_edges:
            nx.draw_networkx_edges(
                self.graph,
                pos,
                edgelist=removed_edges,
                edge_color="tab:red",
                style="dashed",
                alpha=alpha * 0.4,
                width=width * 0.8,
                arrows=False
            )

        if remaining_edges:
            nx.draw_networkx_edges(
                self.graph,
                pos,
                edgelist=remaining_edges,
                edge_color="tab:green",
                style="solid",
                alpha=alpha,
                width=width,
                arrows=True,
                arrowstyle="->",
                arrowsize=8,
                connectionstyle="arc3,rad=0.05"
            )

    def _draw_nodes(self, pos: Dict[str, Coordinates]) -> None:
        """
        Draws nodes.
        """
        nodes_by_class = defaultdict(list)

        for node_id, data in self.graph.nodes(data=True):
            device = self._device_map[node_id]
            nodes_by_class[type(device)].append(node_id)

        for device_type, node_list in nodes_by_class.items():
            sample_device = self._device_map[node_list[0]]
            config = sample_device.viz_config

            nx.draw_networkx_nodes(
                self.graph,
                pos,
                nodelist=node_list,
                node_color=config["color"],
                node_shape=config["marker"],
                node_size=self.plot_config["node_size"],
                alpha=0.9,
                edgecolors="white",
                linewidths=0.5,
                label=sample_device.role.capitalize()
            )

    def _draw_smart_labels(self, pos: Dict[str, Coordinates]) -> None:
        """
        Draws node labels.

        On dense graphs, hides labels for level 1 devices
        (sensors, cameras, actuators) for better clarity.
        """
        labels = {}
        for node_id, data in self.graph.nodes(data=True):
            device = self._device_map[node_id]
            if self.plot_config["smart_labeling"]:
                # Many level 1 devices with labels negatively affects the display in dense graphs.
                if device.level >= 2:
                    labels[node_id] = node_id
            else:
                labels[node_id] = node_id

        nx.draw_networkx_labels(
            self.graph,
            pos,
            labels=labels,
            font_size=self.plot_config["font_size"],
            font_weight="bold"
        )

    def _create_legend(self, axes: Axes) -> None:
        """
        Draws the legend for the plot.
        """
        legend_elements = [
            Line2D([0], [0], color="tab:green", lw=2, label="Allowed Flow"),
            Line2D([0], [0], color="tab:red", lw=2, linestyle="--", label="Blocked"),
            Patch(facecolor="lightgray", edgecolor="gray", alpha=0.5, label="Zone"),
            Patch(alpha=0, label="")
        ]
        present_roles = set()
        for _, data in self.graph.nodes(data=True):
            present_roles.add(data.get("role", "unknown"))

        device_instances = []
        for role in present_roles:
            device_instances.append(DeviceFactory.create(role, "legend"))

        device_instances.sort(key=lambda d: d.level)

        for device in device_instances:
            config = device.viz_config
            legend_elements.append(
                Line2D(
                    [0],
                    [0],
                    color="w",
                    marker=config["marker"],
                    markersize=12,
                    markerfacecolor=config["color"],
                    label=device.role.capitalize(),
                )
            )
        axes.legend(handles=legend_elements, loc="upper left", bbox_to_anchor=(1, 1), title="Legend")
