# import asyncio
import asyncio
import functools
import inspect
import logging
import os
from urllib import parse

from aiohttp import web

from apis import APIError

"""
视图函数（URL处理函数）
"""


def get(path):
    '''
        Define decorator @get('/path')
    '''

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)

        wrapper.__method__ = "GET"
        wrapper.__route__ = path
        return wrapper

    return decorator


def post(path):
    '''
        Define decorator @get('/path')
    '''

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)

        wrapper.__method__ = "POST"
        wrapper.__route__ = path
        return wrapper

    return decorator


# 使用inspect模块，检查视图函数的参数

# inspect.Parameter.kind 类型：
# POSITIONAL_ONLY          位置参数
# KEYWORD_ONLY             命名关键词参数
# VAR_POSITIONAL           可选参数 *args
# VAR_KEYWORD              关键词参数 **kw
# POSITIONAL_OR_KEYWORD    位置或必选参数

def get_required_kwargs(fn):
    """
   获取函数命名关键字参数，且非默认参数

   :param fn: function
   :return:
    """

    args = []

    # 获取函数 fn 的参数，ordered mapping
    params = inspect.signature(fn).parameters
    for name, param in params.items():
        # * 或者 *args 后面的参数
        if param.kind == param.KEYWORD_ONLY:
            args.append(name)
    return tuple(args)


def get_named_kwargs(fn):
    """
    获取函数命名关键字参数

    :param fn: function
    :return:
    """
    args = []
    # 获取函数 fn 的参数，ordered mapping
    params = inspect.signature(fn).parameters
    for name, param in params.items():
        # * 或者 *args 后面的参数
        if param.kind == param.KEYWORD_ONLY:
            args.append(name)
    return tuple(args)


def has_named_kwarg(fn):
    """
    判断是否有命名关键字参数

    :param fn: function
    :return:
    """
    # 获取函数 fn 的参数，ordered mapping
    params = inspect.signature(fn).parameters
    for name, param in params.items():
        # * 或者 *args 后面的参数
        if param.kind == param.KEYWORD_ONLY:
            return True


def has_var_kwarg(fn):
    """
    判断是否有关键字参数

    :param fn: function
    :return:
    """
    # 获取函数 fn 的参数，ordered mapping
    params = inspect.signature(fn).parameters
    for name, param in params.items():
        # **args 后面的参数
        if param.kind == param.VAR_KEYWORD:
            return True


def has_request_arg(fn):
    """
    判断是否有请求参数

    :param fn: function
    :return:
    """
    # 获取函数 fn 的签名
    sig = inspect.signature(fn)
    # 获取函数 fn 的参数，ordered mapping
    params = sig.parameters
    found = False
    for name, param in params.items():
        if name == 'request':
            found = True
            continue
        if found and (param.kind is not param.VAR_POSITIONAL and
                      param.kind is not param.KEYWORD_ONLY and
                      param.kind is not param.VAR_KEYWORD):
            # fn(*args, **kwargs)，fn 为 fn.__name__，(*args, **kwargs) 为 sig
            raise ValueError(
                'Request parameter must be the last named parameter in function: %s%s' % (fn.__name__, str(sig)))
    return found


