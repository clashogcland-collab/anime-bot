# Anime Bot

Anime qismlarini yuklab/ko'rsatib beruvchi Telegram bot + onlayn tomosha qilish uchun Mini App (WebApp).

## Loyiha tuzilishi

```
anime_bot/
├── main.py              # botni ishga tushirish
├── config.py            # .env dan sozlamalar
├── database.py          # SQLite (animelar, qismlar)
├── states.py            # admin uchun FSM holatlari
├── keyboards.py         # inline tugmalar
├── handlers/
│   ├── user.py          # /start, menyu, qism yuborish
│   └── admin.py         # /add_anime, /add_episode
├── middlewares/
│   └── subscribe.py     # majburiy obuna tekshiruvi
├── webapp/
│   └── index.html       # Mini App sahifasi (onlayn pleer)
├── webapp_server.py     # Mini App uchun FastAPI backend
├── requirements.txt
├── Dockerfile.bot
├── Dockerfile.webapp
├── docker-compose.yml   # lokal test uchun (bot + webapp + telegram-bot-api)
└── .env.example
```

## 1-qadam — Botni yaratish

1. @BotFather orqali yangi bot yarating, `BOT_TOKEN` oling.
2. Bitta **asosiy kanal** yarating (ommaviy, foydalanuvchilar ko'radigan) — yangi qismlar shu yerga avtomatik post qilinadi. Botni shu kanalga admin qiling.
3. Bitta **yashirin saqlash kanali** yarating (faqat siz va bot a'zo) — asl video fayllar shu yerda saqlanadi. Botni shu yerga ham admin qiling.
4. Kanal ID'larini olish: kanalga istalgan xabar yuborib, @userinfobot yoki shunga o'xshash botga forward qiling — u sizga `-100...` ko'rinishidagi ID'ni beradi.

## 2-qadam — Local Bot API Server (limitsiz fayllar uchun)

1. https://my.telegram.org ga o'z (shaxsiy) Telegram akkountingiz bilan kiring.
2. **API development tools** bo'limidan yangi ilova yarating — sizga `api_id` va `api_hash` beriladi.
3. Bularni `.env` faylidagi `TELEGRAM_API_ID` va `TELEGRAM_API_HASH` ga yozing.
4. Bu server ishga tushgach, oddiy Bot API'dagi 20MB (yuklab olish) va 50MB (yuborish) limitlari yo'qoladi — fayllar 2GB gacha muammosiz ishlaydi.

## 3-qadam — .env faylini to'ldirish

`.env.example` faylidan nusxa oling (`.env` nomi bilan) va barcha qiymatlarni to'ldiring.

## 4-qadam — Railway'da deploy qilish

Loyihani 3 ta alohida Railway service sifatida joylashtiring (bittasi — repo, 3 xil start buyrug'i/Dockerfile bilan):

1. **telegram-bot-api** — image: `gramiojs/telegram-bot-api`, muhit o'zgaruvchilar: `TELEGRAM_API_ID`, `TELEGRAM_API_HASH`, port `8081`.
2. **bot** — `Dockerfile.bot` orqali, barcha `.env` o'zgaruvchilari bilan. `BOT_API_BASE` qiymatiga birinchi service'ning Railway ichki manzilini yozing (masalan `http://telegram-bot-api.railway.internal:8081`).
3. **webapp** — `Dockerfile.webapp` orqali, ommaviy domenga ega bo'lishi kerak (Railway avtomatik beradi). Shu domenni `WEBAPP_URL` sifatida **bot** service'iga yozing.

## 5-qadam — Mini App'ni BotFather'da ulash

1. @BotFather → `/mybots` → botingizni tanlang → **Bot Settings** → **Menu Button** yoki **Configure Mini App**.
2. `WEBAPP_URL` manzilini kiriting.
3. Shundan so'ng bot chatida pastda ko'k **"Open"** tugmasi paydo bo'ladi (siz screenshot'da ko'rgan kabi).

## Admin buyruqlari

- `/add_anime` — yangi anime qo'shish (nomi → tavsif → poster → janr)
- `/add_episode` — mavjud animega qism qo'shish (anime tanlash → qism raqami → video yuborish). Video yuborilgach, bot avtomatik ravishda: saqlash kanaliga forward qiladi, bazaga yozadi, asosiy kanalga post qiladi va menyuga qo'shadi.
- `/cancel` — istalgan bosqichda joriy amalni bekor qiladi va holatni tozalaydi

## Eslatmalar

- Har bir `/start` va `/cancel` FSM holatini majburiy tozalaydi — bu eski botdagi "o'zgartirish kiritilganda narsalar ochilib ketish" muammosining oldini oladi.
- `webapp_server.py`dagi video oqimi (streaming) hozircha oddiy (`Range` header qisman qo'llab-quvvatlanadi) — video ichida oldinga/orqaga surish (seek) to'liq silliq ishlashi uchun keyinroq 206 Partial Content javobini to'liq amalga oshirish tavsiya etiladi.
- Qidiruv, obuna-bildirishnoma, reyting kabi qo'shimcha g'oyalar keyingi bosqichda alohida qo'shilishi mumkin — asosiy skelet shularni qo'shishga tayyor holda yozilgan (masalan `search_animes()` funksiyasi bazada tayyor turibdi).
