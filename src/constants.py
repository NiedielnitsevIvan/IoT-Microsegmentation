"""
Constants and role/protocol definitions for IoT network topology generation.
"""

from typing import Dict, List, Tuple, Iterable

DEFAULT_SEED = 42

Role = str

ROLES: List[Role] = [
    "sensor", "camera", "actuator", "hub", "controller", "nvr", "gateway", "cloud"
]

# Mapping of roles to their protocol "capabilities" per role
ROLE_PROTOCOLS_TX: Dict[Role, List[Tuple[str, int]]] = {
    "sensor": [("MQTT", 1883), ("HTTP", 80), ("CoAP", 5683)],
    "camera": [("RTSP", 554), ("HTTP", 80)],
    "actuator": [("CoAP", 5683), ("HTTP", 80)],
    "hub": [("MQTT", 1883), ("HTTP", 80)],
    "controller": [("CoAP", 5683), ("HTTP", 80), ("HTTPS", 443)],
    "nvr": [("HTTP", 80)],  # mgmt UI, etc.
    "gateway": [("MQTT", 1883), ("HTTPS", 443), ("HTTP", 80)],
    "cloud": [("HTTPS", 443)]
}


# Minimal necessary required functional flows per role-pair for a IoT setup.
REQUIRED_PATTERNS = [
    # sensors publish to gateway via MQTT, allow direct in some deployments
    ("sensor", "gateway", "MQTT", 1883),
    # hub aggregates sensors (optional) -> gateway, upward to gateway
    ("hub", "gateway", "MQTT", 1883),
    # local aggregation path
    ("sensor", "hub", "MQTT", 1883),
    # gateway -> cloud, upstream management/telemetry
    ("gateway", "cloud", "HTTPS", 443),
    # camera streams to NVR
    ("camera", "nvr", "RTSP", 554),
    # controller commands actuator (CoAP) — command-and-control
    ("controller", "actuator", "CoAP", 5683),
    # controller may query via HTTPS some cloud API
    ("controller", "cloud", "HTTPS", 443),
]

# Pair-wise noise probabilities baseline (before scaling), higher within plausible pairs
# Values are *relative* and will be multiplied by --noise_scale and normalized per src.
ROLE_PAIR_NOISE_BASE: Dict[Tuple[Role, Role], float] = {
    ("sensor", "hub"): 0.30,
    ("sensor", "gateway"): 0.20,
    ("sensor", "sensor"): 0.02,
    ("sensor", "camera"): 0.02,
    ("sensor", "actuator"): 0.05,

    ("camera", "nvr"): 0.30,
    ("camera", "gateway"): 0.10,
    ("camera", "camera"): 0.02,
    ("camera", "sensor"): 0.02,

    ("actuator", "controller"): 0.10,
    ("actuator", "gateway"): 0.05,
    ("actuator", "actuator"): 0.02,

    ("hub", "gateway"): 0.25,
    ("hub", "hub"): 0.05,
    ("hub", "sensor"): 0.05,

    ("controller", "actuator"): 0.30,
    ("controller", "gateway"): 0.15,
    ("controller", "cloud"): 0.10,
    ("controller", "controller"): 0.05,

    ("nvr", "gateway"): 0.10,
    ("nvr", "controller"): 0.05,

    ("gateway", "cloud"): 0.20,
    ("gateway", "gateway"): 0.05,

    # Cloud rarely initiates to on-prem by design (but may have mgmt callbacks)
    ("cloud", "gateway"): 0.03,
}

# Role prefixes for concise representation on the topology plots
ROLE_PREFIXES_MAP = {
    "sensor": "S",
    "camera": "C",
    "actuator": "A",
    "hub": "H",
    "controller": "K",
    "nvr": "N",
    "gateway": "G",
    "cloud": "CL"
}
