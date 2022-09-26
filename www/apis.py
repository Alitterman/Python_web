import asyncio
import functools
import inspect

import logging
import requests
import parser


class RequestHandler(object):
    def __init__(self, app, fn):
        self.__app = app
        self.__func = fn

    async def __call__(self, request):
        # noinspection PyUnresolvedReferences
        r = await self.__func(**kwargs)
        return r


def add_route(app, fn):
    method = getattr(fn, 'method', None)
    path = getattr(fn, 'path', None)
    if path is None or method is None:
        raise ValueError("@get or @post not defined in %s" % str(fn))
    logging.info('add route %s %s => %s(%s)',
                 (method, path, fn.__name__, ','.join(inspect.signature(fn).parameters.keys())))
    app.router.add_route(method, path, RequestHandler(app, fn))


def add_routes(app, module_name):
    n = module_name.rfind('.')
    if n == (-1):
        mod = __import__(module_name, globals(), locals())
    else:
        name = module_name[n + 1:]
        mod = getattr(__import__(module_name[:n], globals(), locals(), [name]), name)
    for attr in dir(mod):
        if attr.startswith('_'):
            continue
        fn = getattr(mod, attr)
        if callable(fn):
            method = getattr(fn, '__method__', None)
            path = getattr(fn, '__route__', None)
            if method and path:
                add_route(app, fn)


class APIError:
    pass
