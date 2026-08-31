import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

import database as db
from config import config

app = FastAPI(title="Anime Mini App")


@app.get("/api/anime/{anime_id}")
async def api_anime(anime_id: int):
    anime = await db.get_anime(anime_id)
    if not anime:
        return JSONResponse({"error": "topilmadi"}, status_code=404)
    episodes = await db.get_episodes(anime_id)
    return {
        "id": anime["id"],
        "name": anime["name"],
        "description": anime["description"],
        "episodes": [{"id": ep["id"], "episode_number": ep["episode_number"]} for ep in episodes],
    }


@app.get("/api/stream/{episode_id}")
async def api_stream(episode_id: int, request: Request):
    episode = await db.get_episode(episode_id)
    if not episode:
        return JSONResponse({"error": "topilmadi"}, status_code=404)

    async with httpx.AsyncClient(base_url=config.bot_api_base, timeout=30) as client:
        r = await client.get(f"/bot{config.bot_token}/getFile", params={"file_id": episode["file_id"]})
        r.raise_for_status()
        file_path = r.json()["result"]["file_path"]

    range_header = request.headers.get("range")

    async def stream_bytes():
        async with httpx.AsyncClient(base_url=config.bot_api_base, timeout=None) as client:
            headers = {"Range": range_header} if range_header else {}
            async with client.stream("GET", f"/file/bot{config.bot_token}/{file_path}", headers=headers) as resp:
                async for chunk in resp.aiter_bytes(chunk_size=1024 * 256):
                    yield chunk

    # Eslatma: to'liq video "seek" (oldinga/orqaga surish) qo'llab-quvvatlashi uchun
    # 206 Partial Content status va Content-Range header qo'shish tavsiya etiladi —
    # bu boshlang'ich versiya, kerak bo'lsa keyinroq mukammallashtiramiz.
    return StreamingResponse(stream_bytes(), media_type="video/mp4")


# Mini App'ning statik fayllari (index.html, css, js) shu papkadan xizmat qiladi
app.mount("/", StaticFiles(directory="webapp", html=True), name="webapp")
