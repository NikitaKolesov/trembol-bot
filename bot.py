import asyncio
import logging
import motor.motor_asyncio

from aiogram import Bot, types
from aiogram.dispatcher import Dispatcher
from aiogram.utils.executor import start_polling

API_TOKEN = '489175236:AAEF7xSRXtmostkUlttKDN3sBQQJPmEngcQ'

logging.basicConfig(level=logging.INFO)

loop = asyncio.get_event_loop()
bot = Bot(token=API_TOKEN, loop=loop)
dp = Dispatcher(bot)


async def is_registered():



@dp.message_handler(commands=['start', 'help'])
async def send_welcome(message: types.Message):
    await message.reply("Hi!\nI'm EchoBot!\nPowered by aiogram.")


@dp.message_handler(regexp='(^cat[s]?$|puss)')
async def cats(message: types.Message):
    with open('data/cats.jpg', 'rb') as photo:
        await bot.send_photo(message.chat.id, photo, caption='Cats is here 😺',
                             reply_to_message_id=message.message_id)



@dp.message_handler()
async def echo(message: types.Message):
    await bot.send_message(message.chat.id, message.text)


@dp.message_handler(commands=['register'])
async def register_user(message: types.Message):
    client = motor.motor_asyncio.AsyncIOMotorClient()
    db = client.bot_database
    if
    await db.test_chat.insert_one({
        "user_id": message.from_user.id,
        "user_firstname": message.from_user.first_name,
        "count": 0
    })
    print("Output of None:" + await db.test_chat.find_one({"user_id": "no valid id"}))


if __name__ == '__main__':
    start_polling(dp, loop=loop, skip_updates=True)

    # Also you can use another execution method
    # >>> try:
    # >>>     loop.run_until_complete(main())
    # >>> except KeyboardInterrupt:
    # >>>     loop.stop()
