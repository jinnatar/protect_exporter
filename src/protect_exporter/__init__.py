import os

from absl import flags

FLAGS = flags.FLAGS

PREFIX = "PROTECT_EXPORTER"

flags.DEFINE_string(
    "url",
    os.getenv(f"{PREFIX}_URL", None),
    "Base url including http(s) to the UniFi device running Protect. Do not include /protect/",
)
flags.DEFINE_string("username", os.getenv(f"{PREFIX}_USERNAME", None), "Local username")
flags.DEFINE_string("password", os.getenv(f"{PREFIX}_PASSWORD", None), "Local password")
flags.DEFINE_integer("port", os.getenv(f"{PREFIX}_PORT", 9841), "Port to serve data on")
flags.DEFINE_integer(
    "interval",
    os.getenv(f"{PREFIX}_INTERVAL", 60),
    "Interval in seconds for data polls",
)
