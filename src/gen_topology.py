import json

from pathlib import Path
from typing import Dict, List, Set, Tuple
from numpy.random import default_rng, Generator

from constants import (
    DEFAULT_SEED,
    Role,
    ROLES,
    ROLE_PROTOCOLS_TX,
    REQUIRED_PATTERNS,
    ROLE_PAIR_NOISE_BASE,
    ROLE_PREFIXES_MAP
)
from iot_models import DeviceFactory, IoTDevice
from utils import group_devices_by_role


class TopologyGenerator:
    """
    Generate a role-aware IoT topology with functional core and controlled noise.

    Steps:
        1. Build devices with roles and zones.
        2. Add required functional edges deterministically.
        3. Add noise edges probabilistically based on role-pair probabilities,
           preferential attachment, and zone affinity.
        4. Save topology to JSON.
    """

    def __init__(
        self,
        seed: int = DEFAULT_SEED,
        n_sensors: int = 20,
        n_cameras: int = 8,
        n_actuators: int = 8,
        n_hubs: int = 3,
        n_controllers: int = 3,
        n_nvr: int = 2,
        n_gateways: int = 1,
        n_cloud: int = 1,
        n_zones: int = 4,
        noise_scale: float = 1.0,
        max_extra_out_per_device: int = 6,
        max_extra_in_per_device: int = 20,
        zone_affinity_weight: float = 5.0,
        preferential_attachment_power: float = 1.2,
    ):
        stringified_noise = f"{noise_scale:.2f}".replace('.', '_')
        self.out_json: str = f"data/topology_{seed}_{stringified_noise}.json"
        self.seed = seed
        self.n_sensors = n_sensors
        self.n_cameras = n_cameras
        self.n_actuators = n_actuators
        self.n_hubs = n_hubs
        self.n_controllers = n_controllers
        self.n_nvr = n_nvr
        self.n_gateways = n_gateways
        self.n_cloud = n_cloud
        self.n_zones = n_zones
        self.noise_scale = noise_scale
        self.max_extra_out_per_device = max_extra_out_per_device
        self.max_extra_in_per_device = max_extra_in_per_device
        self.zone_affinity_weight = zone_affinity_weight
        self.pa_power = preferential_attachment_power
        self.random_generator = default_rng(self.seed)

    def generate_topology(self) -> Dict:
        """
        Generate a role-aware topology with guaranteed functional core and controlled noise.

        - noise_scale: scales the role-pair noise matrix (0 = deterministic core only; 1 = default; >1 = noisier)
        - max_extra_out_per_device / max_extra_in_per_device: hard caps for noise degree per device
        """
        # Build devices and assign them to ZONES
        devices = self._create_devices()
        idx = group_devices_by_role(devices)
        devices_map = {
            device.id: device
            for device in devices
        }
        # Create required core edges
        core_edges_dicts = self._add_required_core(idx, devices_map)

        current_in_degree = {
            device.id: 0
            for device in devices
        }
        existing_edges_set = set()
        for e in core_edges_dicts:
            current_in_degree[e['dst']] += 1
            existing_edges_set.add(
                (e["src"], e["dst"], e["proto"], int(e["port"]))
            )

        # Create noise edges
        noise_edges_dicts = self._sample_calibrated_noise_edges(
            devices=devices,
            idx=idx,
            devices_map=devices_map,
            existing_edges_set=existing_edges_set,
            current_in_degree=current_in_degree
        )

        nodes = [
            {
                "id": device.id,
                "role": device.role,
                "zone": device.zone,
            }
            for device in devices
        ]
        topo = {
            "nodes": nodes,
            "edges": core_edges_dicts + noise_edges_dicts
        }

        out_path = Path(self.out_json)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(topo, indent=2), encoding="utf-8")
        print(f"Topology generated successfully and saved to {self.out_json}")

        return topo

    def _create_devices(self) -> List[IoTDevice]:
        """
        Build list of devices with assigned roles and unique IDs.
        """
        devices = []
        role_counts = {
            "sensor": self.n_sensors,
            "camera": self.n_cameras,
            "actuator": self.n_actuators,
            "hub": self.n_hubs,
            "controller": self.n_controllers,
            "nvr": self.n_nvr,
            "gateway": self.n_gateways,
            "cloud": self.n_cloud,
        }
        for role, count in role_counts.items():
            for node_id in self._make_ids(ROLE_PREFIXES_MAP[role], count):
                if role == 'cloud':  # Cloud is zone-agnostic
                    zone = 0
                else:
                    zone = self.random_generator.integers(1, self.n_zones + 1)

                device = DeviceFactory.create(
                    role=role,
                    node_id=node_id,
                    zone=int(zone),
                )
                devices.append(device)
        return devices

    @staticmethod
    def _make_ids(prefix: str, count: int) -> List[str]:
        return [f"{prefix}{i}" for i in range(1, count + 1)]

    def _add_required_core(self, idx: Dict[Role, List[str]], devices_map: Dict[str, IoTDevice]) -> List[Dict]:
        """
        Deterministically add functional edges.

        Respect ZONES where possible.
        """
        edges: List[Dict] = []

        def find_best_target(src_id, target_role):
            """
            Helper to find target in same zone, fallback to random.
            """
            targets = idx.get(target_role, )
            if not targets:
                return None

            src_zone = devices_map[src_id].zone
            # Filter targets in same zone
            local_targets = [
                t for t in targets
                if devices_map[t].zone == src_zone
            ]

            if local_targets:
                return self.random_generator.choice(local_targets)
            return self.random_generator.choice(targets)


        # 1) Sensor -> Hub (MQTT:1883)
        for sensor_id in idx.get("sensor", []):
            if hub_id := find_best_target(sensor_id, "hub"):
                edges.append({"src": sensor_id, "dst": str(hub_id), "proto": "MQTT", "port": 1883})

        # 2) Hub -> Gateway (MQTT:1883)
        for hub_id in idx.get("hub", []):
            if gateway_id := find_best_target(hub_id, "gateway"):
                edges.append({"src": hub_id, "dst": str(gateway_id), "proto": "MQTT", "port": 1883})

        # 3) Gateway -> Cloud (HTTPS:443)
        for cloud_id in idx.get("cloud", []):
            for gateway_id in idx.get("gateway", []):
                edges.append({"src": gateway_id, "dst": str(cloud_id), "proto": "HTTPS", "port": 443})

        # 4) Camera -> NVR (RTSP:554)
        for cam_id in idx.get("camera", ):
            if nvr_id := find_best_target(cam_id, "nvr"):
                edges.append({"src": cam_id, "dst": str(nvr_id), "proto": "RTSP", "port": 554})

        # 5) Controller -> Actuator (CoAP:5683)
        # One controller might manage multiple actuators in its zone
        for controller in idx.get("controller", ):
            controller_zone = devices_map[controller].zone
            local_actuators = [
                actuator for actuator in idx.get("actuator", [])
                if devices_map[actuator].zone == controller_zone
            ]
            if not local_actuators:
                continue

            target_actuators = self.random_generator.choice(
                local_actuators,
                size=min(len(local_actuators), 2),
                replace=False
            )
            for target in target_actuators:
                edges.append({"src": controller, "dst": str(target), "proto": "CoAP", "port": 5683})

        return edges

    def _sample_calibrated_noise_edges(
        self,
        devices: List[IoTDevice],
        idx: Dict,
        devices_map: Dict,
        existing_edges_set: Set,
        current_in_degree: Dict[str, int]
    ) -> List[Dict]:
        """
        Add plausible "extra" edges using role-pair probabilities and degree caps.
        We avoid O(N^2) by sampling a bounded number per device.

        Change: after selecting a destination role by relative weights, perform an
        acceptance check using the *raw* scaled score (prob_matrix entry) so that
        increasing `noise_scale` increases the absolute chance to add an edge.
        """
        new_edges = []
        prob_matrix = self._role_pair_prob_matrix()

        for src_device in devices:
            # Skip cloud as source for noise (usually)
            if src_device.role == "cloud":
                continue

            # Budget for noise edges
            attempts = int(self.max_extra_out_per_device * self.noise_scale)
            if attempts <= 0:
                continue

            # Identify valid target ROLES first
            valid_target_roles = [r for r in ROLES if (src_device.role, r) in prob_matrix]

            if not valid_target_roles:
                continue

            for _ in range(attempts):
                # 1. Pick a Target Role based on base probability
                role_weights = [prob_matrix.get((src_device.role, r), 0.0) for r in valid_target_roles]
                total_weight = sum(role_weights)
                if total_weight == 0:
                    break

                # Normalize
                p_roles = [w / total_weight for w in role_weights]
                target_role = self.random_generator.choice(valid_target_roles, p=p_roles)

                # Global acceptance check (noise scale control)
                base_prob = prob_matrix.get((src_device.role, target_role), 0.0)
                if self.random_generator.random() > base_prob:
                    continue

                # 2. Select specific Target Node using Preferential Attachment & Zone Affinity
                candidates = idx.get(target_role, )
                candidates = [c for c in candidates if c != src_device.id]  # No self-loops

                if not candidates:
                    continue

                candidate_scores = []
                for cand in candidates:
                    # A. Scale-Free Component (Preferential Attachment)
                    # Score ~ (Current Degree + 1) ^ Power
                    # Adding 1 ensures devices with 0 degree still have a chance
                    degree_score = (current_in_degree[cand] + 1) ** self.pa_power

                    # B. Small-World Component (Zone Affinity)
                    cand_zone = devices_map[cand].zone
                    zone_score = self.zone_affinity_weight if cand_zone == src_device.zone else 1.0

                    # Combine scores
                    final_score = degree_score * zone_score

                    # Check In-Degree Cap (hard limit)
                    if current_in_degree[cand] >= self.max_extra_in_per_device:
                        final_score = 0.0

                    candidate_scores.append(final_score)

                # Normalize candidate scores to probabilities
                total_cand_score = sum(candidate_scores)
                if total_cand_score == 0: continue

                cand_probs = [s / total_cand_score for s in candidate_scores]

                # Select Target
                dst = self.random_generator.choice(candidates, p=cand_probs)

                # 3. Protocol Selection
                proto, port = self._choose_proto_for_pair(src_device.role, target_role, self.random_generator)

                # Check duplicate
                edge_key = (src_device.id, str(dst), proto, int(port))
                if edge_key in existing_edges_set:
                    continue

                # Add Edge
                new_edges.append({
                    "src": src_device.id,
                    "dst": str(dst),
                    "proto": proto,
                    "port": int(port),
                    "extra": 1
                })
                existing_edges_set.add(edge_key)
                # Update degree immediately for "Rich get Richer" effect
                current_in_degree[dst] += 1

        return new_edges


    def _role_pair_prob_matrix(self) -> Dict[Tuple[Role, Role], float]:
        """
        Scale base role-pair noise probabilities.
        """
        return {pair: prob * self.noise_scale for pair, prob in ROLE_PAIR_NOISE_BASE.items()}

    @staticmethod
    def _choose_proto_for_pair(src_role: Role, dst_role: Role, random_generator: Generator) -> Tuple[str, int]:
        """
        Pick a protocol/port that is plausible for src_role; could be refined per pair.
        """
        candidates = ROLE_PROTOCOLS_TX.get(src_role, [])
        if not candidates:
            return "TCP", 0
        # Prefer canonical pairs when they exist
        for (r_src, r_dst, p, port) in REQUIRED_PATTERNS:
            if r_src == src_role and r_dst == dst_role:
                return p, port
        return candidates[int(random_generator.integers(0, len(candidates)))]

    @staticmethod
    def _even_map_sources_to_targets(src_ids: List[str], dst_ids: List[str]) -> Dict[str, List[str]]:
        """
        Evenly distribute each source to one or more targets (round-robin).
        Returns mapping src -> [a few dst], default fanout = 1 (one target).
        """
        mapping = {src: [] for src in src_ids}
        if not dst_ids:
            return mapping
        for i, src in enumerate(src_ids):
            mapping[src].append(dst_ids[i % len(dst_ids)])
        return mapping
