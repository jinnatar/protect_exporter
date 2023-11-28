import asyncio
import os

import aiohttp
from absl import app, flags, logging
from prometheus_client import Gauge, Summary, start_http_server

FLAGS = flags.FLAGS

PREFIX = "PROTECT_EXPORTER"

flags.DEFINE_string(
    "url",
    os.getenv(f"{PREFIX}_URL", None),
    "Base url including http(s) to CloudKey endpoint. Do not include /protect/",
)
flags.DEFINE_string("username", os.getenv(f"{PREFIX}_USERNAME", None), "Local username")
flags.DEFINE_string("password", os.getenv(f"{PREFIX}_PASSWORD", None), "Local password")
flags.DEFINE_integer("port", os.getenv(f"{PREFIX}_PORT", 9841), "Port to serve data on")
flags.DEFINE_integer(
    "interval",
    os.getenv(f"{PREFIX}_INTERVAL", 60),
    "Interval in seconds for data polls",
)


def not_null(value):
    return value is not None


flags.register_validator(
    "username", not_null, message="username must be set", flag_values=FLAGS
)
flags.register_validator(
    "password", not_null, message="password must be set", flag_values=FLAGS
)
flags.register_validator("url", not_null, message="url must be set", flag_values=FLAGS)

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
        "host",
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
async def get_data(session):
    return await session.get(FLAGS.url + "/proxy/protect/api/bootstrap")


@PROCESS_TIME.time()
async def extract_metrics(data):
    json = await data.json()
    nvr = json["nvr"]
    name = nvr["name"]

    # NVR info metrics
    NVR_INFO.labels(
        version=nvr["version"],
        mac=nvr["mac"],
        host=nvr["host"],
        name=name,
        firmware=nvr["firmwareVersion"],
    ).set(1)

    # systemInfo metrics
    sys = nvr["systemInfo"]
    cpu = sys["cpu"]
    memory = sys["memory"]
    storage = sys["storage"]
    storage_type = storage["type"]

    NVR_CPU_LOAD_AVERAGE.labels(name).set(cpu["averageLoad"])
    NVR_CPU_TEMPERATURE.labels(name).set(cpu["temperature"])

    NVR_MEMORY_TOTAL.labels(name).set(memory["total"])
    NVR_MEMORY_AVAILABLE.labels(name).set(memory["available"])
    NVR_MEMORY_FREE.labels(name).set(memory["free"])

    NVR_STORAGE_SIZE.labels(name, storage_type).set(storage["size"])
    NVR_STORAGE_AVAILABLE.labels(name, storage_type).set(storage["available"])
    NVR_STORAGE_USED.labels(name, storage_type).set(storage["used"])

    for device in storage["devices"]:
        healthy = 0
        if "healthy" in device and (
            device["healthy"] == "good" or device["healthy"] == "1"
        ):
            healthy = 1
        NVR_STORAGE_INFO.labels(
            nvr=name,
            model=device["model"],
            size=device["size"],
            healthy=healthy,
        ).set(1)

    # Camera info metrics
    for camera in json["cameras"]:
        id = camera["id"]
        name = camera["name"]
        CAMERA_INFO.labels(
            id=id,
            mac=camera["mac"],
            host=camera["connectionHost"],
            ip=camera["host"],
            type=camera["type"],
            name=name,
            hardware_revision=camera["hardwareRevision"],
            firmware=camera["firmwareVersion"],
            build=camera["firmwareBuild"],
        ).set(1)

        if camera["state"] == "CONNECTED":
            connected = 1
        else:
            connected = 0
        CAMERA_CONNECTED.labels(name, id).set(connected)

        if camera["upSince"]:
            CAMERA_UP_TIMESTAMP.labels(name, id).set(camera["upSince"] * 0.001)
        if camera["connectedSince"]:
            CAMERA_CONNECTED_TIMESTAMP.labels(name, id).set(
                camera["connectedSince"] * 0.001
            )
        if camera["lastSeen"]:
            CAMERA_SEEN_TIMESTAMP.labels(name, id).set(camera["lastSeen"] * 0.001)
        if camera["wiredConnectionState"]["phyRate"]:
            CAMERA_CONNECTION_SPEED.labels(name, id).set(
                camera["wiredConnectionState"]["phyRate"]
            )
        elif camera["stats"]["wifi"]["linkSpeedMbps"]:
            CAMERA_CONNECTION_SPEED.labels(name, id).set(
                camera["stats"]["wifi"]["linkSpeedMbps"]
            )
        CAMERA_CONNECTION_RX.labels(name, id).set(camera["stats"]["rxBytes"])
        CAMERA_CONNECTION_TX.labels(name, id).set(camera["stats"]["txBytes"])


async def looper(interval):
    login_data = {"username": FLAGS.username, "password": FLAGS.password}

    async with aiohttp.ClientSession() as session:
        await session.post(FLAGS.url + "/api/auth/login", json=login_data)

        logging.info(f"Querying every {interval} seconds")
        while True:
            data = await get_data(session)
            await extract_metrics(data)
            await asyncio.sleep(interval)


# Wrap asyncio.run for easy compatibilty with absl.app
def main(argv):
    del argv

    start_http_server(FLAGS.port)
    logging.info(f"Serving metrics at :{FLAGS.port}/metrics")
    asyncio.run(looper(FLAGS.interval))


# script endpoint installed by package
def run():
    app.run(main)


if __name__ == "__main__":
    run()
