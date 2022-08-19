import aiomysql, asyncio
from logging import info, debug, warning

import pymysql.err

global __pool


def log(sql, args=()):
    info('SQL: %s' % sql)


async def create_pool(loop, **kw):
    """
    创建数据库连接池
    :param loop:
    :param kw:键值对参数
    :return:
    """
    info('create database connection pool...')
    global __pool
    # 携程创建数据库，并设为全局变量
    __pool = await aiomysql.create_pool(
        host=kw.get('host', 'localhost'),
        port=kw.get('port', 3306),
        user=kw['user'],
        password=kw['password'],
        db=kw['db'],
        charset=kw.get('charset', 'utf8'),
        autocommit=kw.get('autocommit', True),
        maxsize=kw.get('maxsize', 10),
        minsize=kw.get('minsize', 1),
        loop=loop
    )


async def select(sql, args, size=None):
    """
    查询数据库函数

    :param sql #sql语句
    :param args #参数
    :param size #查询数据条数

    :return rs #返回查询到记录
    """
    log(sql, args)
    global __pool
    async with __pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            # cur = await conn.cursor(aiomysql.DictCursor)  # 设置游标
            await cur.execute(sql.replace('?', '%s'), args or ())  # 执行sql语句
            if size:
                rs = await cur.fetchmany(size)  # 查询指定条数数据
                if isinstance(rs, asyncio.Future):
                    rs = rs.result()

            else:
                rs = cur.fetchall()  # 查询所有数据
                if isinstance(rs, asyncio.Future):
                    rs = rs.result()

            await cur.close()  # 关闭游标
            info(f'rows returned:{len(rs)}')
            return rs


async def execute(sql, args):
    """
    INSERT、UPDATE、DELETE语句

    :param sql #sql语句
    :param args #参数
    :param size #查询数据条数

    :return rs #一个整数表示影响的行数
    """
    log(sql)
    async with __pool.acquire() as conn:
        try:
            cur = await conn.cursor()
            await cur.execute(sql.replace('?', '%s'), args)
            affected = cur.rowcount
            await cur.close()
        except BaseException as e:
            raise
        return affected


def create_args_string(num):
    L = []
    for n in range(num):
        L.append('?')
    return ', '.join(L)  # etc： num =3 ,return = '?, ?, ?'


class ModelMetaclass(type):
    """
    元类的主要目的就是为了当创建类时能够自动地改变类。
    """

    def __new__(mcs, name, bases, attrs):
        """
        :param name:类的名字 str
        :param bases:类继承的父类集合 Tuple
        :param attrs:类的方法集合
        """
        # 排除Model类本身:
        if name == 'Model':
            return type.__new__(mcs, name, bases, attrs)
        # 获取table名称:
        tableName = attrs.get('__table__', None) or name
        # 日志：找到名为 name 的 model
        info('found model: %s (table: %s)' % (name, tableName))
        # 获取所有的Field和主键名:
        mappings = dict()
        fields = []
        primaryKey = None
        # attrs.items 取决于 __new__ 传入的 attrs 参数
        for k, v in attrs.items():
            # isinstance 类型函数：如果 v 和 Field 类型相同则返回 True ，不相同则 False
            # 即检测是否为正确的数据类型输入，如果是通过mapping来建立类型映射，
            if isinstance(v, Field):
                info('  found mapping: %s ==> %s' % (k, v))
                mappings[k] = v
                # 找到主键:
                if v.primary_key:
                    # 如果发现有多个主键，报主键错误
                    if primaryKey:
                        raise RuntimeError('Duplicate primary key for field: %s' % k)
                    primaryKey = k
                else:
                    # 除主键外的表结构丢入field中
                    fields.append(k)
        # 缺失主键报错
        if not primaryKey:
            raise RuntimeError('Primary key not found.')
        # 如果 key 存在于字典中则将其移除并返回其值，否则返回 default
        for k in mappings.keys():
            attrs.pop(k)
        escaped_fields = list(map(lambda f: '`%s`' % f, fields))
        attrs['__mappings__'] = mappings  # 保存属性和列的映射关系
        attrs['__table__'] = tableName  # table名
        attrs['__primary_key__'] = primaryKey  # 主键属性名
        attrs['__fields__'] = fields  # 除主键外的属性名
        # 构造默认的SELECT, INSERT, UPDATE和DELETE语句:

        # 三个参数分别是主键，除主键其他需要查询的参数
        attrs['__select__'] = 'select `%s`, %s from `%s`' % (primaryKey, ', '.join(escaped_fields), tableName)

        # 四个参数分别是表名，除主键其他需要查询的参数，主键，num：=参数数量的'?'占位符
        attrs['__insert__'] = 'insert into `%s` (%s, `%s`) values (%s)' % (
            tableName, ', '.join(escaped_fields), primaryKey, create_args_string(len(escaped_fields) + 1))

        # 三个参数分别是表名，除主键其他需要查询的参数的name并转换格式为‘name=’，主键
        attrs['__update__'] = 'update `%s` set %s where `%s`=?' % (
            tableName, ', '.join(map(lambda f: '`%s`=?' % (mappings.get(f).name or f), fields)), primaryKey)

        # 两个参数分别是表名，主键
        attrs['__delete__'] = 'delete from `%s` where `%s`=?' % (tableName, primaryKey)
        return type.__new__(mcs, name, bases, attrs)


