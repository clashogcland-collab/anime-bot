from aiogram.types import InlineKeyboardButton, WebAppInfo
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import config


def main_menu_kb(animes):
    kb = InlineKeyboardBuilder()
    for anime in animes:
        kb.button(text=anime["name"], callback_data=f"anime_{anime['id']}")
    kb.adjust(1)
    return kb.as_markup()


def anime_detail_kb(anime, episodes):
    kb = InlineKeyboardBuilder()
    for ep in episodes:
        kb.button(text=f"{ep['episode_number']}-qism", callback_data=f"ep_{ep['id']}")
    kb.adjust(4)

    if config.webapp_url:
        kb.row(
            InlineKeyboardButton(
                text="🎬 Onlayn ko'rish",
                web_app=WebAppInfo(url=f"{config.webapp_url}?anime_id={anime['id']}"),
            )
        )
    kb.row(InlineKeyboardButton(text="« Ro'yxatga qaytish", callback_data="back_menu"))
    return kb.as_markup()


def subscribe_kb(channel_username: str):
    kb = InlineKeyboardBuilder()
    kb.button(text="📢 Kanalga obuna bo'lish", url=f"https://t.me/{channel_username.lstrip('@')}")
    kb.button(text="✅ Tekshirish", callback_data="check_sub")
    kb.adjust(1)
    return kb.as_markup()


def admin_anime_choice_kb(animes):
    kb = InlineKeyboardBuilder()
    for anime in animes:
        kb.button(text=anime["name"], callback_data=f"admanime_{anime['id']}")
    kb.adjust(1)
    return kb.as_markup()
