import asyncio
import logging
import motor.motor_asyncio
from random import randint

from aiogram import Bot, types
from aiogram.dispatcher import Dispatcher
from aiogram.utils.executor import start_polling

API_TOKEN = '489175236:AAEF7xSRXtmostkUlttKDN3sBQQJPmEngcQ'

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("__main__")

loop = asyncio.get_event_loop()
bot = Bot(token=API_TOKEN, loop=loop)
dp = Dispatcher(bot)


@dp.message_handler(commands=['start', 'help'])
async def send_welcome(message: types.Message):
    await message.reply("Hi!\nI'm EchoBot!\nPowered by aiogram.")


@dp.message_handler(commands=['register'])
async def register_user(message: types.Message, client):
    db = client[message.chat.title]
    if await db.test_chat.find_one({"user_id": message.from_user.id}) is None:
        await db.test_chat.insert_one({
            "user_id": message.from_user.id,
            "user_firstname": message.from_user.first_name,
            "count": 0
        })
        logger.info("Player {} registered in group {}".format(message.from_user.first_name, message.chat.title))
    else:
        await message.reply("You are already registered.")


async def roll_locked(chat_title):
    db = motor.motor_asyncio.AsyncIOMotorClient()[chat_title]
    que = await db.test_chat.find_one({"lock": 1})
    print(que)
    if que is None:
        return False
    else:
        return True


@dp.message_handler(commands=['roll'])
async def roll_dice(message: types.Message):
    db = motor.motor_asyncio.AsyncIOMotorClient()[message.chat.title]
    if not await roll_locked(message.chat.title): # not roll_locked(message.chat.title):
        user_count = 2
        winner = (await db.test_chat.find({"status": "active"}).limit(1).skip(randint(0,user_count - 1)).to_list(length=20))[0]
        logger.info("Winner: {}".format(winner))
        await db.test_chat.update_one({"user_id": winner["user_id"]}, {"$inc": {"count": 1}})
        logger.info("Winner {} count {}".format(winner["user_firstname"], winner["count"] + 1))
    else:
        await bot.send_message(message.chat.id, "Poll is blocked for today")


@dp.message_handler(regexp='(^cat[s]?$|puss)')
async def cats(message: types.Message):
    with open('data/cats.jpg', 'rb') as photo:
        await bot.send_photo(message.chat.id, photo, caption='Cats is here 😺',
                             reply_to_message_id=message.message_id)


@dp.message_handler()
async def echo(message: types.Message):
    await bot.send_message(message.chat.id, message.text)


if __name__ == '__main__':
    client = motor.motor_asyncio.AsyncIOMotorClient()
    start_polling(dp, loop=loop, skip_updates=True)

    # Also you can use another execution method
    # >>> try:
    # >>>     loop.run_until_complete(main())
    # >>> except KeyboardInterrupt:
    # >>>     loop.stop()
