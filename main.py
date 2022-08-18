# 这是一个示例 Python 脚本。

# 按 Shift+F10 执行或将其替换为您的代码。
# 按 双击 Shift 在所有地方搜索类、文件、工具窗口、操作和设置。
import asyncio
import json
import sys


def consumer():
    r = ''
    while True:
        n = yield r
        if not n:
            return
        print(f"[CONSUMER] Consuming.... {n}")
        r = '200 OK'


def produce(c):
    c.send(None)
    n = 0
    while n < 5:
        n += 1
        print(f"[PRODUCER] Producing... {n}")
        r = c.send(n)
        print(f"[PRODUCER] Consumer return: {r}")
    c.close()


async def C():
    await asyncio.sleep(0)
    print('q')
    await asyncio.sleep(0)
    print('w')
    await asyncio.sleep(0)
    print('e')
    return


async def A_B():
    # print("主协程")
    # print("等待result1协程运行")
    # res1 = await A()
    # print("等待result2协程运行")
    #
    # res2 = await B()
    # return (res1, res2)
    await  asyncio.wait([C()])


# 请记住，'type'实际上是一个类，就像'str'和'int'一样
# 所以，你可以从type继承
class MetaA(type):
    # __new__ 是在__init__之前被调用的特殊方法
    # __new__是用来创建对象并返回之的方法
    # 而__init__只是用来将传入的参数初始化给对象
    # 你很少用到__new__，除非你希望能够控制对象的创建
    # 这里，创建的对象是类，我们希望能够自定义它，所以我们这里改写__new__
    # 如果你希望的话，你也可以在__init__中做些事情
    # 还有一些高级的用法会涉及到改写__call__特殊方法，但是我们这里不用
    def __new__(cls, name, bases, dct):
        print('MetaA.__new__')
        # 这种方式不会调用__init__方法
        # return type(name, bases, dct)
        # 这种方式会调用__init__
        return type.__new__(cls, name, bases, dct)

    def __init__(cls, name, bases, dct):
        print('MetaA.__init__')


class A(object, metaclass=MetaA):
    pass


class ListMetaclass(type):

    # 元类会自动将你通常传给‘type’的参数作为自己的参数传入
    # mcs表示元类
    # name表示创建类的类名（在这里创建类就是继承Model类的子类User）
    # bases表示创建类继承的所有父类
    # namespace表示创建类的所有属性和方法（以键值对的字典的形式）
    def __new__(mcs, name, bases, namespace):
        namespace['add'] = lambda self, value: self.append(value)
        return type.__new__(mcs, name, bases, namespace)


# 通过metaclass，给该类动态添加了add方法
class MyList(list, metaclass=ListMetaclass):
    pass


def print_hi(name):
    # 在下面的代码行中使用断点来调试脚本。
    print(f'Hi, {name}')  # 按 Ctrl+F8 切换断点。


# 按间距中的绿色按钮以运行脚本。
if __name__ == '__main__':
    # loop = asyncio.get_event_loop()
    # loop.run_until_complete(A_B())
    # loop.run_forever()
    # c = consumer()
    # # produce(c)
    # print(A())
    # l = MyList()
    # l.add(1)
    # print(l)

    def create_args_string(num):
        L = []
        for n in range(num):
            L.append('?')
        return ', '.join(L)


    print(create_args_string(3))

    pass
