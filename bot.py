import asyncio
import logging
from datetime import datetime, timedelta
import motor.motor_asyncio
from random import randint, choice
from aiogram import Bot, types
from aiogram.dispatcher import Dispatcher
from aiogram.utils.executor import start_polling

API_TOKEN = '489175236:AAEF7xSRXtmostkUlttKDN3sBQQJPmEngcQ'
LOCK_PERIOD_TEST = timedelta(hours=1)
LOCK_PERIOD = timedelta(1)
DB_NAME = "Game"
LIST_LENGTH = 20
REMOVE_CLUTTER_DELAY = 1  # clear delay in minutes
REMOVE_CLUTTER = False
database = motor.motor_asyncio.AsyncIOMotorClient()[DB_NAME]
PRIZE_ID = "AgADAgADHKkxG_4C0UioQAEy-dkHTZ5Tqw4ABHGHHuOTmBYmJWMCAAEC"

logging.basicConfig(level=logging.DEBUG,
                    filename="/home/nkolesov/TrembolGameTest/logfile.log",
                    filemode="w",
                    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("__main__")

loop = asyncio.get_event_loop()
bot = Bot(token=API_TOKEN, loop=loop)
dp = Dispatcher(bot)


# TODO implement spam period


async def is_locked(db_id):
    """Check if another roll is allowed, set new lock if possible"""
    lock = await database[db_id].find_one({"lock": 1})
    if lock is None:
        await database[db_id].insert_one({
            "lock": 1,
            "date": datetime(2018, 1, 1)
        })
        lock = await database[db_id].find_one({"lock": 1})
    delta = datetime.now() - lock["date"]
    if delta <= timedelta(0):
        return True
    else:
        new_date = datetime.combine(datetime.now().date(), datetime.min.time()) + LOCK_PERIOD
        # new_date = datetime.now() + LOCK_PERIOD_TEST  # TESTING
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
    """Register new user or send message if already registered"""
    if await database[message.chat.title].find_one({"user_id": message.from_user.id}) is None:
        await database[message.chat.title].insert_one({
            "user_id": message.from_user.id,
            "user_firstname": message.from_user.first_name,
            "status": "active",
            "count": 0
        })
        logger.info("Player {} registered in group {}".format(message.from_user.first_name, message.chat.title))
        await bot.send_message(message.chat.id, "{} зарегистрировался".format(message.from_user.first_name))
        await remove_clutter(message)
    else:
        result = await message.reply("Вы уже зарегистрировались")
        await remove_clutter(result, message)


@dp.message_handler(commands=["roll"])
async def roll_dice(message: types.Message):
    """Randomly choose a winner of the day"""
    if not await is_locked(message.chat.title):
        user_count = await database[message.chat.title].find({"status": "active"}).count()
        if user_count == 0:
            await bot.send_message(message.chat.id, "Нет зарегистрировавшихся игроков")
            await remove_clutter(message)
        elif user_count == 1:
            await bot.send_message(message.chat.id, "Только один игрок зарегистрировался 😐")
            await remove_clutter(message)
        else:
            winner = (await database[message.chat.title].find({"status": "active"}).limit(1).skip(
                randint(0, user_count - 1)).to_list(length=LIST_LENGTH))[0]

            # Save winner info in lock for getting it's photo
            await database[message.chat.title].update_one({"lock": {"$exists": 1}},
                                                          {"$set": {"winner": winner}})

            # Increment winner count
            await database[message.chat.title].update_one({"user_id": winner["user_id"]},
                                                          {"$inc": {"count": 1}})
            if message.chat.title == "Трембол":
                await bot.send_photo(message.chat.id, choice(winner["photos"]), caption="Пидор дня")
                await remove_clutter(message)
            else:
                # await bot.send_message(message.chat.id, "Победитель этого дня - {}".format(winner["user_firstname"]))
                result = await bot.send_message(message.chat.id, "Выбираем победителя")
                await result.edit_text("Выбираем победителя.")
                await result.edit_text("Выбираем победителя..")
                await result.edit_text("Выбираем победителя...")
                await bot.send_photo(message.chat.id, choice(winner["photos"]), caption="Победитель дня")
                await remove_clutter(message)
            logger.info("Winner {} count {}".format(winner["user_firstname"], winner["count"] + 1))
    else:
        left_time = (await database[message.chat.title].find_one({"lock": 1}))["date"] - datetime.now()
        result = await bot.send_message(message.chat.id, "День ещё не прошёл\n"
                                                         "Осталось {}".format(left_time))
        await remove_clutter(result, message)


@dp.message_handler(commands=["stats"])
async def show_statistics(message: types.Message):
    """Display statistics of players in order"""
    if database[message.chat.title].find_one({"status": "active"}) is None:
        await bot.send_message(message.chat.id, "Нет зарегистрировавшихся игроков")
        await remove_clutter(message)
    else:
        players = await database[message.chat.title].find({"$query": {"status": "active"},
                                                           "$orderby": {"count": -1}}).to_list(length=LIST_LENGTH)
        # TODO reimplement formatting
        players = [(i["user_firstname"], i["count"]) for i in players]
        reply = ""
        for i in players:
            reply += "{} - {}\n".format(i[0], i[1])
        result = await bot.send_message(message.chat.id, reply)
        await remove_clutter(result, message)


# TODO implement clear count handler
@dp.message_handler(commands=["reset"])
async def clear_stats(message: types.Message):
    """Clear stats (can be performed by admin only)"""
    admins = (await database[message.chat.title].find_one({"admins": {"$exists": 1}}))["admins"]
    if message.from_user.id in admins:
        database[message.chat.title].update_many({"status": "active"},
                                                 {"$set": {"count": 0}})
        result = await bot.send_message(message.chat.id, "Данные сброшены")
        logger.info("Count is reset in {}".format(message.chat.title))
        await remove_clutter(result, message)
    else:
        result1 = await message.reply("У тебя недостаточно прав 😡")
        await asyncio.sleep(2)
        result2 = await message.reply("Но мы можем договориться! 😉\n"
                                      "Отправь косарик на сбер разработчику\n"
                                      "+79269244072\n"
                                      "И админка считай уже у тебя в кармане\n"
                                      "P.S. деньги пойдут на поддержку румынского ВВП")
        await remove_clutter(result1, result2, message)


@dp.message_handler(commands=["prize"])
async def prize(message: types.Message):
    await bot.send_photo(message.chat.id, PRIZE_ID, caption="Приз первого сезона")


@dp.message_handler(commands=["listphotos"])
async def list_photos(message: types.Message):
    """List photos for user
    Usage: /listphotos {chat_title} {user_firstname}"""
    args = message.get_args().split(" ")
    if len(args) == 2:
        chat_title = args[0]
        user_firstname = args[1]
        photos = (await database[chat_title].find_one({"user_firstname": user_firstname}))["photos"]
        logger.info("Photos for {}: {}".format(user_firstname, photos))
        for i in photos:
            await bot.send_photo(message.chat.id, i)
    else:
        await bot.send_message(message.chat.id, "Wrong usage")


@dp.message_handler(content_types=types.ContentType.PHOTO)
async def identify_photo(message: types.Message):
    """All photo messages handler
    Usage: setphoto {chat_title} {user_firstname}"""
    if message.caption is not None:
        setup = message.caption.split(" ")
        if len(setup) == 3 and setup[0] == "setphoto":
            chat_title = setup[1]
            user_firstname = setup[2]
            if (await database[chat_title].find_one({"user_firstname": user_firstname})) is not None:
                await database[chat_title].update_one({"user_firstname": user_firstname},
                                                    {"$push": {"photos": message.photo[0]["file_id"]}})
                logger.info("Photo {} added for {} in {}".format(message.photo[0]["file_id"],
                                                                 user_firstname,
                                                                 chat_title))
                await bot.send_message(message.chat.id, "New photo is added for {} in {}".format(user_firstname,
                                                                                           chat_title))
                # await bot.send_photo(message.chat.id, message.photo[0]["file_id"])
            else:
                logger.info("{} is not in {}".format(user_firstname, chat_title))
                await bot.send_message(message.chat.id, "{} is not in {}".format(user_firstname, chat_title))
        else:
            await bot.send_message(message.chat.id, "Command in caption is not specified\n"
                                                    "Commands:\n"
                                                    "setphoto {chat_title} {user_firstname}")
            logger.info("Incorrect command in caption: {}".format(message.caption))
    else:
        logger.info("Message.photo0: {}".format(message.photo[0]))
        await message.reply("File_id: {}".format(message.photo[0]["file_id"]))


async def remove_clutter(*messages: types.Message):
    """Can remove clutter messages"""
    if not REMOVE_CLUTTER: return 0
    await asyncio.sleep(REMOVE_CLUTTER_DELAY * 60)
    for message in messages:
        await bot.delete_message(message.chat.id, message.message_id)
        logger.info("Message {} at {} from {} in {} has been deleted".format(message.message_id, message.date,
                                                                             message.from_user.username,
                                                                             message.chat.title))


# @dp.message_handler(regexp='(^cat[s]?$|puss)')
# async def cats(message: types.Message):
#     with open('data/cats.jpg', 'rb') as photo:
#         await bot.send_photo(message.chat.id, photo, caption='Cats is here 😺',
#                              reply_to_message_id=message.message_id)


# @dp.message_handler()
# async def echo(message: types.Message):
#     await bot.send_message(message.chat.id, message.text)


if __name__ == '__main__':
    start_polling(dp, loop=loop, skip_updates=True)

    # Also you can use another execution method
    # >>> try:
    # >>>     loop.run_until_complete(main())
    # >>> except KeyboardInterrupt:
    # >>>     loop.stop()
