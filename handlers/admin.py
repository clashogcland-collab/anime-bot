import asyncio
import html
import re
import sqlite3
from datetime import datetime

import aiosqlite
from aiogram import Bot, F, Router
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery,
    FSInputFile,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

import database as db
from config import config
from keyboards import admin_anime_choice_kb
from states import AddAnime, AddEpisode

router = Router()


def is_admin(user_id: int) -> bool:
    return user_id in config.admin_ids


async def _fetch(sql, params=()):
    async with aiosqlite.connect(config.database_path) as conn:
        conn.row_factory = aiosqlite.Row
        cur = await conn.execute(sql, params)
        return await cur.fetchall()


async def _exec(*statements):
    """statements: (sql, params) juftliklari, hammasi bitta tranzaksiyada."""
    async with aiosqlite.connect(config.database_path) as conn:
        total = 0
        for sql, params in statements:
            cur = await conn.execute(sql, params)
            total += cur.rowcount
        await conn.commit()
        return total


# ------------------------------------------------------------------
# UMUMIY BUYRUQLAR (har qanday holatda ishlaydi)
# ------------------------------------------------------------------

@router.message(Command("cancel"))
async def cancel_any(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Bekor qilindi. /start orqali menyuga qayting.")


def _copy_db(src: str, dst: str) -> None:
    s = sqlite3.connect(src)
    d = sqlite3.connect(dst)
    try:
        s.backup(d)
    finally:
        d.close()
        s.close()


async def _send_backup(bot: Bot, chat_ids, caption: str) -> None:
    tmp = "backup_tmp.db"
    await asyncio.to_thread(_copy_db, config.database_path, tmp)
    for chat_id in chat_ids:
        try:
            await bot.send_document(
                chat_id, FSInputFile(tmp, filename="anime_bot.db"), caption=caption
            )
        except Exception:
            pass


@router.message(Command("backup"))
async def backup_db(message: Message):
    if not is_admin(message.from_user.id):
        return
    try:
        await _send_backup(message.bot, [message.from_user.id], "💾 Baza zaxirasi")
    except Exception as e:
        await message.answer(f"❌ Zaxira xatosi: {e}")


@router.message(Command("stats"))
async def stats(message: Message):
    if not is_admin(message.from_user.id):
        return
    animes = (await _fetch("SELECT COUNT(*) AS c FROM animes"))[0]["c"]
    eps = (await _fetch("SELECT COUNT(*) AS c FROM episodes"))[0]["c"]
    users = (await _fetch("SELECT COUNT(*) AS c FROM users"))[0]["c"]
    today = (await _fetch(
        "SELECT COUNT(*) AS c FROM users WHERE date(first_seen) = date('now')"
    ))[0]["c"]
    watchers = (await _fetch("SELECT COUNT(DISTINCT user_id) AS c FROM watch_progress"))[0]["c"]
    favs = (await _fetch("SELECT COUNT(*) AS c FROM favorites"))[0]["c"]
    top = await _fetch(
        "SELECT a.name AS name, COUNT(DISTINCT w.user_id) AS c "
        "FROM watch_progress w JOIN animes a ON a.id = w.anime_id "
        "GROUP BY a.id ORDER BY c DESC LIMIT 5"
    )
    text = (
        "📊 Statistika\n\n"
        f"👥 Foydalanuvchilar: {users} (bugun: +{today})\n"
        f"▶️ Qism ko'rganlar: {watchers}\n"
        f"❤️ Sevimlilar soni: {favs}\n"
        f"🎬 Animelar: {animes}\n"
        f"🎞 Qismlar: {eps}\n"
    )
    if top:
        text += "\n🔥 Eng ko'p ko'rilganlar:\n"
        for i, r in enumerate(top, 1):
            text += f"{i}. {r['name']} — {r['c']} kishi\n"
    await message.answer(text)
    if top:
        text += "\n🔥 Eng ko'p ko'rilganlar:\n"
        for i, r in enumerate(top, 1):
            text += f"{i}. {r['name']} — {r['c']} kishi\n"
    await message.answer(text)


@router.message(Command("animes"))
async def list_animes_cmd(message: Message):
    if not is_admin(message.from_user.id):
        return
    rows = await _fetch(
        "SELECT a.id, a.name, a.status, COUNT(e.id) AS c "
        "FROM animes a LEFT JOIN episodes e ON e.anime_id = a.id "
        "GROUP BY a.id ORDER BY a.id"
    )
    if not rows:
        await message.answer("Animelar yo'q.")
        return
    lines = [f"{r['id']} | {r['name']} | {r['c']} qism | {r['status']}" for r in rows]
    chunk = "📋 ID | nom | qismlar | holat\n\n"
    for line in lines:
        if len(chunk) + len(line) > 3500:
            await message.answer(chunk)
            chunk = ""
        chunk += line + "\n"
    if chunk:
        await message.answer(chunk)


@router.message(Command("delete_anime"))
async def delete_anime_start(message: Message):
    if not is_admin(message.from_user.id):
        return
    animes = await db.list_animes()
    if not animes:
        await message.answer("Animelar yo'q.")
        return
    rows = [
        [InlineKeyboardButton(text=f"🗑 {a['name']}"[:60], callback_data=f"dela_ask_{a['id']}")]
        for a in animes[:90]
    ]
    await message.answer(
        "Qaysi animeni o'chirasiz?", reply_markup=InlineKeyboardMarkup(inline_keyboard=rows)
    )


@router.callback_query(F.data.startswith("dela_ask_"))
async def delete_anime_ask(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer()
        return
    anime_id = int(callback.data.rsplit("_", 1)[1])
    anime = await db.get_anime(anime_id)
    if not anime:
        await callback.answer("Topilmadi.", show_alert=True)
        return
    eps = await db.get_episodes(anime_id)
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Ha, o'chirish", callback_data=f"dela_yes_{anime_id}"),
        InlineKeyboardButton(text="❌ Yo'q", callback_data="dela_no"),
    ]])
    await callback.message.answer(
        f"⚠️ «{anime['name']}» va uning {len(eps)} ta qismi o'chiriladi. Ishonchingiz komilmi?",
        reply_markup=kb,
    )
    await callback.answer()


