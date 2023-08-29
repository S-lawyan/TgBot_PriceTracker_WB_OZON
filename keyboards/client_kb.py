from aiogram.types.inline_keyboard import InlineKeyboardButton
from aiogram.types.inline_keyboard import InlineKeyboardMarkup

btn_add = InlineKeyboardButton(text="Добавить позицию", callback_data="add_position")
btn_cancel = InlineKeyboardButton(text="Отмена", callback_data="cancel")
btn_password = InlineKeyboardButton(text="Ввести пароль", callback_data="password")

kb_password = InlineKeyboardMarkup()
kb_password.add(btn_password)

kb_react = InlineKeyboardMarkup()
kb_react.add(btn_add).add(btn_cancel)

kb_cancel = InlineKeyboardMarkup()
kb_cancel.add(btn_cancel)


async def enter_source_kb(articul):
    btn_wb = InlineKeyboardButton(text="Wildberries", callback_data=f"wb#{articul}")
    btn_ozon = InlineKeyboardButton(text="OZON", callback_data=f"ozon#{articul}")
    kb_source = InlineKeyboardMarkup()
    kb_source.add(btn_wb, btn_ozon).add(btn_cancel)
    return kb_source


from aiogram.types.reply_keyboard import (
    ReplyKeyboardMarkup,
    KeyboardButton,
)


async def client_kb():
    button2 = KeyboardButton(text="Мои позиции", command="my_positions")
    button3 = KeyboardButton(text="Удалить позицию(и)", command="dell_position")
    client_kb = ReplyKeyboardMarkup(resize_keyboard=True).add(button2, button3)
    return client_kb
