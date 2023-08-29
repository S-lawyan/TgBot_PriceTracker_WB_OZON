import logging
import re
from datetime import datetime

from aiogram import Dispatcher
from aiogram import types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text
from aiogram.dispatcher.filters.state import State
from aiogram.dispatcher.filters.state import StatesGroup

from bot.create_bot import bot
from bot.create_bot import db
from bot.create_bot import dp
from bot.create_bot import PASSWORD
from bot.create_bot import selen
from keyboards.client_kb import *


class ClientStates(StatesGroup):
    get_passwd = State()
    get_position_list = State()
    which_store = State()
    await_react = State()
    get_source = State()


# @dp.message_handler(commands=['start'])
async def command_start(message: types.Message, state: FSMContext):
    flag = await db.check_user(user_id=message.from_user.id)
    if flag is False:
        sent_message = await message.answer(
            text="Мой хозяин запрещает мне разговаривать с незнакомцами 😒\n",
            reply_markup=kb_password,
        )
        async with state.proxy() as data:
            data["sent_message"] = sent_message
    else:
        await message.answer(
            text="Отправь мне <b>артикул</b> товара или <b>ссылку</b> на него",
            reply_markup=await client_kb(),
        )


@dp.callback_query_handler(text=["password"], state=None)
async def click_password(call: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data:
        sent_message = data["sent_message"]
    await sent_message.edit_text("Давай знакомиться!\nВведи пароль")
    await ClientStates.get_passwd.set()


# ================    ПРИНИМАЕМ ПАРОЛЬ И ПРОВЕРЯЕМ ЕГО   =========================
@dp.message_handler(content_types=types.ContentType.TEXT, state=ClientStates.get_passwd)
async def check_password(message: types.Message, state: FSMContext):
    MSG_PASS = message.text
    if MSG_PASS == PASSWORD:
        await db.save_client(user_id=message.from_user.id)
        await bot.send_message(
            message.from_user.id,
            text="✅ Пароль верный!\n\nОтправь мне <b>артикул</b> товара или <b>ссылку</b> на него",
            reply_markup=await client_kb(),
        )
        await state.finish()
    else:
        await bot.send_message(message.from_user.id, text="❌ Пароль не верный...")


# ===========   ЗАХВАТ ВСЕХ ТЕКСТОВЫХ СООБЩЕНИЙ ОТПРАВЛЕННЫХ БОТУ   ============
# @dp.message_handler(content_types=types.ContentType.TEXT, state=None)
async def processing_arcicul(message: types.Message, state: FSMContext):
    USER_LIST = await db.get_all_users()
    if message.from_user.id not in USER_LIST:
        await message.answer("Я не разговариваю с незнакомцами 😶")
        return

    msg = message.text
    articul = None
    source = ""

    # Обработка АРТИКУЛА -> переход к вопросу об источнике
    if re.match(r"^\d{5,}$", msg):
        articul = msg
        sent_message = await message.answer(
            text="Выберите источник", reply_markup=await enter_source_kb(articul)
        )
        async with state.proxy() as data:
            data["sent_message"] = sent_message
        await ClientStates.which_store.set()
        return

    # ОБРАБОТКА ССЫЛОК -> автоматическое определение источника
    elif re.match(r"^https?://www\.wildberries\.ru/catalog/\d+", msg):
        match = re.search(r"\d+", msg)  # Извлекаем артикул из ссылки
        if match:
            articul = match.group()
            source = "wb"
        else:
            await message.reply(
                "Ссылка не определяется, попробуйте прислать <b>артикул</b>."
            )
            return

    elif re.match(r"^https?://www\.ozon\.ru/product/.*", msg):
        match = re.search(r"\d{9}", msg)
        if match:
            articul = match.group()
            source = "ozon"
        else:
            await message.reply(
                "Ссылка не определяется, попробуйте прислать <b>артикул</b>."
            )
            return
    else:
        await message.answer("Это не похоже на артикул или ссылку")
        return

    # ===== ЕСЛИ ВСЕ В ПОРЯДКЕ, ТО НАЧИНАЮ ОБРАБОТКУ ТОВАРА =====

    if articul is not None:
        sent_message = await message.answer("🔎 Поиск товара...")
        if source == "wb":
            result = await selen.wb_search_tovar(
                articul=articul, user_id=message.from_user.id
            )
        elif source == "ozon":
            result = await selen.ozon_search_tovar(
                articul=articul, user_id=message.from_user.id
            )
        else:
            await message.answer(
                "Произошло что-то не понятное с определением источника ссылки"
            )
            return

        if result is None:
            await sent_message.edit_text(f"❌ Товар не найден")
            return
        else:
            result["articul"] = articul
            if result["img"] == b"":
                price = (
                    "Нет в наличии"
                    if result["price"] == False
                    else str(result["price"]) + " ₽"
                )
                msg_ = f"<b>Артикул:</b> {result['articul']}\n<b>Название:</b> {result['name']}\n<b>Цена:</b> {price}"
                await sent_message.edit_text(msg_, reply_markup=kb_react)
            else:
                await sent_message.delete()
                price = (
                    "Нет в наличии"
                    if result["price"] == False
                    else str(result["price"]) + " ₽"
                )
                sent_message = await message.answer_photo(
                    photo=result["img"],
                    caption=f"<b>Артикул:</b> {result['articul']}\n<b>Название:</b> {result['name']}\n<b>Цена:</b> {price}",
                    reply_markup=kb_react,
                )
            async with state.proxy() as data:
                data["result"] = result
                data["sent_message"] = sent_message
            await ClientStates.await_react.set()


@dp.callback_query_handler(
    text_contains="#", state=ClientStates.which_store
)  # text=['wb, ozon']
async def enter_source(call: types.CallbackQuery, state: FSMContext):
    # Удаление сообщения с кнопками выбора источника
    async with state.proxy() as data:
        sent_message = data["sent_message"]
        await sent_message.delete()

    source, articul = call.data.split("#")

    sent_message = await call.message.answer("🔎 Поиск товара...")

    if source == "wb":
        result = await selen.wb_search_tovar(
            articul=articul, user_id=call.message.from_user.id
        )
        source_ = "Wildberries 🟣"

    elif source == "ozon":
        result = await selen.ozon_search_tovar(
            articul=articul, user_id=call.message.from_user.id
        )
        source_ = "OZON 🔵"

    else:
        await call.message.answer(
            "Произошло что-то не понятное с определением источника артикула"
        )
        await state.finish()
        return

    # ===== ЕСЛИ ВСЕ В ПОРЯДКЕ, ТО НАЧИНАЮ ОБРАБОТКУ ТОВАРА =====

    if result is None:
        await sent_message.edit_text(f"❌ Товар не найден")
        await state.finish()
        return
    else:
        result["articul"] = articul
        if result["img"] == b"":
            price = (
                "Нет в наличии"
                if result["price"] == False
                else str(result["price"]) + " ₽"
            )
            msg_ = f"{source_}\n<b>Артикул:</b> {result['articul']}\n<b>Название:</b> {result['name']}\n<b>Цена:</b> {price}"
            await sent_message.edit_text(msg_, reply_markup=kb_react)
        else:
            await sent_message.delete()
            price = (
                "Нет в наличии"
                if result["price"] == False
                else str(result["price"]) + " ₽"
            )
            sent_message = await call.message.answer_photo(
                photo=result["img"],
                caption=f"{source_}\n<b>Артикул:</b> {result['articul']}\n<b>Название:</b> {result['name']}\n<b>Цена:</b> {price}",
                reply_markup=kb_react,
            )
        async with state.proxy() as data:
            data["result"] = result
            data["sent_message"] = sent_message
            data["source"] = source
        await ClientStates.await_react.set()


@dp.callback_query_handler(text=["add_position"], state=ClientStates.await_react)
async def add_position(call: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data:
        result = data["result"]
        sent_message = data["sent_message"]
        source = data["source"]
    flag = await db.check_position(
        articul=int(result["articul"]), user_id=call.from_user.id, source=source
    )
    if flag is True:
        await bot.send_message(
            call.from_user.id, f"⚠️Товар с таким артикулом уже есть среди отслеживаемых"
        )
        await sent_message.edit_reply_markup(reply_markup=None)
        await state.finish()
        return
    else:
        # сохранние товара в БД
        time_now = int(datetime.now().timestamp())
        price = "Нет в наличии" if result["price"] == False else result["price"]
        await db.save_position(
            articul=int(result["articul"]),
            name=result["name"],
            price=price,
            date_time=time_now,
            user_id=call.from_user.id,
            img=result["img"],
            source=source,
        )
        await state.finish()
        await sent_message.edit_reply_markup(reply_markup=None)
        await bot.send_message(call.from_user.id, "✅ Позиция добавлена!")


@dp.callback_query_handler(text=["cancel"], state="*")
async def registration_new_user(call: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data:
        sent_message = data["sent_message"]
    current_state = await state.get_state()
    if current_state is not None:
        await state.finish()
    await sent_message.edit_reply_markup(reply_markup=None)


@dp.message_handler(commands=["my_positions"])
@dp.message_handler(Text(equals="мои позиции", ignore_case=True))
async def my_positions(message: types.Message, state: FSMContext):
    try:
        wb_position_list = await db.get_all_position(
            user_id=message.from_user.id, source="wb"
        )
        ozon_position_list = await db.get_all_position(
            user_id=message.from_user.id, source="ozon"
        )

        if len(wb_position_list) == 0:
            await message.answer("⚠️ У вас нет отслеживаемых позиций на Wildberries 🟣")
        else:
            msg = "📋 Список отслеживаемых позиций Wildberries 🟣:\n\n"
            count = 0
            for item in wb_position_list:
                price = (
                    str(item[2]) + " ₽"
                    if str(item[2]) != "Нет в наличии"
                    else str(item[2])
                )
                msg += f'🔰  {item[0]}\n<b>Название:</b> {item[1]}\n<b>Цена:</b> {price}\n<a href="https://www.wildberries.ru/catalog/{item[0]}/detail.aspx">ССЫЛКА</a>\n'
                msg += "\n"
                count += 1
                if count == 20:
                    await message.answer(msg)
                    msg = ""
                    count = 0
            if count > 0:
                await message.answer(msg)

        if len(ozon_position_list) == 0:
            await message.answer("⚠️ У вас нет отслеживаемых позиций на OZON 🔵")
        else:
            msg = "📋 Список отслеживаемых позиций OZON 🔵:\n\n"
            count = 0
            for item in ozon_position_list:
                price = (
                    str(item[2]) + " ₽"
                    if str(item[2]) != "Нет в наличии"
                    else str(item[2])
                )
                msg += f'🔰  {item[0]}\n<b>Название:</b> {item[1]}\n<b>Цена:</b> {price}\n<a href="https://www.ozon.ru/product/{item[0]}">ССЫЛКА</a>\n'
                msg += "\n"
                count += 1
                if count == 20:
                    await message.answer(msg)
                    msg = ""
                    count = 0
            if count > 0:
                await message.answer(msg)

    except Exception as e:
        logging.error(
            f"Исключение при получении списка всех позиций: {e} -- user -- {message.from_user.id}"
        )


@dp.message_handler(commands=["dell_position"])
@dp.message_handler(Text(equals="удалить позицию(и)", ignore_case=True))
async def delete_position(message: types.Message, state: FSMContext):
    sent_message = await message.answer(
        "Выберите источник", reply_markup=await enter_source_kb(articul="")
    )
    async with state.proxy() as data:
        data["sent_message"] = sent_message
    await ClientStates.get_source.set()


# @dp.message_handler(content_types=types.ContentType.TEXT, state=ClientStates.get_source)
@dp.callback_query_handler(text_contains="#", state=ClientStates.get_source)
async def get_source_for_delete(call: types.CallbackQuery, state: FSMContext):
    source_ = call.data.split("#")[0]
    source = "Wildberries 🟣" if source_ == "wb" else "OZON 🔵"
    async with state.proxy() as data:
        sent_message = data["sent_message"]

    await sent_message.edit_reply_markup(reply_markup=None)
    await sent_message.edit_text(f"Источник: {source}")
    position_list = await db.get_all_position(user_id=call.from_user.id, source=source_)
    if len(position_list) == 0:
        await call.message.answer("⚠️ У вас нет отслеживаемых позиций в этом источнике")
        await state.finish()
        return

    sent_message = await call.message.answer(
        f"Укажите один или несколько артикулов {source}", reply_markup=kb_cancel
    )
    async with state.proxy() as data:
        data["sent_message"] = sent_message
        data["source"] = source_
    await ClientStates.get_position_list.set()


# @dp.message_handler(content_types=types.ContentType.TEXT, state=ClientStates.get_position_list)
async def processing_delete(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        sent_message = data["sent_message"]
        source = data["source"]
    await sent_message.edit_reply_markup(reply_markup=None)
    msg = message.text
    pattern = r"^\d+(,\s*\d+)*$"
    if not re.match(pattern, msg):
        await sent_message.edit_reply_markup(reply_markup=None)
        sent_message = await message.answer(
            "⚠️В артикуле(ах) допущена ошибка, повторите ввод", reply_markup=kb_cancel
        )
        async with state.proxy() as data:
            data["sent_message"] = sent_message
        return

    else:
        msg_list = msg.split(",")
        articul_list = [int(x) for x in msg_list]
        deleted_list = ""
        for articul in articul_list:
            flag = await db.check_position(
                articul, user_id=message.from_user.id, source=source
            )
            if flag == False:
                await message.answer(
                    f"⚠️Такой позиции нет в отслеживаемых (возможно только в указанном магазине): {articul}"
                )
                continue
                # async with state.proxy() as data:
                #     data['sent_message'] = sent_message
            else:
                try:
                    await db.dell_position(
                        articul=articul, user_id=message.from_user.id, source=source
                    )
                    deleted_list += str(articul) + " "
                except Exception as e:
                    logging.error(f"Исключение при удалении позиции {e} -- {articul}")
                    await message.answer(f"❗ Позиция <b>{articul}</b> не удалена.")
                    continue
        if deleted_list != "":
            await message.answer(
                f"✅ Следующие позиции были успешно удалены:\n<b>{deleted_list}</b>"
            )
        await state.finish()


def register_handlers_client(dp: Dispatcher):
    dp.register_message_handler(command_start, commands=["start"], state=None)
    dp.register_message_handler(
        processing_arcicul, content_types=types.ContentType.TEXT, state=None
    )
    dp.register_message_handler(
        processing_delete,
        content_types=types.ContentType.TEXT,
        state=ClientStates.get_position_list,
    )