@router.callback_query(F.data.startswith("dela_yes_"))
async def delete_anime_yes(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer()
        return
    anime_id = int(callback.data.rsplit("_", 1)[1])
    await _exec(
        ("DELETE FROM watch_progress WHERE anime_id = ?", (anime_id,)),
        ("DELETE FROM episodes WHERE anime_id = ?", (anime_id,)),
        ("DELETE FROM animes WHERE id = ?", (anime_id,)),
    )
    await callback.message.answer("🗑 O'chirildi. Endi /backup qiling.")
    await callback.answer()


@router.callback_query(F.data == "dela_no")
async def delete_anime_no(callback: CallbackQuery):
    await callback.message.answer("Bekor qilindi.")
    await callback.answer()


@router.message(Command("del_ep"))
async def del_ep(message: Message, command: CommandObject):
    if not is_admin(message.from_user.id):
        return
    parts = (command.args or "").split()
    if len(parts) != 2 or not all(p.isdigit() for p in parts):
        await message.answer(
            "Foydalanish: /del_ep ANIME_ID QISM_RAQAMI\n"
            "Masalan: /del_ep 1 150\nID larni /animes dan ko'ring."
        )
        return
    anime_id, number = int(parts[0]), int(parts[1])
    n = await _exec((
        "DELETE FROM episodes WHERE anime_id = ? AND episode_number = ?",
        (anime_id, number),
    ))
    await message.answer("🗑 O'chirildi." if n else "Bunday qism topilmadi.")


@router.message(Command("status"))
async def set_status(message: Message, command: CommandObject):
    if not is_admin(message.from_user.id):
        return
    parts = (command.args or "").split(maxsplit=1)
    if len(parts) != 2 or not parts[0].isdigit():
        await message.answer("Foydalanish: /status ANIME_ID matn\nMasalan: /status 1 tugagan")
        return
    n = await _exec(("UPDATE animes SET status = ? WHERE id = ?", (parts[1].strip(), int(parts[0]))))
    await message.answer("✅ Holat yangilandi." if n else "Bunday anime topilmadi.")


@router.message(Command("rename"))
async def rename_anime(message: Message, command: CommandObject):
    if not is_admin(message.from_user.id):
        return
    parts = (command.args or "").split(maxsplit=1)
    if len(parts) != 2 or not parts[0].isdigit():
        await message.answer("Foydalanish: /rename ANIME_ID Yangi nom")
        return
    n = await _exec(("UPDATE animes SET name = ? WHERE id = ?", (parts[1].strip(), int(parts[0]))))
    await message.answer("✅ Nom yangilandi." if n else "Bunday anime topilmadi.")


# ------------------------------------------------------------------
# ANIME QO'SHISH
# ------------------------------------------------------------------

@router.message(Command("add_anime"))
async def add_anime_start(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await state.clear()
    await state.set_state(AddAnime.name)
    await message.answer("🆕 Yangi anime nomini yuboring:\n(bekor qilish uchun /cancel)")


@router.message(AddAnime.name)
async def add_anime_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await state.set_state(AddAnime.description)
    await message.answer("Anime haqida qisqacha tavsif yuboring:")


@router.message(AddAnime.description)
async def add_anime_description(message: Message, state: FSMContext):
    await state.update_data(description=message.text)
    await state.set_state(AddAnime.poster)
    await message.answer("Anime uchun poster yuboring — rasm yoki video bo'lishi mumkin:")


@router.message(AddAnime.poster, F.photo)
async def add_anime_poster_photo(message: Message, state: FSMContext):
    await state.update_data(poster_file_id=message.photo[-1].file_id, poster_type="photo")
    await state.set_state(AddAnime.genre)
    await message.answer("Janrini yuboring (masalan: Aksiya, Fantastika):")


@router.message(AddAnime.poster, F.video)
async def add_anime_poster_video(message: Message, state: FSMContext):
    await state.update_data(poster_file_id=message.video.file_id, poster_type="video")
    await state.set_state(AddAnime.genre)
    await message.answer("Janrini yuboring (masalan: Aksiya, Fantastika):")


@router.message(AddAnime.poster)
async def add_anime_poster_invalid(message: Message):
    await message.answer("Iltimos, rasm yoki video (poster) yuboring.")


@router.message(AddAnime.genre)
async def add_anime_genre(message: Message, state: FSMContext):
    genre = re.sub(r"^\s*janr(?:lar|i)?\s*:\s*", "", message.text or "", flags=re.IGNORECASE).strip()
    data = await state.update_data(genre=genre)
    anime_id = await db.add_anime(
        name=data["name"],
        description=data["description"],
        poster_file_id=data["poster_file_id"],
        poster_type=data.get("poster_type", "photo"),
        genre=data["genre"],
    )
    await state.clear()

    # Kanalga faqat anime birinchi marta qo'shilganda, bitta post qilinadi.
    if config.main_channel:
        bot_username = (await message.bot.get_me()).username
        hashtag = "#" + re.sub(r"\W", "", data["name"])
        caption = (
            f"🎬 <b>{html.escape(data['name'])}</b>\n\n"
            f"{html.escape(data['description'] or '')}\n\n"
            f"🎭 Janr: {html.escape(data['genre'])}\n\n"
            f"{hashtag} #Anime #AnimeHub"
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(
                text="🎬 Ko'rish",
                url=f"https://t.me/{bot_username}?start=anime_{anime_id}",
            )
        ]])
        try:
            if data.get("poster_type") == "video":
                await message.bot.send_video(
                    config.main_channel, data["poster_file_id"],
                    caption=caption, reply_markup=kb, parse_mode="HTML",
                )
            else:
                await message.bot.send_photo(
                    config.main_channel, data["poster_file_id"],
                    caption=caption, reply_markup=kb, parse_mode="HTML",
                )
        except Exception as e:
            await message.answer(f"⚠️ Kanalga post joylashda xatolik: {e}")

    await message.answer(
        f"✅ Anime qo'shildi! ID: {anime_id}\n"
        f"Endi /add_episode orqali qismlarini qo'shishingiz mumkin."
    )