class Model(dict, metaclass=ModelMetaclass):

    def __init__(self, **kw):
        super(Model, self).__init__(**kw)

    def __getattr__(self, key):
        try:
            return self[key]
            print(self.__primary_key__)
        except KeyError:
            raise AttributeError(r"'Model' object has no attribute '%s'" % key)

    def __setattr__(self, key, value):
        """
        设置属性
        :param key: 属性名
        :param value: 属性值
        :return:
        """
        self[key] = value

    def getValue(self, key):
        """
        :param key: 属性名
        :return: field的属性值
        """
        return getattr(self, key, None)

    def getValueOrDefault(self, key):
        """
        获取一个属性值，如果未赋值，则获取他对应的默认值
        :param key: 属性名
        :return:返回有默认值的field的属性值
        """
        value = getattr(self, key, None)
        if value is None:
            field = self.__mappings__[key]
            if field.default is not None:
                value = field.default() if callable(field.default) else field.default
                debug('using default value for %s: %s' % (key, str(value)))
                setattr(self, key, value)
        return value

    def sql_handle(self, sql, kw, where=None, args=None):

        return sql, args

    @classmethod
    async def findAll(cls, where=None, args=None, **kw):
        # find objects by where clause
        sql = [cls.__select__]

        # sql, args = cls.sql_handle(sql, kw, where, args)
        if where:
            sql.append("where")
            sql.append(where)
        if args is None:
            args = []
        orderBy = kw.get('orderBy', None)
        if orderBy:
            sql.append("orderBy")
            sql.append(orderBy)
        limit = kw.get("limit", None)
        if limit is not None:
            sql.append("limit")
            if isinstance(limit, int):
                sql.append('?')
                args.append(limit)
            elif isinstance(limit, tuple) and len(limit) == 2:
                sql.append("?, ?")
                args.extend((limit))
            else:
                raise ValueError('Invalid limit value: %s' % str(limit))

        log(sql, args)
        rs = await select(' '.join(sql), args)

        return [cls(**r) for r in rs]

    @classmethod
    async def findNumber(cls, selectField, where=None, args=None, **kw):
        # 找到选中的数及位置
        sql = ['select %s _num_ from `%s`' % (selectField, cls.__table__)]

        # sql, args = cls.sql_handle(sql, kw, where, args)

        if where:
            sql.append("where")
            sql.append(where)
        if args is None:
            args = []
        orderBy = kw.get('orderBy', None)
        if orderBy:
            sql.append("orderBy")
            sql.append(orderBy)
        limit = kw.get("limit", None)
        if limit is not None:
            sql.append("limit")
            if isinstance(limit, int):
                sql.append('?')
                args.append(limit)
            elif isinstance(limit, tuple) and len(limit) == 2:
                sql.append("?, ?")
                args.extend((limit))
            else:
                raise ValueError('Invalid limit value: %s' % str(limit))
        rs = await select(' '.join(sql), args, 1)
        return [cls(**r) for r in rs]

    @classmethod
    async def find(cls, pk):
        # 通过主键找对象
        rs = await select('%s where `%s`=?' % (cls.__select__, cls.__primary_key__), [pk], 1)
        if len(rs) == 0:
            return None
            return cls(**rs[0])

    async def save(self):
        args = list(map(self.getValueOrDefault, self.__fields__))
        args.append(self.getValueOrDefault(self.__primary_key__))
        try:
            rows = await execute(self.__insert__, args)
            if rows != 1:
                warning('failed to insert record: affected rows: %s' % rows)
        except pymysql.err.IntegrityError:
            warning('主键参数输入错误')

    async def update(self):
        args = list(map(self.getValue, self.__fields__))
        args.append(self.getValue(self.__primary_key__))
        rows = await execute(self.__update__, args)
        if rows != 1:
            warning('failed to update by primary key: affected rows: %s' % rows)

    async def remove(self):
        args = [self.getValue(self.__primary_key__)]
        rows = await execute(self.__delete__, args)
        if rows != 1:
            warning('failed to remove by primary key: affected rows: %s' % rows)


class Field(object):

    def __init__(self, name, column_type, primary_key, default):
        self.name = name
        self.column_type = column_type
        self.primary_key = primary_key
        self.default = default

    def __str__(self):
        return '<%s, %s:%s>' % (self.__class__.__name__, self.column_type, self.name)


'''
include Fieldtype: String, Int, Boolean, Text

'''


class StringField(Field):

    def __init__(self, name=None, primary_key=False, default=None, ddl='varchar(100)'):
        super().__init__(name, ddl, primary_key, default)


class IntegerField(Field):

    def __init__(self, name=None, primary_key=False, default=0):
        super().__init__(name, 'bigint', primary_key, default)


class BooleanField(Field):
    def __init__(self, name=None, default=False):
        super().__init__(name, 'boolean', False, default)


class TextField(Field):
    def __init__(self, name=None, default=None):
        super().__init__(name, 'text', False, default)


class FloatField(Field):
    def __init__(self, name=None, primary_key=False, default=0):
        super().__init__(name, 'real', primary_key, default)
