import logging

logging.basicConfig(level=logging.INFO)
import asyncio, os, time

import json

from datetime import datetime
from aiohttp import web


def index(request):
    return web.Response(body=b'<h1>Awesome</h1>', content_type='text/html')  # 此处content_type添加后正常访问，不添加则下载文件


async def init():
    app = web.Application()  # loop=loop 会提示loop弃用，此处为空
    app.router.add_route('GET', '/', index)
    app_runner = web.AppRunner(app)
    await app_runner.setup()
    srv = web.TCPSite(app_runner, '127.0.0.1', 9000)
    await srv.start()
    logging.info('server started at http://127.0.0.1:9000...')
    return srv


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(init())
    loop.run_forever()
