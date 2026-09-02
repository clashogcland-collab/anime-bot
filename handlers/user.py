from aiogram import F, Router
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

import database as db
from config import config
from keyboards import anime_detail_kb, main_menu_kb

router = Router()


async def _render_anime_detail(message: Message, anime_id: int):
    anime = await db.get_anime(anime_id)
    if not anime:
        await message.answer("Bu anime topilmadi.")
        return
    episodes = await db.get_episodes(anime_id)
    caption = (
        f"<b>{anime['name']}</b>\n\n"
        f"Janr: {anime['genre'] or '-'}\n"
        f"Holat: {anime['status']}\n"
        f"Qismlar soni: {len(episodes)}"
    )
    kb = anime_detail_kb(anime, episodes)
    poster_type = anime["poster_type"] if "poster_type" in anime.keys() else "photo"
    if anime["poster_file_id"] and poster_type == "video":
        await message.answer_video(anime["poster_file_id"], caption=caption, reply_markup=kb, parse_mode="HTML")
    elif anime["poster_file_id"]:
        await message.answer_photo(anime["poster_file_id"], caption=caption, reply_markup=kb, parse_mode="HTML")
    else:
        await message.answer(caption, reply_markup=kb, parse_mode="HTML")


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, command: CommandObject):
    # Har bir /start bosilganda avvalgi FSM holati majburiy tozalanadi —
    # eski botdagi "narsalar ochilib ketish" xatosini oldini olish uchun.
    await state.clear()

    if command.args and command.args.startswith("anime_"):
        try:
            anime_id = int(command.args.split("_", 1)[1])
        except ValueError:
            anime_id = None
        if anime_id:
            await _render_anime_detail(message, anime_id)
            return

    animes = await db.list_animes()
    if not animes:
        await message.answer("Hozircha animelar mavjud emas. Tez orada qo'shiladi!")
        return
    await message.answer(
        "🎌 Anime botga xush kelibsiz!\nQuyidagi ro'yxatdan animeni tanlang:",
        reply_markup=main_menu_kb(animes),
    )


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


@router.callback_query(F.data.startswith("anime_"))
async def show_anime(callback: CallbackQuery):
    anime_id = int(callback.data.split("_", 1)[1])
    await _render_anime_detail(callback.message, anime_id)
    await callback.answer()


@router.callback_query(F.data.startswith("ep_"))
async def send_episode(callback: CallbackQuery):
    episode_id = int(callback.data.split("_", 1)[1])
    episode = await db.get_episode(episode_id)
    if not episode:
        await callback.answer("Bu qism topilmadi.", show_alert=True)
        return

    # copy_message — faylni qayta yuklamasdan, saqlash kanalidagi asl xabarni foydalanuvchiga
    # nusxalab yuboradi, shu sababli fayl hajmi cheklovi (50MB) bu yerda ta'sir qilmaydi.
    await callback.bot.copy_message(
        chat_id=callback.from_user.id,
        from_chat_id=config.storage_channel_id,
        message_id=episode["storage_message_id"],
    )
    await callback.answer()


@router.callback_query(F.data == "check_sub")
async def check_sub(callback: CallbackQuery):
    await callback.answer("Obuna qabul qilindi. Endi /start ni bosing.", show_alert=True)
