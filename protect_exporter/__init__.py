from absl import app, flags, logging
import json
import os
import time
import requests
import asyncio
import aiohttp
from prometheus_client import start_http_server, Summary, Counter, Gauge

FLAGS = flags.FLAGS

PREFIX = 'PROTECT_EXPORTER'

flags.DEFINE_string('url', os.getenv(f'{PREFIX}_URL', None), 'Base url including http(s) to CloudKey endpoint. Do not include /protect/')
flags.DEFINE_string('username', os.getenv(f'{PREFIX}_USERNAME', None), 'Local username')
flags.DEFINE_string('password', os.getenv(f'{PREFIX}_PASSWORD', None), 'Local password')
flags.DEFINE_integer('port', os.getenv(f'{PREFIX}_PORT', 9841), 'Port to serve data on')
flags.DEFINE_integer('interval', os.getenv(f'{PREFIX}_INTERVAL', 60), 'Interval in seconds for data polls')


def not_null(value):
    return value is not None


flags.register_validator('username',
                         not_null,
                         message='username must be set',
                         flag_values=FLAGS)
flags.register_validator('password',
                         not_null,
                         message='password must be set',
                         flag_values=FLAGS)
flags.register_validator('url',
                         not_null,
                         message='url must be set',
                         flag_values=FLAGS)

REQUEST_TIME = Summary('data_retrieve_seconds', 'Time spent collecting the data')
PROCESS_TIME = Summary('data_processing_seconds', 'Time spent mangling the data')

@REQUEST_TIME.time()
async def get_data(session):
    return await session.get(FLAGS.url + '/proxy/protect/api/bootstrap')

@PROCESS_TIME.time()
async def extract_metrics(data):
    json = await data.json()
    print(json)


async def looper(interval):
    login_data = {'username' : FLAGS.username, 'password' : FLAGS.password}

    async with aiohttp.ClientSession() as session:
        await session.post(FLAGS.url + '/api/auth/login', json=login_data)

        logging.info(f'Querying every {interval} seconds')
        while True:
            data = await get_data(session)
            await extract_metrics(data)
            await asyncio.sleep(interval)

# Wrap asyncio.run for easy compatibilty with absl.app
def main(argv):
    del argv

    start_http_server(FLAGS.port)
    logging.info(f'Serving metrics at :{FLAGS.port}/metrics')
    asyncio.run(looper(FLAGS.interval))



# script endpoint installed by package
def run():
    app.run(main)


if __name__ == '__main__':
    run()


