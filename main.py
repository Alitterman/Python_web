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


def print_hi(name):
    # 在下面的代码行中使用断点来调试脚本。
    print(f'Hi, {name}')  # 按 Ctrl+F8 切换断点。


# 按间距中的绿色按钮以运行脚本。
if __name__ == '__main__':
    # loop = asyncio.get_event_loop()
    # loop.run_until_complete(A_B())
    # loop.run_forever()
    c = consumer()
    produce(c)
