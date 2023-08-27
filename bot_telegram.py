from aiogram.utils import executor
from bot.create_bot import dp
from handlers import client

async def on_startup(_):
    print('Бот вышел в онлайн.')


async def on_shutdown(_):
    print('Бот прекратил работу.')

client.register_handlers_client(dp)

executor.start_polling(dp, skip_updates=True, on_startup=on_startup, on_shutdown=on_shutdown)
