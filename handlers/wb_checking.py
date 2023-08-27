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
           text=f"Время выполнения проверки цен WB - {datetime.now().timestamp() - start_time}"
        )
        logging.error(f"Время выполнения проверки цен WB --- {datetime.now().timestamp() - start_time}")
        return
    return wrapper


@stopwatch
async def wb_price_checking() -> None:
    '''
    Функция, проверяющая разницу цен товара. Запускается в интервале времени.
    :return:
    '''
    scheduler.remove_job('wb_price_checking')
    users_list = await db.get_all_users()
    if len(users_list) == 0:
        return
    start_time = datetime.now().timestamp()
    articul = None
    for user_id in users_list:
        positions_list = await db.get_all_position(user_id=user_id, source='wb')
        if len(positions_list) == 0:
            continue
        logging.error(f"Начата проверка цен WB для пользователя {user_id}")
        for position in positions_list:
            articul = position[0]
            name = position[1]
            if position[2] != 'Нет в наличии':
                price_old = int(position[2])
            else:
                price_old = False
            img = position[3]

            # Получение новых данных
            price_new = await selen.wb_check_price(articul)
            if price_new is not None:

                if price_old == False and price_new != False:
                    await bot.send_photo(user_id, photo=img,
                                         caption=f'⚡⚡⚡ <b>Товар появился в наличии</b>\nWildberries 🟣\n{name}\n<b>Артикул:</b> {articul}\n<b>Цена:</b> {price_new} ₽\n<a href="https://www.wildberries.ru/catalog/{articul}/detail.aspx">ССЫЛКА</a>')
                    await db.update_price(articul=articul, user_id=user_id, price=price_new, source='wb')

                elif price_old != False and price_new == False:
                    await bot.send_photo(user_id, photo=img,
                                         caption=f'⚡⚡ <b>Товара больше нет в наличии</b>\nWildberries 🟣\n{name}\n<b>Артикул:</b> {articul}\n<a href="https://www.wildberries.ru/catalog/{articul}/detail.aspx">ССЫЛКА</a>')
                    price_new = 'Нет в наличии'
                    await db.update_price(articul=articul, user_id=user_id, price=price_new, source='wb')

                elif price_new < price_old:
                    difference = price_old - price_new
                    await bot.send_photo(user_id, photo=img,
                                         caption=f'⚡⚡⚡ <b>Цена снижена</b>\nWildberries 🟣\n{name}\n<b>Артикул:</b> {articul}\n<b>Старая цена:</b> {price_old} ₽\n<b>Новая цена:</b> {price_new} ₽\n<a href="https://www.wildberries.ru/catalog/{articul}/detail.aspx">ССЫЛКА</a>\n\n<b>Подешевело на: {difference} ₽</b>')
                    await db.update_price(articul=articul, user_id=user_id, price=price_new, source='wb')

                elif price_new > price_old:
                    difference = price_new - price_old
                    await bot.send_photo(user_id, photo=img,
                                         caption=f'⚡ Цена возросла\nWildberries 🟣\n<b>{name}</b>\nАртикул: <b>{articul}</b>\nСтарая цена: <b>{price_old}</b> ₽\nНовая цена: <b>{price_new}</b> ₽\n<a href="https://www.wildberries.ru/catalog/{articul}/detail.aspx">ССЫЛКА</a>\n\n<b>Подорожало на: {difference} ₽</b>')
                    await db.update_price(articul=articul, user_id=user_id, price=price_new, source='wb')

                else:
                    continue

            else:
                logging.error(f"При проверке цены возникла проблема при обработке с артикулом {articul}")
                await bot.send_message(user_id,
                                       f"⚠️ С артикулом {articul} (WB) возникли проблемы. Проверьте наличие товара.")
                continue

    await wb_add_price_checking_job()


async def wb_add_price_checking_job():
    '''
    Запуск проверки цен каждый 30 минут (в плане - 60 минут)
    '''
    scheduler.add_job(wb_price_checking, trigger='interval', minutes=random.randint(1, 5), id='wb_price_checking')


scheduler.add_job(
    wb_add_price_checking_job,
    trigger='date',
    run_date=datetime.now() + timedelta(seconds=15),
    id='wb_price_checking'
)

__all__ = ['wb_price_checking']
