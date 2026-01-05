from typing import Dict, List
from iot_models import IoTDevice

def group_devices_by_role(nodes: List[IoTDevice]) -> Dict[str, List[str]]:
    """
    Group nodes by their role.

    :return: {
        'sensor': ['S1', 'S2', ...],
        'camera': ['C1', 'C2', ...],
        'hub': ['H1', 'H2', ...],
        'gateway': ['G3', 'G4', ...],
    }
    """
    role_index = {}
    for node in nodes:
        role_index.setdefault(node.role, []).append(node.id)
    return role_index
