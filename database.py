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
"""


async def init_db() -> None:
    async with aiosqlite.connect(config.database_path) as db:
        await db.executescript(SCHEMA)
        # Eski bazalarda poster_type ustuni bo'lmasligi mumkin — bo'lmasa qo'shamiz
        try:
            await db.execute("ALTER TABLE animes ADD COLUMN poster_type TEXT DEFAULT 'photo'")
            await db.commit()
        except Exception:
            pass


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
        cur = await db.execute("SELECT * FROM animes WHERE name LIKE ? ORDER BY name", (f"%{query}%",))
        return await cur.fetchall()


async def add_episode(anime_id: int, episode_number: int, file_id: str, storage_message_id: int) -> int:
    async with aiosqlite.connect(config.database_path) as db:
        cur = await db.execute(
            "INSERT INTO episodes (anime_id, episode_number, file_id, storage_message_id) VALUES (?, ?, ?, ?)",
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
