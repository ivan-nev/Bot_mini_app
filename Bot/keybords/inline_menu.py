from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from aiogram.utils.keyboard import InlineKeyboardBuilder

LEXICON_BUTTON = {
    'StubACME': "https://miniapp.calc.press/stubacme-calc",
    'Метрическая': "https://miniapp.calc.press/metric-calc"
}


def create_menu_thread() -> InlineKeyboardMarkup:
    kb_builder = InlineKeyboardBuilder()
    buttons = [InlineKeyboardButton(text=text, web_app=WebAppInfo(url=url)) for text, url in LEXICON_BUTTON.items()]
    kb_builder.row(*buttons, width=2)
    return kb_builder.as_markup()
