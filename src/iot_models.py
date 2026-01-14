"""
IoT Models Definition.

Defines various IoT device types with their properties and behaviors.
"""

from abc import ABC, abstractmethod


class IoTDevice(ABC):
    """
    Base class for IoT devices in the network topology.

    Each device has an ID, zone, and role-specific properties.
    """

    def __init__(
        self,
        node_id: str,
        zone: int = None,
        **kwargs
    ):
        self.id = node_id
        self.zone = zone
        self.extra_attrs = kwargs

    @property
    @abstractmethod
    def role(self) -> str:
        """
        Defines the role of the device in the network.
        Examples: "sensor", "camera", "actuator", "hub", "nvr", "controller", "gateway", "cloud"
        """
        pass

    @property
    @abstractmethod
    def level(self) -> int:
        """
        Hierarchical level of the device in the network.
            1 - Edge (Sensors, Cameras, Actuators)
            2 - Aggregation (Hubs, NVRs)
            3 - Egress (Gateways)
            4 - Cloud
        """
        pass

    @property
    def is_isolated_peer(self) -> bool:
        """
        Returns whether this device is prohibited from peer-to-peer communication.
        Default: True for level 1, False for others.
        """
        return self.level == 1

    @property
    def can_receive_commands(self) -> bool:
        """
        Returns whether this device can receive commands from higher levels (Downstream).
        """
        return True

    @property
    def viz_config(self) -> dict:
        """
        Visualization configuration for plotting the device in network graphs.
        Default configuration for unknown device types.
        """
        return {
            "color": "tab:gray",
            "marker": "o",
            "zorder": 1
        }

    @property
    def criticality(self) -> float:
        """
        Returns the criticality score of the device.

        By default, it's dependent on the device level.
        """
        return float(self.level) * 2.5 / 10.0  # Normalize to [0.25, 1.0]

    def __repr__(self):
        return f"<{self.__class__.__name__} id={self.id} zone={self.zone}>"


class Sensor(IoTDevice):
    """
    Represents a Sensor device in the IoT network.

    Sensors are typically read-only devices that collect data.
    """

    @property
    def role(self):
        return "sensor"

    @property
    def level(self):
        return 1

    @property
    def can_receive_commands(self):
        return False

    @property
    def criticality(self) -> float:
        """
        Sensors passively collect data and loss of a sensor is less critical.
        """
        return 0.4

    @property
    def viz_config(self):
        return {
            "color": "tab:blue",
            "marker": "o",  # circle
            "zorder": 2
        }


class Camera(IoTDevice):
    """
    Represents a Camera device in the IoT network.

    Cameras are typically read-only devices that stream video data.
    """

    @property
    def role(self):
        return "camera"

    @property
    def level(self):
        return 1

    @property
    def can_receive_commands(self):
        return False

    @property
    def criticality(self) -> float:
        """
        Cameras are less critical because they are read-only devices,
        and the loss of a camera cannot directly affect the control
        of the entire system.
        """
        return 0.3

    @property
    def viz_config(self):
        return {
            "color": "tab:orange",
            "marker": "p",  # pentagon
            "zorder": 2
        }


class Actuator(IoTDevice):
    """
    Represents an Actuator device in the IoT network.

    Actuators can receive commands to perform actions.
    """

    @property
    def role(self):
        return "actuator"

    @property
    def level(self):
        return 1

    @property
    def can_receive_commands(self):
        return True

    @property
    def criticality(self) -> float:
        """
        Actuators can directly affect the physical environment,
        so is can affect the overall system's operation.
        """
        return 0.6

    @property
    def viz_config(self):
        return {
            "color": "tab:green",
            "marker": "s",  # square
            "zorder": 2
        }


class Hub(IoTDevice):
    """
    Represents a Hub device in the IoT network.

    Hubs aggregate data from edge devices.
    """

    @property
    def role(self):
        return "hub"

    @property
    def level(self):
        return 2

    @property
    def criticality(self) -> float:
        """
        Hubs aggregate data and have a crucial role in data flow within the network.
        """
        return 0.7

    @property
    def viz_config(self):
        return {
            "color": "tab:red",
            "marker": "D",  # diamond
            "zorder": 3
        }


class NVR(IoTDevice):
    """
    Represents a Network Video Recorder (NVR) device in the IoT network.

    NVRs store and manage video data from cameras.
    """

    @property
    def role(self):
        return "nvr"

    @property
    def level(self):
        return 2

    @property
    def criticality(self) -> float:
        """
        NVRs usually have access to a large number of cameras.
        They are powerful nodes for launching attacks within the network,
        so their weight should be high.
        """
        return 0.8

    @property
    def viz_config(self):
        return {
            "color": "tab:brown",
            "marker": "v",  # triangle_down
            "zorder": 3
        }


class Controller(IoTDevice):
    """
    Represents a Controller device in the IoT network.

    Controllers manage and coordinate edge devices.
    """

    @property
    def role(self):
        return "controller"

    @property
    def level(self):
        return 2

    @property
    def criticality(self) -> float:
        """
        Controllers have significant control over edge devices,
        attacks or incorrect pruning here can have serious consequences.
        """
        return 1

    @property
    def viz_config(self):
        return {
            "color": "tab:purple",
            "marker": "8",  # octagon
            "zorder": 3
        }


class Gateway(IoTDevice):
    """
    Represents a Gateway device in the IoT network.

    Gateways connect the local network to external networks (e.g., cloud).
    """

    @property
    def role(self):
        return "gateway"

    @property
    def level(self):
        return 3

    @property
    def criticality(self) -> float:
        """
        Gateways are crucial because they serve as a bridge between
        networks. Attacks on gateways can compromise the entire network.
        """
        return 0.95

    @property
    def viz_config(self):
        return {
            "color": "tab:pink",
            "marker": "h",  # hexagon1
            "zorder": 4
        }


class Cloud(IoTDevice):
    """
    Represents a Cloud device in the IoT network.
    Cloud devices provide centralized processing and storage.
    """

    @property
    def role(self):
        return "cloud"

    @property
    def level(self):
        return 4

    @property
    def criticality(self) -> float:
        """
        Cloud services are critical for data storage and processing.
        Attacks on the cloud usually result in data leaks,
        but may not cause physical damage so slightly less critical than controllers/gateways.
        """
        return 0.9

    @property
    def viz_config(self):
        return {
            "color": "tab:gray",
            "marker": "H",  # hexagon2
            "zorder": 5
        }


class DeviceFactory:
    """
    Factory Pattern for IoTDevice creation.
    """

    _MAPPING = {
        "sensor": Sensor,
        "actuator": Actuator,
        "camera": Camera,
        "nvr": NVR,
        "controller": Controller,
        "hub": Hub,
        "gateway": Gateway,
        "cloud": Cloud
    }

    @staticmethod
    def create(
        role: str,
        node_id: str,
        zone: int = None,
        **kwargs
    ) -> IoTDevice:
        """
        Factory method to create IoTDevice instances based on role.
        """
        if cls := DeviceFactory._MAPPING.get(role.lower()):
            return cls(node_id, zone, **kwargs)

        print(f"Warning: Unknown role '{role}' for node {node_id}. Defaulting to generic IoTDevice.")
        raise ValueError(f"Unknown device role: {role}")

    @staticmethod
    def get_all_classes():
        """
        Returns a list of all IoTDevice classes available in the factory.
        """
        return list(DeviceFactory._MAPPING.values())