# ------------------------------------------------------------------
# QISM QO'SHISH (qism raqami video izohidan olinadi)
# ------------------------------------------------------------------

@router.message(Command("add_episode"))
async def add_episode_start(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await state.clear()
    animes = await db.list_animes()
    if not animes:
        await message.answer("Avval /add_anime orqali anime qo'shing.")
        return
    await state.set_state(AddEpisode.choose_anime)
    await message.answer("Qaysi anime uchun qism qo'shasiz?", reply_markup=admin_anime_choice_kb(animes))


@router.callback_query(AddEpisode.choose_anime, F.data.startswith("admanime_"))
async def add_episode_choose_anime(callback: CallbackQuery, state: FSMContext):
    anime_id = int(callback.data.split("_", 1)[1])
    await state.update_data(anime_id=anime_id, added=[])
    await state.set_state(AddEpisode.video)
    await callback.message.answer(
        "Videolarni yuboring. Har videoning izohiga qism raqamini yozing, masalan: 85-qism.\n\n"
        "Tugatgach:\n"
        "/done — foydalanuvchilarga xabar yuboradi\n"
        "/cancel — xabarsiz tugatadi"
    )
    await callback.answer()


async def _notify_users(bot: Bot, anime, numbers) -> int:
    rows = await _fetch(
        "SELECT DISTINCT user_id FROM watch_progress WHERE anime_id = ?", (anime["id"],)
    )
    name = html.escape(anime["name"])
    if len(numbers) == 1:
        text = f"🔔 <b>{name}</b>: {numbers[0]}-qism chiqdi!"
    else:
        text = f"🔔 <b>{name}</b>: yangi qismlar chiqdi ({numbers[0]}–{numbers[-1]}-qism, {len(numbers)} ta)!"
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="▶️ Ko'rish", callback_data=f"anime_{anime['id']}")
    ]])
    sent = 0
    for r in rows:
        uid = r["user_id"]
        if uid in config.admin_ids:
            continue
        try:
            await bot.send_message(uid, text, reply_markup=kb, parse_mode="HTML")
            sent += 1
        except Exception:
            pass
        await asyncio.sleep(0.05)
    return sent