class RequestHandler(object):
    """
    RequestHandler
    需要处理以下问题：
    1、确定HTTP请求的方法（’POST’or’GET’）（用request.method获取）
    2、根据HTTP请求的content_type字段，选用不同解析方法获取参数。（用request.content_type获取）
    3、将获取的参数经处理，使其完全符合视图函数接收的参数形式
    4、调用视图函数
    """

    def __init__(self, app, fn):

        self.__app = app
        self.__func = fn
        self.__has_request_arg = has_request_arg(fn)  # 判断是否有请求参数
        self.__has_var_kwarg = has_var_kwarg(fn)  # 判断是否有关键字参数
        self.__has_named_kwarg = has_named_kwarg(fn)  # 判断是否有命名关键字参数
        self.__named_kwargs = get_named_kwargs(fn)  # 获取函数命名关键字参数
        self.__required_kwargs = get_required_kwargs(fn)  # 获取函数命名关键字参数，且非默认参数

    # Make RequestHandler callable
    # 1.定义kw，用于保存参数
    # 2.判断视图函数是否存在关键词参数，如果存在根据POST或者GET方法将request请求内容保存到kw
    # 3.如果kw为空（说明request无请求内容），则将match_info列表里的资源映射给kw；若不为空，把命名关键词参数内容给kw
    # 4.完善_has_request_arg和_required_kw_args属性
    async def __call__(self, request):
        # 1.定义kw，用于保存参数
        kwargs = None
        # 2.判断视图函数是否存在关键词参数，如果存在根据POST或者GET方法将request请求内容保存到kw
        if self.__has_var_kwarg or self.__has_named_kwarg or self.__required_kwargs:
            # 如果是POST，则进行数据类型的判断，并将数据保存到kwargs中
            if request.method == 'POST':
                # 不存在Content-Type，返回报错
                if not request.content_type:
                    return web.HTTPBadRequest(text='Missing Content-Type.')
                ct = request.content_type.lower()
                # JSON 数据格式
                if ct.startswith('application/json'):
                    # Read request body decoded as json
                    params = await request.json()
                    if not isinstance(params, dict):
                        return web.HTTPBadRequest(text='JSON body must be dict object.')
                    kwargs = params
                # form 表单数据被编码为 key/value 格式发送到服务器（表单默认的提交数据的格式）
                elif ct.startswith('application/x-www-form-urlencoded') or ct.startswith('multipart/form-data'):
                    # Read POST parameters from request body
                    params = await request.post()
                    kwargs = dict(**params)
                else:
                    return web.HTTPBadRequest(text='Unsupported Content-Type: %s' % request.content_type)
            # 如果是GET请求，将相关参数放到kwargs
            if request.method == 'GET':
                # The query string in the URL, e.g., id=10
                qs = request.query_string
                if qs:
                    kwargs = dict()
                    # {'id': ['10']}
                    for k, v in parse.parse_qs(qs, True).items():
                        kwargs[k] = v[0]
        # 3.如果kw为空（说明request无请求内容），则将match_info列表里的资源映射给kw；若不为空，把命名关键词参数内容给kw
        if kwargs is None:
            kwargs = dict(**request.match_info)
        else:
            if not self.__has_var_kwarg and self.__named_kwargs:
                # Remove all unnamed kwargs
                copy = dict()
                for name in self.__named_kwargs:
                    if name in kwargs:
                        copy[name] = kwargs[name]
                kwargs = copy
            # Check named kwargs
            for k, v in request.match_info.items():
                if k in kwargs:
                    logging.warning('Duplicate arg name in named kwargs and kwargs: %s' % k)
                kwargs[k] = v
        # 4.完善_has_request_arg和_required_kwargs属性
        if self.__has_request_arg:
            kwargs['request'] = request
        # Check required kwargs
        if self.__required_kwargs:
            for name in self.__required_kwargs:
                # 若未传入必须参数值，报错。
                if name not in kwargs:
                    return web.HTTPBadRequest(text='Missing argument: %s' % name)
        logging.info('Call with kwargs: %s' % str(kwargs))
        try:
            r = await self.__func(**kwargs)
            return r
        except APIError as e:
            return dict(error=e.error, data=e.data, message=e.message)


# 添加静态文件，如image，css，javascript等
def add_static(app):
    # 拼接static文件目录
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static')
    # path = os.path.join(os.path.abspath('.'), 'static')

    app.router.add_static('/static/', path)
    logging.info('add static %s => %s' % ('/static/', path))


# 编写一个add_route函数，用来注册一个视图函数
def add_route(app, fn):
    """
    add_route函数每次只能注册一个视图函数。
    若要批量注册视图函数，需要编写一个批注册函数add_routes

    1、验证视图函数是否拥有method和path参数
    2、将视图函数转变为协程
    :param app:
    :param fn:
    :return:
    """
    method = getattr(fn, '__method__', None)
    path = getattr(fn, '__route__', None)
    if method is None or path is None:
        raise ValueError('@get or @post not defined in %s.' % fn.__name__)
    # 判断URL处理函数是否协程并且是生成器 （先版本似乎会自动会转换成协程）
    # if not asyncio.iscoroutinefunction(fn) and not inspect.isgeneratorfunction(fn):
    #     # 将fn转变成协程
    #     fn = asyncio.coroutine(fn)
    logging.info(
        'add route %s %s => %s(%s)' % (method, path, fn.__name__, ','.join(inspect.signature(fn).parameters.keys())))
    # 在app中注册经RequestHandler类封装的视图函数
    app.router.add_route(method, path, RequestHandler(app, fn))


# 导入模块，批量注册视图函数
def add_routes(app, module_name):
    n = module_name.rfind('.')  # 从右侧检索，返回索引。若无，返回-1。
    # 导入整个模块
    if n == -1:
        # __import__ 作用同import语句，但__import__是一个函数，并且只接收字符串作为参数
        # __import__('os',globals(),locals(),['path','pip'], 0) ,等价于from os import path, pip
        mod = __import__(module_name, globals(), locals, [], 0)
    else:
        name = module_name[(n + 1):]
        # 只获取最终导入的模块，为后续调用dir()
        mod = getattr(__import__(module_name[:n], globals(), locals, [name], 0), name)
    for attr in dir(mod):  # dir()迭代出mod模块中所有的类，实例及函数等对象,str形式
        if attr.startswith('_'):
            continue  # 忽略'_'开头的对象，直接继续for循环
        fn = getattr(mod, attr)
        # 确保是函数
        if callable(fn):
            # 确保视图函数存在method和path
            method = getattr(fn, '__method__', None)
            path = getattr(fn, '__route__', None)
            if method and path:
                # 注册
                add_route(app, fn)
