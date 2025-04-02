import asyncio
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message
from pytgcalls import PyTgCalls
from pytgcalls.types import Update
from pytgcalls.types.input_stream import InputAudioStream
from pytgcalls.types.input_stream.quality import HighQualityAudio
from youtube_dl import YoutubeDL
import os

# Bot Configuration
API_ID = "YOUR_API_ID"  # Replace with your API ID
API_HASH = "YOUR_API_HASH"  # Replace with your API Hash
BOT_TOKEN = "YOUR_BOT_TOKEN"  # Replace with your Bot Token
SESSION_NAME = "YOUR_SESSION_STRING"  # Replace with your Session String (generate separately)

# Initialize clients
bot = Client(
    "MusicBot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

# User account client
user = Client(
    "MusicPlayer",
    api_id=API_ID,
    api_hash=API_HASH,
    session_string=SESSION_NAME
)

# Initialize PyTgCalls
call_py = PyTgCalls(user)

# Music Queue
queues = {}

# YouTube DL options
ydl_opts = {
    "format": "bestaudio/best",
    "extractaudio": True,
    "audio-format": "mp3",
    "outtmpl": "downloads/%(title)s.%(ext)s",
}

def get_queue(chat_id):
    if chat_id in queues:
        return queues[chat_id]
    return []

def add_to_queue(chat_id, song):
    if chat_id in queues:
        queues[chat_id].append(song)
    else:
        queues[chat_id] = [song]
    return len(queues[chat_id])

def remove_from_queue(chat_id):
    if chat_id in queues and queues[chat_id]:
        return queues[chat_id].pop(0)
    return None

def clear_queue(chat_id):
    if chat_id in queues:
        queues[chat_id] = []

# Helper function for duration formatting
def format_duration(seconds):
    minutes = seconds // 60
    seconds %= 60
    return f"{minutes:02d}:{seconds:02d}"

@bot.on_message(filters.command("start"))
async def start_command(_, message: Message):
    await message.reply_text(
        "👋 नमस्ते! मैं एक म्यूजिक बॉट हूं।\n\n"
        "मैं आपके ग्रुप की वॉइस चैट में गाने बजा सकता हूं।\n\n"
        "कमांड्स की लिस्ट के लिए /help टाइप करें।",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("➕ मुझे ग्रुप में ऐड करें", url=f"https://t.me/{(await bot.get_me()).username}?startgroup=true")],
            [InlineKeyboardButton("👨‍💻 डेवलपर", url="https://t.me/R4jeshh")]
        ])
    )

@bot.on_message(filters.command("help"))
async def help_command(_, message: Message):
    await message.reply_text(
        "**🎵 कमांड्स:**\n\n"
        "/play [गाना/URL] - गाना बजाने के लिए\n"
        "/pause - गाना रोकने के लिए\n"
        "/resume - गाना फिर से चालू करने के लिए\n"
        "/skip - अगला गाना बजाने के लिए\n"
        "/stop - गाना बंद करने के लिए\n"
        "/queue - कतार में लगे गानों की लिस्ट\n"
        "/join - वॉइस चैट में जॉइन\n"
        "/leave - वॉइस चैट से लीव"
    )

@bot.on_message(filters.command("play"))
async def play_command(_, message: Message):
    try:
        if not message.from_user:
            await message.reply_text("⚠️ यह कमांड केवल ग्रुप में काम करेगा!")
            return

        if len(message.command) < 2:
            await message.reply_text("⚠️ गाने का नाम या URL दें!")
            return

        query = " ".join(message.command[1:])
        status_msg = await message.reply_text("🔍 खोज रहा हूं...")

        # Download song
        try:
            with YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(f"ytsearch:{query}", download=False)['entries'][0]
                audio_file = f"downloads/{info['title']}.mp3"
                if not os.path.exists(audio_file):
                    ydl.download([info['webpage_url']])
        except Exception as e:
            await status_msg.edit_text(f"❌ एरर: {str(e)}")
            return

        # Add to queue
        song_info = {
            'title': info['title'],
            'duration': info['duration'],
            'file': audio_file,
            'requested_by': message.from_user.mention
        }

        position = add_to_queue(message.chat.id, song_info)

        if position == 1 and not call_py.get_active_call(message.chat.id):
            await start_playing(message.chat.id)
            await status_msg.edit_text(
                f"▶️ अब बज रहा है:\n"
                f"📀 {info['title']}\n"
                f"⏱ समय: {format_duration(info['duration'])}\n"
                f"👤 चलाया: {message.from_user.mention}"
            )
        else:
            await status_msg.edit_text(
                f"📝 कतार में जोड़ा गया ({position}):\n"
                f"📀 {info['title']}\n"
                f"⏱ समय: {format_duration(info['duration'])}\n"
                f"👤 रिक्वेस्ट: {message.from_user.mention}"
            )

    except Exception as e:
        await message.reply_text(f"❌ एरर: {str(e)}")

