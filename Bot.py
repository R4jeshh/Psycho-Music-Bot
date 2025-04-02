import os
import asyncio
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message, CallbackQuery
from pytgcalls import PyTgCalls
from pytgcalls.types import Update
from pytgcalls.types.input_stream import InputAudioStream
from pytgcalls.types.input_stream.quality import HighQualityAudio
from youtube_dl import YoutubeDL
from config import API_ID, API_HASH, BOT_TOKEN, SESSION_NAME
from utils.queue import MusicQueue
from utils.helpers import download_youtube_audio, format_duration, get_youtube_details

# Initialize bot and user clients
bot = Client(
    "MusicBot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

# User account client for playing music
user = Client(
    "MusicPlayer",
    api_id=API_ID,
    api_hash=API_HASH,
    session_string=SESSION_NAME
)

# Initialize PyTgCalls
call_py = PyTgCalls(user)

# Initialize music queues for different chats
music_queue = MusicQueue()

# YouTube DL options
ydl_opts = {
    "format": "bestaudio/best",
    "extractaudio": True,
    "audio-format": "mp3",
    "outtmpl": "downloads/%(title)s.%(ext)s",
}

@bot.on_message(filters.command("start"))
async def start_command(_, message: Message):
    await message.reply_text(
        "👋 नमस्ते! मैं एक म्यूजिक बॉट हूं।\n\n"
        "मैं आपके ग्रुप की वॉइस चैट में गाने बजा सकता हूं।\n\n"
        "कमांड्स की लिस्ट के लिए /help टाइप करें।",
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "➕ मुझे अपने ग्रुप में ऐड करें",
                    url=f"https://t.me/{(await bot.get_me()).username}?startgroup=true"
                )
            ],
            [
                InlineKeyboardButton(
                    "👨‍💻 डेवलपर",
                    url="https://t.me/R4jeshh"
                )
            ]
        ])
    )

@bot.on_message(filters.command("help"))
async def help_command(_, message: Message):
    await message.reply_text(
        "**🎵 म्यूजिक बॉट कमांड्स:**\n\n"
        "/play [song name/URL] - गाना बजाने के लिए\n"
        "/pause - गाना पॉज करने के लिए\n"
        "/resume - गाना रिज्यूम करने के लिए\n"
        "/skip - अगला गाना बजाने के लिए\n"
        "/stop - गाना बंद करने के लिए\n"
        "/queue - कतार में लगे गानों की लिस्ट देखने के लिए\n"
        "/join - वॉइस चैट में जॉइन करने के लिए\n"
        "/leave - वॉइस चैट छोड़ने के लिए"
    )

@bot.on_message(filters.command("play"))
async def play_command(_, message: Message):
    try:
        # Check if user is in voice chat
        if not message.from_user:
            await message.reply_text("⚠️ यह कमांड केवल ग्रुप में काम करेगा!")
            return

        if not message.chat.type in ["group", "supergroup"]:
            await message.reply_text("⚠️ यह कमांड केवल ग्रुप में काम करेगा!")
            return

        # Get the song query
        if len(message.command) < 2:
            await message.reply_text("⚠️ गाने का नाम या URL दें!")
            return

        query = " ".join(message.command[1:])
        status_msg = await message.reply_text("🔍 खोज रहा हूं...")

        # Get song details
        try:
            song_info = await get_youtube_details(query)
            if not song_info:
                await status_msg.edit_text("❌ गाना नहीं मिला!")
                return
        except Exception as e:
            await status_msg.edit_text(f"❌ एरर: {str(e)}")
            return

        # Download and process
        try:
            audio_file = await download_youtube_audio(song_info['url'], ydl_opts)
            if not audio_file:
                await status_msg.edit_text("❌ डाउनलोड नहीं कर पाया!")
                return
        except Exception as e:
            await status_msg.edit_text(f"❌ डाउनलोड एरर: {str(e)}")
            return

        # Add to queue
        song_item = {
            'title': song_info['title'],
            'duration': song_info['duration'],
            'file': audio_file,
            'requested_by': message.from_user.mention
        }

        # Add to queue and start playing if not already playing
        position = music_queue.add(message.chat.id, song_item)
        
        if position == 0 and not call_py.get_active_call(message.chat.id):
            await start_playing(message.chat.id)
            await status_msg.edit_text(
                f"▶️ अब बज रहा है:\n"
                f"📀 {song_info['title']}\n"
                f"⏱ समय: {format_duration(song_info['duration'])}\n"
                f"👤 रिक्वेस्ट: {message.from_user.mention}"
            )
        else:
            await status_msg.edit_text(
                f"📝 कतार में जोड़ दिया गया ({position}):\n"
                f"📀 {song_info['title']}\n"
                f"⏱ समय: {format_duration(song_info['duration'])}\n"
                f"👤 रिक्वेस्ट: {message.from_user.mention}"
            )

    except Exception as e:
        await message.reply_text(f"❌ एरर: {str(e)}")

