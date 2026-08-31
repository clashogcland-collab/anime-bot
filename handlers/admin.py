from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

import database as db
from config import config
from keyboards import admin_anime_choice_kb
from states import AddAnime, AddEpisode

router = Router()


def is_admin(user_id: int) -> bool:
    return user_id in config.admin_ids


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
    await message.answer("Anime uchun poster (rasm) yuboring:")


@router.message(AddAnime.poster, F.photo)
async def add_anime_poster(message: Message, state: FSMContext):
    await state.update_data(poster_file_id=message.photo[-1].file_id)
    await state.set_state(AddAnime.genre)
    await message.answer("Janrini yuboring (masalan: Aksiya, Fantastika):")


@router.message(AddAnime.poster)
async def add_anime_poster_invalid(message: Message):
    await message.answer("Iltimos, rasm (poster) yuboring.")


@router.message(AddAnime.genre)
async def add_anime_genre(message: Message, state: FSMContext):
    data = await state.update_data(genre=message.text)
    anime_id = await db.add_anime(
        name=data["name"],
        description=data["description"],
        poster_file_id=data["poster_file_id"],
        genre=data["genre"],
    )
    await state.clear()
    await message.answer(
        f"✅ Anime qo'shildi! ID: {anime_id}\n"
        f"Endi /add_episode orqali qismlarini qo'shishingiz mumkin."
    )


# ------------------------------------------------------------------
# QISM QO'SHISH
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
    await state.update_data(anime_id=anime_id)
    await state.set_state(AddEpisode.episode_number)
    await callback.message.answer("Qism raqamini kiriting (masalan: 1):")
    await callback.answer()


@router.message(AddEpisode.episode_number)
async def add_episode_number(message: Message, state: FSMContext):
    if not message.text or not message.text.isdigit():
        await message.answer("Iltimos, faqat raqam kiriting (masalan: 1).")
        return
    await state.update_data(episode_number=int(message.text))
    await state.set_state(AddEpisode.video)
    await message.answer("Endi video faylni yuboring (hajmi katta bo'lsa, yuklanishi biroz vaqt olishi mumkin):")


@router.message(AddEpisode.video, F.video | F.document)
async def add_episode_video(message: Message, state: FSMContext):
    data = await state.get_data()
    anime = await db.get_anime(data["anime_id"])
    if not anime:
        await state.clear()
        await message.answer("Xatolik: anime topilmadi. Qaytadan /add_episode bosing.")
        return

    forwarded = await message.forward(config.storage_channel_id)
    file_id = message.video.file_id if message.video else message.document.file_id

    episode_id = await db.add_episode(
        anime_id=anime["id"],
        episode_number=data["episode_number"],
        file_id=file_id,
        storage_message_id=forwarded.message_id,
    )

    if config.main_channel:
        bot_username = (await message.bot.get_me()).username
        caption = (
            f"🎬 <b>{anime['name']}</b>\n"
            f"{data['episode_number']}-qism qo'shildi!\n\n"
            f"👉 Ko'rish: https://t.me/{bot_username}?start=anime_{anime['id']}"
        )
        try:
            if anime["poster_file_id"]:
                await message.bot.send_photo(
                    config.main_channel, anime["poster_file_id"], caption=caption, parse_mode="HTML"
                )
            else:
                await message.bot.send_message(config.main_channel, caption, parse_mode="HTML")
        except Exception as e:
            await message.answer(f"⚠️ Kanalga post joylashda xatolik: {e}")

    await state.clear()
    await message.answer(
        f"✅ {data['episode_number']}-qism qo'shildi, menyuga qo'shildi va kanalga e'lon qilindi!\n"
        f"Yana qo'shish uchun /add_episode"
    )
    _ = episode_id


@router.message(AddEpisode.video)
async def add_episode_video_invalid(message: Message):
    await message.answer("Iltimos, video fayl yuboring.")
