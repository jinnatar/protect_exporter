from typing import TypeAlias

from absl import logging
from prometheus_client import Gauge, Summary
from uiprotect.data import Bootstrap

JSON: TypeAlias = None | bool | int | float | str | list["JSON"] | dict[str, "JSON"]

# Metrics related to the exporter itself
REQUEST_TIME = Summary("data_retrieve_seconds", "Time spent collecting the data")
PROCESS_TIME = Summary("data_processing_seconds", "Time spent mangling the data")

# Protect metrics
PREFIX = "protect_"
NVR_INFO = Gauge(
    PREFIX + "nvr_info",
    "General NVR information",
    ["version", "mac", "host", "name", "firmware"],
)
NVR_CPU_LOAD_AVERAGE = Gauge(
    PREFIX + "nvr_cpu_load_average", "Load average of the NVR CPU", ["name"]
)
NVR_CPU_TEMPERATURE = Gauge(
    PREFIX + "nvr_cpu_temperature", "Temperature in Celsius of the NVR CPU", ["name"]
)
NVR_MEMORY_TOTAL = Gauge(PREFIX + "nvr_memory_total", "Total NVR memory", ["name"])
NVR_MEMORY_AVAILABLE = Gauge(
    PREFIX + "nvr_memory_available", "Available NVR memory", ["name"]
)
NVR_MEMORY_FREE = Gauge(PREFIX + "nvr_memory_free", "Free NVR memory", ["name"])

NVR_STORAGE_SIZE = Gauge(
    PREFIX + "nvr_storage_size_total", "Total NVR storage size", ["name", "type"]
)
NVR_STORAGE_AVAILABLE = Gauge(
    PREFIX + "nvr_storage_available_total",
    "Total Available NVR storage",
    ["name", "type"],
)
NVR_STORAGE_USED = Gauge(
    PREFIX + "nvr_storage_used_total", "Total used NVR storage", ["name", "type"]
)
NVR_STORAGE_INFO = Gauge(
    PREFIX + "nvr_storage_info",
    "Information about NVR storage devices",
    ["nvr", "model", "size", "healthy"],
)

CAMERA_INFO = Gauge(
    PREFIX + "camera_info",
    "General camera information",
    [
        "id",
        "mac",
        "ip",
        "type",
        "name",
        "hardware_revision",
        "firmware",
        "build",
    ],
)
CAMERA_CONNECTED = Gauge(
    PREFIX + "camera_connected", "Is the camera connected", ["name", "id"]
)
CAMERA_UP_TIMESTAMP = Gauge(
    PREFIX + "camera_up_timestamp", "When the camera last booted", ["name", "id"]
)
CAMERA_CONNECTED_TIMESTAMP = Gauge(
    PREFIX + "camera_connected_timestamp",
    "When the camera last connected",
    ["name", "id"],
)
CAMERA_SEEN_TIMESTAMP = Gauge(
    PREFIX + "camera_seen_timestamp", "When the camera was last seen", ["name", "id"]
)
CAMERA_CONNECTION_SPEED = Gauge(
    PREFIX + "camera_connection_speed",
    "Physical interface speed of camera",
    ["name", "id"],
)
CAMERA_CONNECTION_RX = Gauge(
    PREFIX + "camera_connection_received_total", "Total bytes received", ["name", "id"]
)
CAMERA_CONNECTION_TX = Gauge(
    PREFIX + "camera_connection_transmitted_total",
    "Total bytes transmitted",
    ["name", "id"],
)


@REQUEST_TIME.time()
def extract_metrics(response: Bootstrap) -> None:
    logging.debug(f"Bootstrap: {response}")
    nvr = response.nvr
    name: str = nvr.name or "Unknown"

    # NVR info metrics
    NVR_INFO.labels(
        version=nvr.version,
        mac=nvr.mac,
        host=nvr.host,
        name=name,
        firmware=nvr.firmware_version,
    ).set(1)

    # systemInfo metrics
    sys = nvr.system_info
    cpu = sys.cpu

    NVR_CPU_LOAD_AVERAGE.labels(name).set(cpu.average_load)
    NVR_CPU_TEMPERATURE.labels(name).set(cpu.temperature)

    memory = sys.memory
    NVR_MEMORY_TOTAL.labels(name).set(memory.total or 0)
    NVR_MEMORY_AVAILABLE.labels(name).set(memory.available or 0)
    NVR_MEMORY_FREE.labels(name).set(memory.free or 0)

    storage = sys.storage
    storage_type = storage.type.value
    NVR_STORAGE_SIZE.labels(name, storage_type).set(storage.size)
    NVR_STORAGE_AVAILABLE.labels(name, storage_type).set(storage.available)
    NVR_STORAGE_USED.labels(name, storage_type).set(storage.used)

    for device in storage.devices:
        NVR_STORAGE_INFO.labels(
            nvr=name,
            model=device.model,
            size=device.size,
            healthy=1 if device.healthy else 0,
        ).set(1)

    # Camera info metrics
    for camera in response.cameras.values():
        id = camera.id
        name = camera.name or "Unknown"
        CAMERA_INFO.labels(
            id=id,
            mac=camera.mac,
            ip=camera.host,
            type=camera.type,
            name=name,
            hardware_revision=camera.hardware_revision,
            firmware=camera.firmware_version,
            build=camera.firmware_build,
        ).set(1)

        connected = 1 if camera.state == "CONNECTED" else 0
        CAMERA_CONNECTED.labels(name, id).set(connected)

        if camera.up_since:
            CAMERA_UP_TIMESTAMP.labels(name, id).set(camera.up_since.timestamp())
        if camera.connected_since:
            CAMERA_CONNECTED_TIMESTAMP.labels(name, id).set(
                camera.connected_since.timestamp()
            )
        if camera.last_seen:
            CAMERA_SEEN_TIMESTAMP.labels(name, id).set(camera.last_seen.timestamp())
        if camera.wired_connection_state and camera.wired_connection_state.phy_rate:
            CAMERA_CONNECTION_SPEED.labels(name, id).set(
                camera.wired_connection_state.phy_rate
            )
        elif camera.stats.wifi.link_speed_mbps:
            CAMERA_CONNECTION_SPEED.labels(name, id).set(
                float(camera.stats.wifi.link_speed_mbps)
            )
        if camera.stats:
            # These seem to have gone missing: https://github.com/uilibs/uiprotect/issues/584
            if hasattr(camera.stats, 'rx_bytes'):
                CAMERA_CONNECTION_RX.labels(name, id).set(camera.stats.rx_bytes)
            if hasattr(camera.stats, 'tx_bytes'):
                CAMERA_CONNECTION_TX.labels(name, id).set(camera.stats.tx_bytes)