@router.message(AddEpisode.video, Command("done"))
async def add_episode_done(message: Message, state: FSMContext):
    data = await state.get_data()
    await state.clear()
    added = sorted(set(data.get("added", [])))
    anime = await db.get_anime(data["anime_id"]) if data.get("anime_id") else None
    if not added or not anime:
        await message.answer("Tugadi. Yangi qism qo'shilmagan edi.")
        return
    sent = await _notify_users(message.bot, anime, added)
    await message.answer(
        f"✅ Tugadi. {len(added)} ta qism qo'shildi, {sent} ta foydalanuvchiga xabar yuborildi.\n"
        f"Endi /backup qiling."
    )


@router.message(AddEpisode.video, F.video | F.document)
async def add_episode_video(message: Message, state: FSMContext):
    data = await state.get_data()
    anime = await db.get_anime(data["anime_id"])
    if not anime:
        await state.clear()
        await message.answer("Xatolik: anime topilmadi. Qaytadan /add_episode bosing.")
        return

    caption = message.caption or ""
    m = re.search(r"(\d+)\s*[-–]?\s*qism", caption, re.IGNORECASE) or re.search(r"(\d+)", caption)
    if not m:
        await message.answer("❌ Izohda qism raqami yo'q. Masalan: 85-qism. Videoni izoh bilan qayta yuboring.")
        return
    episode_number = int(m.group(1))

    existing = await db.get_episodes(anime["id"])
    if any(e["episode_number"] == episode_number for e in existing):
        await message.answer(f"⚠️ {episode_number}-qism allaqachon bor, qayta qo'shilmadi.")
        return

    forwarded = await message.forward(config.storage_channel_id)
    file_id = message.video.file_id if message.video else message.document.file_id

    await db.add_episode(
        anime_id=anime["id"],
        episode_number=episode_number,
        file_id=file_id,
        storage_message_id=forwarded.message_id,
    )
    added = list(data.get("added", [])) + [episode_number]
    await state.update_data(added=added)
    await message.answer(
        f"✅ {episode_number}-qism qo'shildi! Keyingisini yuboring.\n"
        f"Tugatish: /done yoki /cancel"
    )


@router.message(AddEpisode.video)
async def add_episode_video_invalid(message: Message):
    await message.answer("Iltimos, video fayl yuboring. Tugatish: /done yoki /cancel")


# ------------------------------------------------------------------
# AVTOMATIK ZAXIRA (har 24 soatda)
# ------------------------------------------------------------------

_tasks = set()


async def _backup_loop(bot: Bot) -> None:
    await asyncio.sleep(30)
    while True:
        try:
            stamp = datetime.now().strftime("%Y-%m-%d %H:%M")
            await _send_backup(bot, config.admin_ids, f"💾 Avto zaxira ({stamp})")
        except Exception:
            pass
        await asyncio.sleep(24 * 60 * 60)


@router.startup()
async def start_backup_task(bot: Bot):
    task = asyncio.create_task(_backup_loop(bot))
    _tasks.add(task)
