import asyncio
import logging
from datetime import datetime, timedelta
import motor.motor_asyncio
from random import randint
from aiogram import Bot, types
from aiogram.dispatcher import Dispatcher
from aiogram.utils.executor import start_polling

API_TOKEN = '489175236:AAEF7xSRXtmostkUlttKDN3sBQQJPmEngcQ'
LOCK_PERIOD_TEST = timedelta(hours=1)
LOCK_PERIOD = timedelta(1)
DB_NAME = "Game"
LIST_LENGTH = 20
REMOVE_CLUTTER_DELAY = 1 # clear delay in minutes
database = motor.motor_asyncio.AsyncIOMotorClient()[DB_NAME]

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("__main__")

loop = asyncio.get_event_loop()
bot = Bot(token=API_TOKEN, loop=loop)
dp = Dispatcher(bot)

# TODO implement spam period


async def is_locked(db_id):
    lock = await database[db_id].find_one({"lock": 1})
    if lock is None:
        await database[db_id].insert_one({
            "lock": 1,
            "date": datetime(2018, 1, 1)
        })
        lock = await database[db_id].find_one({"lock": 1})
    delta = datetime.now() - lock["date"]
    # logger.info("Delta is {}".format(delta))
    if delta <= timedelta(0):
        return True
    else:
        # new_date = datetime.combine(datetime.now().date(), datetime.min.time()) + LOCK_PERIOD_TEST
        new_date = datetime.now() + LOCK_PERIOD_TEST # TESTING
        await database[db_id].update_one({"lock": 1}, {
            "$set": {"date": new_date}
        })
        logger.info("New date for lock is set {}".format(new_date))
        return False


@dp.message_handler(commands=["start", "help"])
async def send_welcome(message: types.Message):
    await message.reply("Hi!\nI'm TrembolGameBot!\nPowered by aiogram.")


@dp.message_handler(commands=["register"])
async def register_user(message: types.Message):
    if await database[message.chat.title].find_one({"user_id": message.from_user.id}) is None:
        await database[message.chat.title].insert_one({
            "user_id": message.from_user.id,
            "user_firstname": message.from_user.first_name,
            "status": "active",
            "count": 0
        })
        logger.info("Player {} registered in group {}".format(message.from_user.first_name, message.chat.title))
        await bot.send_message(message.chat.id, "{} зарегистрировался".format(message.from_user.first_name))
    else:
        result = await message.reply("Вы уже зарегистрировались.")
        await remove_clutter(result)
        await remove_clutter(message)


@dp.message_handler(commands=["roll"])
async def roll_dice(message: types.Message):
    if not await is_locked(message.chat.title):
        user_count = await database[message.chat.title].find({"status": "active"}).count()
        if user_count == 0:
            await bot.send_message(message.chat.id, "Нет зарегистрировавшихся игроков")
        elif user_count == 1:
            await bot.send_message(message.chat.id, "Только один игрок зарегистрировался 😐")
        else:
            winner = (await database[message.chat.title].find({"status": "active"}).limit(1).skip(
                randint(0, user_count - 1)).to_list(length=LIST_LENGTH))[0]
            await database[message.chat.title].update_one({"user_id": winner["user_id"]}, {"$inc": {"count": 1}})
            if message.chat.title == "Трембол":
                await bot.send_message(message.chat.id, "Пидор этого часа - {}".format(winner["user_firstname"]))
            else:
                await bot.send_message(message.chat.id, "Победитель этого часа - {}".format(winner["user_firstname"]))
            logger.info("Winner {} count {}".format(winner["user_firstname"], winner["count"] + 1))
    else:
        left_time = (await database[message.chat.title].find_one({"lock": 1}))["date"] - datetime.now()
        await bot.send_message(message.chat.id, "Час ещё не прошёл\n"
                                                "Осталось {}".format(left_time))


@dp.message_handler(commands=["stats"])
async def show_statistics(message: types.Message):
    """Display statistics of players in order"""
    if database[message.chat.title].find_one({"status": "active"}) is None:
        await bot.send_message(message.chat.id, "Нет зарегистрировавшихся игроков")
    else:
        players = await database[message.chat.title].find({
            "$query": {"status": "active"},
            "$orderby": {"count": -1}
        }).to_list(length=LIST_LENGTH)
        # TODO reimplement formatting
        players = [(i["user_firstname"], i["count"]) for i in players]
        reply = ""
        for i in players:
            reply += "{} - {}\n".format(i[0], i[1])
        await bot.send_message(message.chat.id, reply)


# TODO implement clear count handler
async def remove_clutter(message: types.Message):
    await asyncio.sleep(REMOVE_CLUTTER_DELAY * 60)
    await bot.delete_message(message.chat.id, message.message_id)
    logger.info("Message {} at {} from {} in {} has been deleted".format(message.message_id, message.date, message.from_user.username, message.chat.title))
# def remove_clutter(func, message: types.Message):
#     async def wrapper(message):
#         await func(message: types.Message)
#         await asyncio.sleep(REMOVE_CLUTTER_DELAY * 60)
#         await bot.delete_message(chat_id, message_id)
#     return wrapper()


@dp.message_handler(regexp='(^cat[s]?$|puss)')
async def cats(message: types.Message):
    with open('data/cats.jpg', 'rb') as photo:
        await bot.send_photo(message.chat.id, photo, caption='Cats is here 😺',
                             reply_to_message_id=message.message_id)


@dp.message_handler()
async def echo(message: types.Message):
    await bot.send_message(message.chat.id, message.text)


if __name__ == '__main__':
    start_polling(dp, loop=loop, skip_updates=True)

    # Also you can use another execution method
    # >>> try:
    # >>>     loop.run_until_complete(main())
    # >>> except KeyboardInterrupt:
    # >>>     loop.stop()
