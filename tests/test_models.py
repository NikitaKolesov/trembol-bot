import asyncio
from copy import copy
from random import randint, choice
import pytest
from aiogram.types import User as TelegramUser
from aiogram.types import Chat as TelegramChat
from mimesis import Person

from trembol_bot.models import User, ZodiacSign


class TestUser:

    @pytest.yield_fixture(scope='class')
    def event_loop(self):
        loop = asyncio.get_event_loop()
        yield loop
        loop.close()

    @pytest.fixture(scope='class')
    def jhon_doe(self):
        id = 666666666
        photos_list = ["AgADAgADW6oxG9_hGEnK9FjRQCHWsGe5qw4ABOzJcOb5lx8b-IcCAAEC"]
        count = 55
        zodiac_sign = ZodiacSign.Cancer
        yield User(id, 'John', True, count, photos_list, zodiac_sign)

    @pytest.fixture()
    def rand_user(self):
        id = randint(111111111, 999999999)
        photos_list = ["AgADAgADU6oxG9_hGEkuUceK7WG9EnAYrQ4ABHRBA15oGC7nGI0CAAEC",
                       "AgADAgADxKgxG4xY4UnFiTuNych_cEmttw4ABIxvoIMdhZdwx6gAAgI"]
        count = randint(0, 90)
        zodiac_sign = choice(list(ZodiacSign))
        # zodiac_sign = ZodiacSign.Cancer  # for correct work of from_message because zodiac sign is not specified there
        yield User(id, Person().name(), True, count, photos_list, zodiac_sign)

    @pytest.fixture()
    def message(self, rand_user):
        c = TelegramChat()
        c.title = 'UnitTesting'
        u = TelegramUser()
        u.id = rand_user.id
        u.first_name = rand_user.first_name

        class _Message:
            def __init__(self, user, chat):
                self.from_user = user
                self.chat = chat

            @staticmethod
            async def reply(text):
                print(text)
                await asyncio.sleep(0)

        yield _Message(u, c)

    @pytest.fixture(scope='class')
    async def setup_database(self, jhon_doe):
        await jhon_doe.create()
        yield
        jhon_doe._conn.drop()  # drop test users collection

    def test_eq(self, rand_user):
        user = copy(rand_user)
        assert user == rand_user

    def test_eq_negative(self, rand_user):
        user = copy(rand_user)
        user.first_name = user.first_name + 'V'
        assert rand_user != user

    def test_eq_invalid_type(self, rand_user):
        with pytest.raises(TypeError):
            rand_user == 3

    def test_from_message(self, message):
        assert User.from_message(message)

    @pytest.mark.asyncio
    async def test_create(self, rand_user, setup_database):
        assert rand_user == await rand_user.create()

    @pytest.mark.asyncio
    async def test_create_existing(self, jhon_doe, setup_database):
        assert await jhon_doe.create() is None

    @pytest.mark.asyncio
    async def test_create_from_message(self, message, rand_user, setup_database):
        new_user = copy(rand_user)
        new_user.count = 0
        new_user.photos = []
        new_user.zodiac_sign = ZodiacSign.Cancer
        assert new_user == await User.create_from_message(message)

    @pytest.mark.asyncio
    async def test_create_from_message_existing(self, message, rand_user, setup_database):
        new_user = copy(rand_user)
        new_user.count = 0
        new_user.photos = []
        new_user.zodiac_sign = ZodiacSign.Cancer
        await User.create_from_message(message)
        assert await User.create_from_message(message) is None

    @pytest.mark.asyncio
    async def test_from_db_id(self, setup_database, jhon_doe):
        assert jhon_doe == await User.from_db(jhon_doe.id)

    @pytest.mark.asyncio
    async def test_from_db_name(self, setup_database, jhon_doe):
        assert jhon_doe == await User.from_db(jhon_doe.first_name)

    @pytest.mark.asyncio
    async def test_from_db_not_found(self, setup_database, jhon_doe):
        invalid_id = 1
        with pytest.raises(LookupError):
            await User.from_db(invalid_id)

    @pytest.mark.asyncio
    async def test_from_db_negative(self):
        with pytest.raises(TypeError):
            await User.from_db(Exception)

    @pytest.mark.asyncio
    async def test_update(self, setup_database, jhon_doe):
        user1 = await jhon_doe.update(first_name='UpdatedName')
        user2 = await User.from_db(jhon_doe.id)
        assert user1.first_name == user2.first_name

    @pytest.mark.asyncio
    async def test_update_negative_id(self, setup_database, jhon_doe):
        with pytest.raises(IOError):
            await jhon_doe.update(id=123123)

    @pytest.mark.asyncio
    async def test_update_invalid_attr(self, setup_database, jhon_doe):
        with pytest.raises(IOError):
            await jhon_doe.update(invalid_attr=123123)
