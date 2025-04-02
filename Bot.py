import os
import asyncio
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message
from pytgcalls import PyTgCalls
from pytgcalls.types import AudioPiped, AudioParameters
from youtube_dl import YoutubeDL

# Bot Configuration
API_ID = "22561859"  # Replace with your API ID
API_HASH = "011b61e0a533ed82a5ae800268f46ecd"  # Replace with your API Hash
BOT_TOKEN = "8054879453:AAEqPO5_aK8S3B0EVjDdK1TFj0QPxALKX6Q"  # Replace with your Bot Token
SESSION_NAME = "BQFYREMAZkQuYW3WQNFM6wJVpQ8gqlE-lxtApE1ACplneygWCWO4cj-EqHYsSSRN4NsPWzFHO3UlqFcMbDz6tHd3SW7S2IA1Yr29tpiugkP6kePa_ONAXyYL7LwyuOO9cxHO4V0eKnlahWKOlX8MGIu3ZbngtFPKzlFFdRb72Kt4wLJx0jk9DGhZ9fXdMb38poOfeoYn9AYXNE6WSjyerC9UrGGt2NWWr2HjUJj_7WrxIhmQRr1RrTDUnZ8VYYSfqZaX_AMncrKLyXyRK0DhYcHxqUpSxkoQa1rlLYfWFZJLK35SKE6Xn2UIGI1ftPLSXZaTzEPo6Bhy5vDOwWm8VGEYS-7B-gAAAAHTgtrLAA"  # Replace with your Session String

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
        "/queue - कतार में लगे गानों की लिस्ट"
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
        chat_id = message.chat.id
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
            'file': audio_file,
            'requested_by': message.from_user.mention
        }

        if not await call_py.get_active_call(chat_id):
            await call_py.join_group_call(
                chat_id,
                AudioPiped(
                    audio_file,
                    AudioParameters(
                        bitrate=48000,
                    ),
                )
            )
            add_to_queue(chat_id, song_info)
            await status_msg.edit_text(
                f"▶️ अब बज रहा है:\n"
                f"📀 {info['title']}\n"
                f"👤 चलाया: {message.from_user.mention}"
            )
        else:
            position = add_to_queue(chat_id, song_info)
            await status_msg.edit_text(
                f"📝 कतार में जोड़ा गया ({position}):\n"
                f"📀 {info['title']}\n"
                f"👤 रिक्वेस्ट: {message.from_user.mention}"
            )

    except Exception as e:
        await message.reply_text(f"❌ एरर: {str(e)}")

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
    chat_id = message.chat.id
    if get_queue(chat_id):
        try:
            remove_from_queue(chat_id)
            if get_queue(chat_id):
                next_song = get_queue(chat_id)[0]
                await call_py.change_stream(
                    chat_id,
                    AudioPiped(
                        next_song['file'],
                        AudioParameters(
                            bitrate=48000,
                        ),
                    )
                )
                await message.reply_text(
                    f"⏭️ अब बज रहा है:\n"
                    f"📀 {next_song['title']}\n"
                    f"👤 रिक्वेस्ट: {next_song['requested_by']}"
                )
            else:
                await call_py.leave_group_call(chat_id)
                await message.reply_text("⏹️ कतार खत्म हो गई है")
        except Exception as e:
            await message.reply_text(f"❌ एरर: {str(e)}")
    else:
        await message.reply_text("⚠️ कतार खाली है")

@bot.on_message(filters.command("queue"))
async def queue_command(_, message: Message):
    chat_id = message.chat.id
    if get_queue(chat_id):
        queue_list = "📝 **कतार में लगे गाने:**\n\n"
        for i, song in enumerate(get_queue(chat_id), 1):
            queue_list += f"{i}. {song['title']} | 👤 {song['requested_by']}\n"
        await message.reply_text(queue_list)
    else:
        await message.reply_text("⚠️ कतार खाली है")

# Start the bot
async def main():
    print("🎵 बॉट स्टार्ट हो रहा है...")
    if not os.path.exists("downloads"):
        os.makedirs("downloads")
    await bot.start()
    await user.start()
    await call_py.start()
    print("✅ बॉट स्टार्ट हो गया है!")
    await idle()

if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(main())