async def start_playing(chat_id):
    while True:
        if get_queue(chat_id):
            song = get_queue(chat_id)[0]
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
                # Remove played song
                remove_from_queue(chat_id)
            except Exception as e:
                print(f"Error playing song: {str(e)}")
                remove_from_queue(chat_id)
        else:
            await call_py.leave_group_call(chat_id)
            break

@bot.on_message(filters.command("pause"))
async def pause_command(_, message: Message):
    try:
        await call_py.pause_stream(message.chat.id)
        await message.reply_text("⏸️ गाना रोक दिया गया है")
    except Exception as e:
        await message.reply_text(f"❌ एरर: {str(e)}")

@bot.on_message(filters.command("resume"))
async def resume_command(_, message: Message):
    try:
        await call_py.resume_stream(message.chat.id)
        await message.reply_text("▶️ गाना फिर से चालू कर दिया गया है")
    except Exception as e:
        await message.reply_text(f"❌ एरर: {str(e)}")

@bot.on_message(filters.command("stop"))
async def stop_command(_, message: Message):
    try:
        clear_queue(message.chat.id)
        await call_py.leave_group_call(message.chat.id)
        await message.reply_text("⏹️ गाना बंद कर दिया गया है")
    except Exception as e:
        await message.reply_text(f"❌ एरर: {str(e)}")

@bot.on_message(filters.command("skip"))
async def skip_command(_, message: Message):
    try:
        if not get_queue(message.chat.id):
            await message.reply_text("⚠️ कतार खाली है")
            return

        remove_from_queue(message.chat.id)
        await start_playing(message.chat.id)
        await message.reply_text("⏭️ अगला गाना बजा रहा हूं")
    except Exception as e:
        await message.reply_text(f"❌ एरर: {str(e)}")

@bot.on_message(filters.command("queue"))
async def queue_command(_, message: Message):
    try:
        queue = get_queue(message.chat.id)
        if not queue:
            await message.reply_text("⚠️ कतार खाली है")
            return

        queue_list = "📝 **कतार में लगे गाने:**\n\n"
        for i, song in enumerate(queue, 1):
            queue_list += f"{i}. {song['title']} | ⏱ {format_duration(song['duration'])} | 👤 {song['requested_by']}\n"

        await message.reply_text(queue_list)
    except Exception as e:
        await message.reply_text(f"❌ एरर: {str(e)}")

@bot.on_message(filters.command(["join", "userbotjoin"]))
async def join_command(_, message: Message):
    try:
        await user.join_chat(message.chat.username or message.chat.id)
        await message.reply_text("✅ वॉइस चैट में जॉइन कर लिया है!")
    except Exception as e:
        await message.reply_text(f"❌ एरर: {str(e)}")

@bot.on_message(filters.command("leave"))
async def leave_command(_, message: Message):
    try:
        await user.leave_chat(message.chat.id)
        await message.reply_text("👋 वॉइस चैट छोड़ दिया है!")
    except Exception as e:
        await message.reply_text(f"❌ एरर: {str(e)}")

# Start the bot
async def start_bot():
    print("🎵 बॉट स्टार्ट हो रहा है...")
    await bot.start()
    await user.start()
    await call_py.start()
    print("✅ बॉट स्टार्ट हो गया है!")
    await idle()

if __name__ == "__main__":
    if not os.path.exists("downloads"):
        os.makedirs("downloads")
    asyncio.get_event_loop().run_until_complete(start_bot())
