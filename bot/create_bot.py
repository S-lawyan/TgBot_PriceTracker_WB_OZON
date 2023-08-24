import configparser
from aiogram.dispatcher import Dispatcher
from aiogram import Bot, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from DB.db_sqlite import DataBase
from src.selen import Selen
from apscheduler.schedulers.asyncio import AsyncIOScheduler

import logging

# логируем ошибки
logging.basicConfig(filename='log/ERROR.txt',
                    filemode='a',
                    format='%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S',
                    level=logging.ERROR)

# берем конфиги
config = configparser.ConfigParser()
config.read("src/config.ini")
# Присваиваем значения внутренним переменным
TOKEN = config['Bot']['TOKEN']
PASSWORD = config['Bot']['PASSWORD']
db = DataBase()
USER_LIST = db.all_users()

selen = Selen(USER_LIST)

job_defaults = {
    'coalesce': False,
    'max_instances': 3,
    'timezone': 'Europe/Moscow',
    'misfire_grace_time': 360,
}
scheduler = AsyncIOScheduler(job_defaults=job_defaults)
scheduler.start()

# запускаем бота
bot = Bot(token=TOKEN, parse_mode=types.ParseMode.HTML)
dp = Dispatcher(bot, storage=MemoryStorage())
