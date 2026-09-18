import os
import asyncio
import logging
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import CommandStart
from aiogram.utils.keyboard import InlineKeyboardBuilder
from yt_dlp import YoutubeDL

logging.basicConfig(level=logging.INFO)

# Токен будет бережно храниться в настройках Render
API_TOKEN = os.getenv('BOT_TOKEN')

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

def search_tracks(query: str, limit: int = 3):
    ydl_opts = {
        'format': 'bestaudio/best',
        'noplaylist': True,
        'quiet': True,
        'extract_flat': 'in_playlist'
    }
    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(f"ytsearch{limit}:{query}", download=False)
        results = []
        for entry in info.get('entries', []):
            results.append({
                'id': entry.get('id'),
                'title': entry.get('title'),
                'duration': entry.get('duration_string', '--:--')
            })
        return results

def download_audio(video_id: str) -> str:
    filename = f"{video_id}.mp3"
    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'outtmpl': video_id,
        'quiet': True,
    }
    with YoutubeDL(ydl_opts) as ydl:
        ydl.download([f"https://www.youtube.com/watch?v={video_id}"])
    return filename

@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    await message.answer("Привет! Напиши название трека или исполнителя, и я найду его для тебя.")

@dp.message(F.text)
async def handle_search(message: types.Message):
    status_msg = await message.answer("Ищу варианты...")
    
    loop = asyncio.get_running_loop()
    results = await loop.run_in_executor(None, search_tracks, message.text)
    
    if not results:
        await status_msg.edit_text("Ничего не удалось найти.")
        return

    builder = InlineKeyboardBuilder()
    for idx, track in enumerate(results, 1):
        btn_text = f"{idx}. {track['title'][:35]}... ({track['duration']})"
        builder.button(text=btn_text, callback_data=f"dl_{track['id']}")
    
    builder.adjust(1)
    await status_msg.edit_text("Выбери нужный трек:", reply_markup=builder.as_markup())

@dp.callback_query(F.data.startswith("dl_"))
async def handle_download(callback: types.CallbackQuery):
    video_id = callback.data.split("dl_")[1]
    
    await callback.answer("Скачиваю трек...")
    await callback.message.edit_text("📥 Загружаю аудио...")

    loop = asyncio.get_running_loop()
    try:
        file_path = await loop.run_in_executor(None, download_audio, video_id)
        audio_file = types.FSInputFile(file_path)
        await callback.message.answer_audio(audio=audio_file)
        await callback.message.delete()
        
        if os.path.exists(file_path):
            os.remove(file_path)
    except Exception as e:
        logging.error(f"Ошибка: {e}")
        await callback.message.answer("Произошла ошибка при скачивании.")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
  
