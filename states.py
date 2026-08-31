from aiogram.fsm.state import State, StatesGroup


class AddAnime(StatesGroup):
    name = State()
    description = State()
    poster = State()
    genre = State()


class AddEpisode(StatesGroup):
    choose_anime = State()
    episode_number = State()
    video = State()
