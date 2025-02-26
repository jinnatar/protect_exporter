import asyncio

from absl import app, logging
from prometheus_client import start_http_server
from uiprotect import ProtectApiClient
from uiprotect.data import Bootstrap

from . import FLAGS, metrics


async def looper(interval: int) -> None:
    protect = ProtectApiClient(
        FLAGS.protect_host,
        FLAGS.protect_port,
        FLAGS.username,
        FLAGS.password,
        verify_ssl=FLAGS.verify_ssl,
    )
    bootstrap: Bootstrap = await protect.update()
    logging.info(f"Found NVR: {bootstrap.nvr.name}")
    logging.info(f"Starting update loop with interval: {FLAGS.interval}s")

    while True:
        metrics.extract_metrics(bootstrap)
        await asyncio.sleep(interval)
        bootstrap = await protect.update()


# Wrap asyncio.run for easy compatibilty with absl.app
def main(argv: list[str]):
    del argv

    _ = start_http_server(FLAGS.port)
    logging.info(f"Serving metrics at :{FLAGS.port}/metrics")
    asyncio.run(looper(FLAGS.interval))


# script endpoint installed by package
def run():
    app.run(main)


if __name__ == "__main__":
    run()
