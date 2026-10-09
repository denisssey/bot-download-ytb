import asyncio
import os

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import (
    Message, CallbackQuery,
    InlineKeyboardMarkup, InlineKeyboardButton,
    FSInputFile,
)

from config import BOT_TOKEN, MAX_DURATION_SEC, MAX_FILESIZE
from downloader import get_info, download, human_size

bot = Bot(BOT_TOKEN)
dp = Dispatcher()

cache: dict[int, dict] = {}


@dp.message(CommandStart())
async def start(msg: Message):
    await msg.answer(
        "Привет. Отправляй ссылку Youtube, а я скину видео или аудио :)\n"
        "Пока поддерживаю ролики до 10 минут."
    )


@dp.message(F.text.regexp(r"^https?://"))
async def on_link(msg: Message):
    url = msg.text.strip()
    status = await msg.answer("Проверяю ссылку...")

    try:
        info = await get_info(url)
    except Exception as e:
        await status.edit_text(
            f"Не смог прочитать ссылку:\n<code>{e}</code>",
            parse_mode="HTML",
        )
        return

    duration = int(info.get("duration") or 0)
    if duration == 0:
        await status.edit_text("Не удалось определить длительность.")
        return
    if duration > MAX_DURATION_SEC:
        m = duration // 60
        await status.edit_text(f"Видео длится {m} мин. Пока лимит — 10 минут.")
        return

    cache[msg.from_user.id] = {"url": url, "info": info}

    title = (info.get("title") or "video")[:80]
    mins, secs = divmod(duration, 60)

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="MP3", callback_data="dl:audio")],
        [
            InlineKeyboardButton(text="360p", callback_data="dl:360"),
            InlineKeyboardButton(text="480p", callback_data="dl:480"),
        ],
    ])

    await status.edit_text(
        f"<b>{title}</b>\n⏱ {mins}:{secs:02d}\n\nЧто скачать?",
        reply_markup=kb,
        parse_mode="HTML",
    )


@dp.callback_query(F.data.startswith("dl:"))
async def on_choice(cb: CallbackQuery):
    mode = cb.data.split(":", 1)[1]
    entry = cache.get(cb.from_user.id)
    if not entry:
        await cb.answer("Ссылка устарела, кинь заново", show_alert=True)
        return

    await cb.answer()
    await cb.message.edit_text("⏳ Качаю...")

    try:
        path = await download(entry["url"], mode)
    except Exception as e:
        await cb.message.edit_text(
            f"Ошибка скачивания:\n<code>{e}</code>",
            parse_mode="HTML",
        )
        return

    size = os.path.getsize(path)
    if size > MAX_FILESIZE:
        os.remove(path)
        await cb.message.edit_text(
            f"Файл {human_size(size)} — больше лимита Telegram (50 МБ).\n"
            "Попробуй качество ниже или MP3."
        )
        return

    await cb.message.edit_text("Отправляю...")

    try:
        f = FSInputFile(path)
        if mode == "audio":
            await bot.send_audio(
                cb.message.chat.id, f,
                title=entry["info"].get("title"),
            )
        else:
            await bot.send_video(
                cb.message.chat.id, f,
                supports_streaming=True,
            )
        await cb.message.delete()
    finally:
        if os.path.exists(path):
            os.remove(path)


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())