from orm import Model, StringField, IntegerField, BooleanField, FloatField, create_pool
import asyncio


class User(Model):
    print('调用了User')
    __table__ = 'users'
    id = IntegerField(primary_key=True)
    # id = StringField(primary_key=True, default=next_id(), ddl='varchar(50)')    email = StringField(ddl='varchar(50)')
    passwd = StringField(ddl='varchar(50)')
    admin = BooleanField()
    name = StringField(ddl='varchar(50)')
    image = StringField(ddl='varchar(500)')
    created_at = FloatField(default='1111')


# 创建实例:
async def test_save():
    await create_pool(loop, user='root', password='root', db='orm_test')
    # 测试时需要修改为自己使用的数据库账户与密码    await create_pool(loop, user='www-data', password='www-data', db='awesome')
    user = User(id=10, name='c', email='c@example', passwd='123', image='about:blank')
    await user.save()


if __name__ == '__main__':
    loop = asyncio.get_event_loop()

    loop.run_until_complete(test_save())

# 查询所有User对象:
# users = User.findAll()
