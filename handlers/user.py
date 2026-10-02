import re

from aiogram import F, Router
from aiogram.filters import Command, CommandObject, CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

import database as db
from config import config
from keyboards import anime_detail_kb, main_menu_kb

router = Router()

PAGE_SIZE = 40


def _page_of(episodes, episode_id):
    for i, e in enumerate(episodes):
        if e["id"] == episode_id:
            return i // PAGE_SIZE
    return 0


async def _build_kb(anime, episodes, user_id, page):
    pages = max(1, (len(episodes) + PAGE_SIZE - 1) // PAGE_SIZE)
    page = max(0, min(page, pages - 1))
    chunk = episodes[page * PAGE_SIZE:(page + 1) * PAGE_SIZE]
    kb = anime_detail_kb(anime, chunk)

    rows = []
    progress = await db.get_progress(user_id, anime["id"])
    if progress:
        last = next((e for e in episodes if e["id"] == progress["episode_id"]), None)
        if last:
            rows.append([InlineKeyboardButton(
                text=f"▶️ Davom ettirish: {last['episode_number']}-qism",
                callback_data=f"ep_{last['id']}",
            )])
            nxt = next((e for e in episodes if e["episode_number"] > last["episode_number"]), None)
            if nxt:
                rows.append([InlineKeyboardButton(
                    text=f"⏭ Keyingi qism: {nxt['episode_number']}-qism",
                    callback_data=f"ep_{nxt['id']}",
                )])

    fav = await db.is_favorite(user_id, anime["id"])
    rows.append([InlineKeyboardButton(
        text="💔 Sevimlilardan olib tashlash" if fav else "❤️ Sevimlilarga qo'shish",
        callback_data=f"fav_{anime['id']}_{page}",
    )])

    rows += kb.inline_keyboard

    if pages > 1:
        nav = []
        if page > 0:
            nav.append(InlineKeyboardButton(text="◀️ Oldingi", callback_data=f"pg_{anime['id']}_{page - 1}"))
        nav.append(InlineKeyboardButton(text=f"{page + 1}/{pages}", callback_data="noop"))
        if page < pages - 1:
            nav.append(InlineKeyboardButton(text="Keyingi ▶️", callback_data=f"pg_{anime['id']}_{page + 1}"))
        rows.append(nav)

    return InlineKeyboardMarkup(inline_keyboard=rows)


async def _render_anime_detail(message: Message, anime_id: int, user_id: int):
    anime = await db.get_anime(anime_id)
    if not anime:
        await message.answer("Bu anime topilmadi.")
        return
    episodes = await db.get_episodes(anime_id)
    caption = (
        f"<b>{anime['name']}</b>\n\n"
        f"Janr: {anime['genre'] or '-'}\n"
        f"Holat: {anime['status']}\n"
        f"Qismlar soni: {len(episodes)}\n\n"
        f"🔎 Qismni topish: nom va raqamni yozing, masalan: {anime['name']} 5"
    )

    page = 0
    progress = await db.get_progress(user_id, anime_id)
    if progress:
        page = _page_of(episodes, progress["episode_id"])
    kb = await _build_kb(anime, episodes, user_id, page)

    poster_type = anime["poster_type"] if "poster_type" in anime.keys() else "photo"
    if anime["poster_file_id"] and poster_type == "video":
        await message.answer_video(anime["poster_file_id"], caption=caption, reply_markup=kb, parse_mode="HTML")
    elif anime["poster_file_id"]:
        await message.answer_photo(anime["poster_file_id"], caption=caption, reply_markup=kb, parse_mode="HTML")
    else:
        await message.answer(caption, reply_markup=kb, parse_mode="HTML")


async def _deliver_episode(bot, user_id: int, episode):
    episodes = await db.get_episodes(episode["anime_id"])
    idx = next((i for i, e in enumerate(episodes) if e["id"] == episode["id"]), 0)

    nav = []
    if idx > 0:
        prev = episodes[idx - 1]
        nav.append(InlineKeyboardButton(text=f"⏮ {prev['episode_number']}-qism", callback_data=f"ep_{prev['id']}"))
    if idx < len(episodes) - 1:
        nxt = episodes[idx + 1]
        nav.append(InlineKeyboardButton(text=f"{nxt['episode_number']}-qism ⏭", callback_data=f"ep_{nxt['id']}"))
    rows = []
    if nav:
        rows.append(nav)
    rows.append([InlineKeyboardButton(text="📋 Qismlar ro'yxati", callback_data=f"anime_{episode['anime_id']}")])

    await bot.copy_message(
        chat_id=user_id,
        from_chat_id=config.storage_channel_id,
        message_id=episode["storage_message_id"],
        reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
    )
    await db.save_progress(user_id, episode["anime_id"], episode["id"])


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, command: CommandObject):
    await state.clear()
    await db.add_user(message.from_user.id)

    if command.args and command.args.startswith("anime_"):
        try:
            anime_id = int(command.args.split("_", 1)[1])
        except ValueError:
            anime_id = None
        if anime_id:
            await _render_anime_detail(message, anime_id, message.from_user.id)
            return

    animes = await db.list_animes()
    if not animes:
        await message.answer("Hozircha animelar mavjud emas. Tez orada qo'shiladi!")
        return
    await message.answer(
        "🎌 Anime botga xush kelibsiz!\n"
        "Ro'yxatdan animeni tanlang yoki nomini yozib qidiring.\n"
        "Aniq qismni topish uchun nom va raqamni yozing, masalan: One Piece 150\n"
        "❤️ Sevimlilar: /favorites",
        reply_markup=main_menu_kb(animes),
    )


@router.message(Command("favorites"))
async def cmd_favorites(message: Message):
    await db.add_user(message.from_user.id)
    favs = await db.list_favorites(message.from_user.id)
    if not favs:
        await message.answer(
            "❤️ Sevimlilar ro'yxati bo'sh.\n"
            "Animeni ochib, «Sevimlilarga qo'shish» tugmasini bosing."
        )
        return
    await message.answer("❤️ Sevimli animelaringiz:", reply_markup=main_menu_kb(favs))


@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Bekor qilindi. /start orqali menyuga qayting.")


@router.callback_query(F.data == "back_menu")
async def back_menu(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    animes = await db.list_animes()
    await callback.message.answer("🎌 Animelar ro'yxati:", reply_markup=main_menu_kb(animes))
    await callback.answer()


@router.callback_query(F.data == "noop")
async def noop(callback: CallbackQuery):
    await callback.answer()


@router.callback_query(F.data.startswith("pg_"))
async def change_page(callback: CallbackQuery):
    _, anime_id, page = callback.data.split("_")
    anime = await db.get_anime(int(anime_id))
    if not anime:
        await callback.answer()
        return
    episodes = await db.get_episodes(anime["id"])
    kb = await _build_kb(anime, episodes, callback.from_user.id, int(page))
    await callback.message.edit_reply_markup(reply_markup=kb)
    await callback.answer()


@router.callback_query(F.data.startswith("fav_"))
async def toggle_fav(callback: CallbackQuery):
    _, anime_id, page = callback.data.split("_")
    anime = await db.get_anime(int(anime_id))
    if not anime:
        await callback.answer()
        return
    added = await db.toggle_favorite(callback.from_user.id, anime["id"])
    episodes = await db.get_episodes(anime["id"])
    kb = await _build
