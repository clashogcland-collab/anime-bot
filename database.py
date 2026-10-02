import aiosqlite

from config import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS animes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT,
    poster_file_id TEXT,
    poster_type TEXT DEFAULT 'photo',
    genre TEXT,
    status TEXT DEFAULT 'davom etmoqda',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS episodes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    anime_id INTEGER NOT NULL,
    episode_number INTEGER NOT NULL,
    file_id TEXT NOT NULL,
    storage_message_id INTEGER,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (anime_id) REFERENCES animes (id)
);

CREATE TABLE IF NOT EXISTS watch_progress (
    user_id INTEGER NOT NULL,
    anime_id INTEGER NOT NULL,
    episode_id INTEGER NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, anime_id)
);

CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS favorites (
    user_id INTEGER NOT NULL,
    anime_id INTEGER NOT NULL,
    PRIMARY KEY (user_id, anime_id)
);
"""


async def init_db() -> None:
    async with aiosqlite.connect(config.database_path) as db:
        await db.executescript(SCHEMA)
        # Eski bazalarda poster_type ustuni bo'lmasligi mumkin
        try:
            await db.execute("ALTER TABLE animes ADD COLUMN poster_type TEXT DEFAULT 'photo'")
            await db.commit()
        except Exception:
            pass
        # Eski foydalanuvchilarni ham hisobga qo'shamiz
        await db.execute(
            "INSERT OR IGNORE INTO users (user_id) SELECT DISTINCT user_id FROM watch_progress"
        )
        await db.commit()


# ------------------------------------------------------------------
# ANIME
# ------------------------------------------------------------------

async def add_anime(name: str, description: str, poster_file_id: str | None, genre: str,
                    poster_type: str = "photo", status: str = "davom etmoqda") -> int:
    async with aiosqlite.connect(config.database_path) as db:
        cur = await db.execute(
            "INSERT INTO animes (name, description, poster_file_id, poster_type, genre, status) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (name, description, poster_file_id, poster_type, genre, status),
        )
        await db.commit()
        return cur.lastrowid


async def list_animes():
    async with aiosqlite.connect(config.database_path) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM animes ORDER BY name")
        return await cur.fetchall()


async def get_anime(anime_id: int):
    async with aiosqlite.connect(config.database_path) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM animes WHERE id = ?", (anime_id,))
        return await cur.fetchone()


async def search_animes(query: str):
    async with aiosqlite.connect(config.database_path) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT * FROM animes WHERE name LIKE ? ORDER BY name", (f"%{query}%",)
        )
        return await cur.fetchall()


# ------------------------------------------------------------------
# QISMLAR
# ------------------------------------------------------------------

async def add_episode(anime_id: int, episode_number: int, file_id: str, storage_message_id: int) -> int:
    async with aiosqlite.connect(config.database_path) as db:
        cur = await db.execute(
            "INSERT INTO episodes (anime_id, episode_number, file_id, storage_message_id) "
            "VALUES (?, ?, ?, ?)",
            (anime_id, episode_number, file_id, storage_message_id),
        )
        await db.commit()
        return cur.lastrowid


async def get_episodes(anime_id: int):
    async with aiosqlite.connect(config.database_path) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT * FROM episodes WHERE anime_id = ? ORDER BY episode_number", (anime_id,)
        )
        return await cur.fetchall()


async def get_episode(episode_id: int):
    async with aiosqlite.connect(config.database_path) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM episodes WHERE id = ?", (episode_id,))
        return await cur.fetchone()


# ------------------------------------------------------------------
# DAVOM ETTIRISH
# ------------------------------------------------------------------

async def save_progress(user_id: int, anime_id: int, episode_id: int) -> None:
    async with aiosqlite.connect(config.database_path) as db:
        await db.execute(
            "INSERT OR REPLACE INTO watch_progress (user_id, anime_id, episode_id) "
            "VALUES (?, ?, ?)",
            (user_id, anime_id, episode_id),
        )
        await db.commit()


async def get_progress(user_id: int, anime_id: int):
    async with aiosqlite.connect(config.database_path) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT * FROM watch_progress WHERE user_id = ? AND anime_id = ?",
            (user_id, anime_id),
        )
        return await cur.fetchone()


# ------------------------------------------------------------------
# FOYDALANUVCHILAR VA SEVIMLILAR
# ------------------------------------------------------------------

async def add_user(user_id: int) -> None:
    async with aiosqlite.connect(config.database_path) as db:
        await db.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
        await db.commit()


async def is_favorite(user_id: int, anime_id: int) -> bool:
    async with aiosqlite.connect(config.database_path) as db:
        cur = await db.execute(
            "SELECT 1 FROM favorites WHERE user_id = ? AND anime_id = ?", (user_id, anime_id)
        )
        return await cur.fetchone() is not None


async def toggle_favorite(user_id: int, anime_id: int) -> bool:
    """True: sevimlilarga qo'shildi, False: olib tashlandi."""
    async with aiosqlite.connect(config.database_path) as db:
        cur = await db.execute(
            "SELECT 1 FROM favorites WHERE user_id = ? AND anime_id = ?", (user_id, anime_id)
        )
        exists = await cur.fetchone() is not None
        if exists:
            await db.execute(
                "DELETE FROM favorites WHERE user_id = ? AND anime_id = ?", (user_id, anime_id)
            )
        else:
            await db.execute(
                "INSERT INTO favorites (user_id, anime_id) VALUES (?, ?)", (user_id, anime_id)
            )
        await db.commit()
        return not exists


async def list_favorites(user_id: int):
    async with aiosqlite.connect(config.database_path) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT a.* FROM favorites f JOIN animes a ON a.id = f.anime_id "
            "WHERE f.user_id = ? ORDER BY a.name",
            (user_id,),
        )
        return await cur.fetchall()
