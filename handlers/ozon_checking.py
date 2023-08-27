import logging
from datetime import datetime, timedelta
from bot.create_bot import db, selen, bot, scheduler
import random


def stopwatch(funk):
    async def wrapper(*args, **kwargs):
        start_time = datetime.now().timestamp()
        await funk(*args, **kwargs)
        await bot.send_message(
            chat_id=514665692,
           text=f"Время выполнения проверки цен OZON - {datetime.now().timestamp() - start_time}"
        )
        logging.error(f"Время выполнения проверки цен OZON --- {datetime.now().timestamp() - start_time}")
        return
    return wrapper


@stopwatch
async def ozon_price_checking() -> None:
    '''
    Функция, проверяющая разницу цен товара. Запускается в интервале времени.
    :return:
    '''
    scheduler.remove_job('ozon_price_checking')
    users_list = await db.get_all_users()
    if len(users_list) == 0:
        return
    # start_time = datetime.now().timestamp()
    # articul = None
    for user_id in users_list:
        positions_list = await db.get_all_position(user_id=user_id, source='ozon')
        if len(positions_list) == 0:
            continue
        logging.error(f"Начата проверка цен OZON для пользователя {user_id}")
        for position in positions_list:
            articul = position[0]
            name = position[1]
            if position[2] != 'Нет в наличии':
                price_old = int(position[2])
            else:
                price_old = False
            img = position[3]

            # Получение новых данных
            price_new = await selen.ozon_check_price(articul)

            if price_new is not None:

                if price_old == False and price_new != False:
                    await bot.send_photo(user_id, photo=img,
                                         caption=f'⚡⚡⚡ <b>Товар появился в наличии</b>\nOZON 🔵\n{name}\n<b>Артикул:</b> {articul}\n<b>Цена:</b> {price_new} ₽\n<a href="https://www.ozon.ru/product/{articul}/detail.aspx">ССЫЛКА</a>')
                    await db.update_price(articul=articul, user_id=user_id, price=price_new, source='ozon')

                elif price_old != False and price_new == False:
                    await bot.send_photo(user_id, photo=img,
                                         caption=f'⚡⚡ <b>Товара больше нет в наличии</b>\nOZON 🔵\n{name}\n<b>Артикул:</b> {articul}\n<a href="https://www.ozon.ru/product/{articul}/detail.aspx">ССЫЛКА</a>')
                    price_new = 'Нет в наличии'
                    await db.update_price(articul=articul, user_id=user_id, price=price_new, source='ozon')

                elif price_new < price_old:
                    difference = price_old - price_new
                    await bot.send_photo(user_id, photo=img,
                                         caption=f'⚡⚡⚡ <b>Цена снижена</b>\nOZON 🔵\n{name}\n<b>Артикул:</b> {articul}\n<b>Старая цена:</b> {price_old} ₽\n<b>Новая цена:</b> {price_new} ₽\n<a href="https://www.ozon.ru/product/{articul}/detail.aspx">ССЫЛКА</a>\n\n<b>Подешевело на: {difference} ₽</b>')
                    await db.update_price(articul=articul, user_id=user_id, price=price_new, source='ozon')

                elif price_new > price_old:
                    difference = price_new - price_old
                    await bot.send_photo(user_id, photo=img,
                                         caption=f'⚡ <b>Цена возросла</b>\nOZON 🔵\n{name}\n<b>Артикул:</b> {articul}\n<b>Старая цена:</b> {price_old} ₽\n<b>Новая цена:</b> {price_new} ₽\n<a href="https://www.ozon.ru/product/{articul}/detail.aspx">ССЫЛКА</a>\n\n<b>Подорожало на: {difference} ₽</b>')
                    await db.update_price(articul=articul, user_id=user_id, price=price_new, source='ozon')

                else:
                    continue

            else:
                logging.error(f"При проверке цены возникла проблема при обработке с артикулом {articul}")
                await bot.send_message(user_id,
                                       f"⚠️ С артикулом {articul} (OZON) возникли проблемы. Проверьте наличие товара.")
                continue

    await ozon_add_price_checking_job()


async def ozon_add_price_checking_job():
    '''
    Запуск проверки цен каждый 30 минут (в плане - 60 минут)
    '''
    scheduler.add_job(ozon_price_checking, trigger='interval', minutes=random.randint(1, 5), id='ozon_price_checking')


scheduler.add_job(
    ozon_add_price_checking_job,
    trigger='date',
    run_date=datetime.now() + timedelta(seconds=10),
    id='ozon_price_checking'
)

__all__ = ['ozon_price_checking']