async def start_playing(chat_id):
    while True:
        if not music_queue.is_empty(chat_id):
            song = music_queue.get_current(chat_id)
            try:
                await call_py.join_group_call(
                    chat_id,
                    InputAudioStream(
                        song['file'],
                        HighQualityAudio(),
                    )
                )
                # Wait until song finishes
                await asyncio.sleep(song['duration'])
                # Remove the played song and move to next
                music_queue.remove(chat_id)
            except Exception as e:
                print(f"Error playing song: {str(e)}")
                music_queue.remove(chat_id)
        else:
            await call_py.leave_group_call(chat_id)
            break

@bot.on_message(filters.command("pause"))
async def pause_command(_, message: Message):
    try:
        if await call_py.pause_stream(message.chat.id):
            await message.reply_text("⏸️ गाना पॉज कर दिया गया है")
    except Exception as e:
        await message.reply_text(f"❌ एरर: {str(e)}")

@bot.on_message(filters.command("resume"))
async def resume_command(_, message: Message):
    try:
        if await call_py.resume_stream(message.chat.id):
            await message.reply_text("▶️ गाना फिर से शुरू कर दिया गया है")
    except Exception as e:
        await message.reply_text(f"❌ एरर: {str(e)}")

@bot.on_message(filters.command("stop"))
async def stop_command(_, message: Message):
    try:
        music_queue.clear(message.chat.id)
        await call_py.leave_group_call(message.chat.id)
        await message.reply_text("⏹️ गाना बंद कर दिया गया है")
    except Exception as e:
        await message.reply_text(f"❌ एरर: {str(e)}")

@bot.on_message(filters.command("skip"))
async def skip_command(_, message: Message):
    try:
        if music_queue.is_empty(message.chat.id):
            await message.reply_text("⚠️ कतार खाली है")
            return

        music_queue.remove(message.chat.id)
        await start_playing(message.chat.id)
        await message.reply_text("⏭️ अगला गाना बजा रहा हूं")
    except Exception as e:
        await message.reply_text(f"❌ एरर: {str(e)}")

@bot.on_message(filters.command("queue"))
async def queue_command(_, message: Message):
    try:
        if music_queue.is_empty(message.chat.id):
            await message.reply_text("⚠️ कतार खाली है")
            return

        queue_list = "📝 **कतार में लगे गाने:**\n\n"
        for i, song in enumerate(music_queue.get_queue(message.chat.id), 1):
            queue_list += f"{i}. {song['title']} | ⏱ {format_duration(song['duration'])} | 👤 {song['requested_by']}\n"

        await message.reply_text(queue_list)
    except Exception as e:
        await message.reply_text(f"❌ एरर: {str(e)}")

@bot.on_message(filters.command(["join", "userbotjoin"]))
async def join_command(_, message: Message):
    try:
        if not message.from_user:
            await message.reply_text("⚠️ यह कमांड केवल ग्रुप में काम करेगा!")
            return

        if not message.chat.type in ["group", "supergroup"]:
            await message.reply_text("⚠️ यह कमांड केवल ग्रुप में काम करेगा!")
            return

        chat_id = message.chat.id
        await user.join_chat(message.chat.username or message.chat.id)
        await message.reply_text("✅ यूजरबॉट ग्रुप में जॉइन कर गया है!")
    except Exception as e:
        await message.reply_text(f"❌ एरर: {str(e)}")

@bot.on_message(filters.command("leave"))
async def leave_command(_, message: Message):
    try:
        await user.leave_chat(message.chat.id)
        await message.reply_text("👋 यूजरबॉट ने ग्रुप छोड़ दिया है!")
    except Exception as e:
        await message.reply_text(f"❌ एरर: {str(e)}")

# Start the bot
async def start_bot():
    await bot.start()
    await user.start()
    await call_py.start()
    print("🎵 म्यूजिक बॉट शुरू हो गया है!")
    await idle()

if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(start_bot())
