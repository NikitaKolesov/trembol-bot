import logging
from enum import unique, auto, Enum
from typing import Union

from aiogram import types
from marshmallow import Schema, fields, post_load
from marshmallow_enum import EnumField
from motor import motor_asyncio

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)  # TODO get from config file


@unique
class ZodiacSign(Enum):
    Aries = auto()
    Taurus = auto()
    Gemini = auto()
    Cancer = auto()
    Leo = auto()
    Virgo = auto()
    Libra = auto()
    Scorpio = auto()
    Sagittarius = auto()
    Capricorn = auto()
    Aquarius = auto()
    Pisces = auto()


class UserSchema(Schema):
    id = fields.Int(data_key='_id', required=True)
    first_name = fields.Str(required=True)
    status = fields.Bool(required=True)
    count = fields.Int(required=True)
    photos = fields.List(fields.Str(), required=True)
    zodiac_sign = EnumField(ZodiacSign)

    @post_load
    def make_user(self, data):
        return User(**data)


class User:
    collection = 'users'
    # bot = Bot(token='dummy', loop=None)  # change to correct Bot instance
    db = motor_asyncio.AsyncIOMotorClient()['test']  # change to correct db name
    _conn = db[collection]  # maybe won't work correctly because of parameters above need to be changed
    SCHEMA_FIELDS = UserSchema().fields
    ID_DATA_KEY = SCHEMA_FIELDS['id'].data_key

    def __init__(self, id: int, first_name: str, status: bool, count: int, photos: list, zodiac_sign: Enum):
        self.id = id
        self.first_name = first_name
        self.status = status
        self.count = count
        self.photos = photos
        self.zodiac_sign = zodiac_sign
        self._conn = self.db[self.collection]

    @classmethod
    def _db_key(cls, key):
        return cls.SCHEMA_FIELDS[key].data_key or cls.SCHEMA_FIELDS[key].name

    def __eq__(self, other):
        # TODO maybe need to compare only attributes in __init__
        if not isinstance(other, __class__):
            raise TypeError(f'Comparing with not instance of {__class__}')
        return self.__dict__ == other.__dict__

    async def is_created(self):
        """Check if user with the same id is already created"""
        if await self._conn.find_one({self.ID_DATA_KEY: self.id}) is None:
            return False
        return True

    async def create(self):
        """Create user entry in database

        :return: self if not is_created else None
        """
        if await self.is_created():
            log.warning(f'Player with id {self.id} already exists in database')
            return
        await self._conn.insert_one(UserSchema().dump(self))
        log.info(f'Player {self.first_name} added. ID {self.id}')
        return self

    @classmethod
    async def is_created_from_message(cls, message: types.Message):
        """Check if user that sent register command is already created"""
        if await cls.db[cls.collection].find_one({cls.ID_DATA_KEY: message.from_user.id}) is None:
            return False
        return True

    @classmethod
    def from_message(cls, message: types.Message):
        dump = {
            '_id': message.from_user.id,
            'first_name': message.from_user.first_name,
            'status': True,
            'count': 0,
            'photos': [],
            'zodiac_sign': ZodiacSign.Cancer.name  # just a default value need to change manually
        }
        return UserSchema().load(dump)

    @classmethod
    async def create_from_message(cls, message: types.Message):
        if await cls.is_created_from_message(message):
            await message.reply("Вы уже зарегистрировались")
            log.debug(f'Player {message.from_user.first_name} already registered in group {message.chat.title}')
            return
        o = cls.from_message(message)
        return await o.create()

    @classmethod
    async def from_db(cls, id_or_name: Union[int, str]):
        _conn = cls.db[cls.collection]
        if isinstance(id_or_name, int):
            dump = await _conn.find_one({cls._db_key('id'): id_or_name})
        elif isinstance(id_or_name, str):
            dump = await _conn.find_one({cls._db_key('first_name'): id_or_name})
        else:
            raise TypeError(f'Specify either id(int) or first_name(str). {type(id_or_name)} was given')
        if dump is None:
            raise LookupError(f'User with {"id" if isinstance(id_or_name,int) else "name"} not found in db')
        return UserSchema().load(dump)

    async def update(self, **kwargs):
        if 'id' in kwargs:
            raise IOError("Can't update ID field")
        for k, v in kwargs.items():
            if k not in self.SCHEMA_FIELDS:
                raise IOError('Not supported argument')
            self.__setattr__(k, v)
        await self._conn.update_one({self.ID_DATA_KEY: self.id}, {'$set': kwargs})
        return self

    async def delete(self):
        pass
