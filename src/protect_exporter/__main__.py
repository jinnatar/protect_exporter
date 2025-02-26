import asyncio
from http.cookies import SimpleCookie

import aiohttp
from absl import app, flags, logging
from prometheus_client import start_http_server

from . import FLAGS, metrics


def not_null(value):
    return value is not None


flags.register_validator(
    "username", not_null, message="username must be set", flag_values=FLAGS
)
flags.register_validator(
    "password", not_null, message="password must be set", flag_values=FLAGS
)
flags.register_validator("url", not_null, message="url must be set", flag_values=FLAGS)


@metrics.REQUEST_TIME.time()
async def get_data(session):
    logging.debug("Session cookie_jar:")
    for cookie in session.cookie_jar:
        logging.debug(f"Cookie: {cookie}")
    return await session.get(FLAGS.url + "/proxy/protect/api/bootstrap")


async def looper(interval):
    login_data = {"username": FLAGS.username, "password": FLAGS.password}

    async with aiohttp.ClientSession() as session:
        response = await session.post(FLAGS.url + "/api/auth/login", data=login_data)
        # Protect sends non-standard cookies with the 'partitioned' field which
        # are not slated for support until the unreleased python 3.13.
        # so we handle it very manually.
        cookie = SimpleCookie()
        logging.debug(f"Cookie header: {response.headers['Set-Cookie']}")
        cookie.load(response.headers["Set-Cookie"].replace("partitioned", ""))
        logging.debug(f"Extracted cookie: {cookie}")
        session.cookie_jar.update_cookies(cookie)

        logging.info(f"Querying every {interval} seconds.")
        while True:
            data = await get_data(session)
            await metrics.extract_metrics(data)
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
