import os

from absl import flags

FLAGS = flags.FLAGS

PREFIX = "PROTECT_EXPORTER"

# _ = flags.DEFINE_string(
#     "url",
#     os.getenv(f"{PREFIX}_URL", None),
#     "Base url including http(s) to the UniFi device running Protect. Do not include /protect/",
# )
_ = flags.DEFINE_string(
    "protect_host",
    os.getenv(f"{PREFIX}_PROTECT_HOST", None),
    "Host of the device where Protect lives",
)
_ = flags.DEFINE_integer(
    "protect_port",
    os.getenv(f"{PREFIX}_PROTECT_PORT", 443),
    "Port on device where Protect lives",
)
_ = flags.DEFINE_boolean(
    "verify_ssl", os.getenv(f"{PREFIX}_VERIFY_SSL", True), "Verify SSL cert validity"
)
_ = flags.DEFINE_string(
    "username", os.getenv(f"{PREFIX}_USERNAME", None), "Local username"
)
_ = flags.DEFINE_string(
    "password", os.getenv(f"{PREFIX}_PASSWORD", None), "Local password"
)
_ = flags.DEFINE_integer(
    "port", os.getenv(f"{PREFIX}_PORT", 9841), "Port to serve metrics data on"
)
_ = flags.DEFINE_integer(
    "interval",
    os.getenv(f"{PREFIX}_INTERVAL", 60),
    "Interval in seconds for data polls",
)
_ = flags.DEFINE_string(
    "dump_path",
    os.getenv(f"{PREFIX}_DUMP_PATH", None),
    "Path where to dump the raw received data on every poll",
)


def not_null(value: str | int | None):
    return value is not None


flags.register_validator(
    "username", not_null, message="username must be set", flag_values=FLAGS
)
flags.register_validator(
    "password", not_null, message="password must be set", flag_values=FLAGS
)
flags.register_validator(
    "protect_host", not_null, message="protect_host must be set", flag_values=FLAGS
)
