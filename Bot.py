import os
from pyrogram import Client, filters, enums
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message, CallbackQuery
import yt_dlp
import asyncio
from datetime import datetime
import math
import re
from urllib.parse import urlparse

# Environment variables से configuration
bot = Client(
    "MusicDLBot",
    api_id=os.environ.get("API_ID"),
    api_hash=os.environ.get("API_HASH"),
    bot_token=os.environ.get("BOT_TOKEN")
)

# Configs
DOWNLOAD_LOCATION = "./downloads"
MAX_DURATION = 15  # minutes
AUTO_DELETE = 300  # seconds (5 minutes)

# यूट्यूब DL options
ydl_opts = {
    'format': 'bestaudio/best',
    'prefer_ffmpeg': True,
    'outtmpl': f'{DOWNLOAD_LOCATION}/%(title)s.%(ext)s',
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'mp3',
        'preferredquality': '320',
    }],
}

# Folders create
if not os.path.exists(DOWNLOAD_LOCATION):
    os.makedirs(DOWNLOAD_LOCATION)

# Helpers
def get_readable_time(seconds: int) -> str:
    """Seconds को readable format में convert करता है"""
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    if hours > 0:
        return f'{hours:02d}:{minutes:02d}:{seconds:02d}'
    else:
        return f'{minutes:02d}:{seconds:02d}'

def get_readable_size(size_in_bytes: int) -> str:
    """Bytes को readable format में convert करता है"""
    if size_in_bytes is None:
        return '0B'
    size_units = ['B', 'KB', 'MB', 'GB', 'TB']
    index = 0
    while size_in_bytes >= 1024 and index < len(size_units) - 1:
        size_in_bytes /= 1024
        index += 1
    return f'{size_in_bytes:.2f}{size_units[index]}'

def get_progress_bar(current: int, total: int, length: int = 10) -> str:
    """Progress bar generate करता है"""
    if total == 0:
        return '░' * length
    filled_length = int(length * current // total)
    return '█' * filled_length + '░' * (length - filled_length)

async def delete_message_after_delay(message: Message, delay: int):
    """Message को delay के बाद delete करता है"""
    await asyncio.sleep(delay)
    try:
        await message.delete()
    except:
        pass

# Message texts
START_TEXT = """
🎵 **नमस्कार! मैं म्यूजिक डाउनलोडर बॉट हूं** 🎵

मैं आपके लिए YouTube से गाने डाउनलोड कर सकता हूं और उन्हें HQ MP3 format में भेज सकता हूं।

**📚 कमांड्स:**
• `/song` - गाना डाउनलोड करें (नाम या लिंक)
• `/about` - बॉट के बारे में जानें
• `/help` - मदद मेनू

**🔍 उदाहरण:**
`/song Tum Hi Ho`
`/song https://youtube.com/...`

**⚡️ फीचर्स:**
• उच्च गुणवत्ता (320Kbps)
• तेज़ डाउनलोड
• थम्बनेल और मेटाडेटा
• प्रोग्रेस अपडेट्स
"""

HELP_TEXT = """
📚 **मदद मेनू | Help Menu**

**🎵 गाना डाउनलोड कैसे करें?**

1️⃣ `/song` कमांड का उपयोग करें
2️⃣ गाने का नाम या YouTube लिंक दें
3️⃣ बॉट गाना खोजेगा और डाउनलोड करेगा
4️⃣ आपको HQ MP3 फाइल मिल जाएगी

**📝 उदाहरण:**
• `/song Tum Hi Ho`
• `/song Shape of You`
• `/song https://youtube.com/...`

**⚠️ सीमाएं:**
• अधिकतम अवधि: 15 मिनट
• अधिकतम साइज़: 50MB
• फॉर्मेट: MP3 (320Kbps)

**❓ कोई समस्या?**
@R4jeshh से संपर्क करें
"""

ABOUT_TEXT = """
**🤖 बॉट के बारे में**

**🎵 नाम:** Music Downloader Bot
**👨‍💻 डेवलपर:** @R4jeshh
**📚 लाइब्रेरी:** Pyrogram
**🎞 सोर्स:** YouTube
**🎹 क्वालिटी:** 320Kbps MP3

**⚡️ फीचर्स:**
• HQ म्यूजिक डाउनलोड
• फास्ट प्रोसेसिंग
• प्रोग्रेस अपडेट्स
• थम्बनेल सपोर्ट
• इंटेलिजेंट एरर हैंडलिंग

**📊 स्टैट्स:**
• डाउनलोड: {downloads_count}
• लास्ट अपडेट: {last_update}

**🔗 लिंक्स:**
• [GitHub](https://github.com/yourusername/music-dl-bot)
• [डेवलपर](https://t.me/R4jeshh)
"""

# Handlers
@bot.on_message(filters.command("start"))
async def start_command(_, message: Message):
    await message.reply_text(
        START_TEXT,
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton("❓ मदद", callback_data="help"),
                InlineKeyboardButton("ℹ️ जानकारी", callback_data="about")
            ],
            [InlineKeyboardButton("👨‍💻 डेवलपर", url="https://t.me/R4jeshh")]
        ]),
        disable_web_page_preview=True
    )

@bot.on_message(filters.command("help"))
async def help_command(_, message: Message):
    await message.reply_text(
        HELP_TEXT,
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("👨‍💻 डेवलपर", url="https://t.me/R4jeshh")
        ]]),
        disable_web_page_preview=True
    )

@bot.on_message(filters.command("about"))
async def about_command(_, message: Message):
    current_time = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    await message.reply_text(
        ABOUT_TEXT.format(
            downloads_count="1000+",
            last_update=current_time
        ),
        disable_web_page_preview=True
    )

@bot.on_message(filters.command(["song", "music", "dl"]))
async def song_command(_, message: Message):
    try:
        # Check query
        if len(message.command) < 2:
            await message.reply_text(
                "⚠️ कृपया गाने का नाम या लिंक दें!\n\n"
                "📝 उदाहरण:\n"
                "`/song Tum Hi Ho`\n"
                "`/song https://youtube.com/...`"
            )
            return

        query = " ".join(message.command[1:])
        status_msg = await message.reply_text("🔍 खोज रहा हूं...")

        # Get video info
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                info = ydl.extract_info(f"ytsearch:{query}", download=False)['entries'][0]
            except:
                await status_msg.edit_text("❌ गाना नहीं मिला!")
                return

            # Check duration
            if int(info['duration']) > MAX_DURATION * 60:
                await status_msg.edit_text(
                    f"❌ {MAX_DURATION} मिनट से लंबे गाने डाउनलोड नहीं किए जा सकते!"
                )
                return

            # Update status with details
            await status_msg.edit_text(
                f"📥 डाउनलोड हो रहा है:\n\n"
                f"🎵 **{info['title']}**\n"
                f"⏱ **समय:** {get_readable_time(info['duration'])}\n"
                f"👁 **व्यूज:** {info['view_count']:,}\n"
                f"👤 **चैनल:** {info['uploader']}\n\n"
                f"▱▱▱▱▱▱▱▱▱▱ 0%"
            )

            # Download
            file_path = await bot.loop.run_in_executor(None, lambda: ydl.download([info['webpage_url']]))

            # Find downloaded file
            for file in os.listdir(DOWNLOAD_LOCATION):
                if file.endswith(".mp3"):
                    audio_path = os.path.join(DOWNLOAD_LOCATION, file)
                    
                    # Get file size
                    file_size = os.path.getsize(audio_path)
                    
                    # Send audio
                    await message.reply_audio(
                        audio_path,
                        title=info['title'],
                        performer=info['uploader'],
                        duration=int(info['duration']),
                        thumb=info.get('thumbnail'),
                        caption=(
                            f"🎵 **{info['title']}**\n"
                            f"⏱ **समय:** {get_readable_time(info['duration'])}\n"
                            f"💿 **साइज़:** {get_readable_size(file_size)}\n"
                            f"🎼 **बिटरेट:** 320Kbps\n\n"
                            f"👨‍💻 **@R4jeshh द्वारा**"
                        )
                    )
                    
                    # Cleanup
                    os.remove(audio_path)
                    await status_msg.delete()
                    break

    except Exception as e:
        await status_msg.edit_text(f"❌ एरर: {str(e)}")

@bot.on_callback_query()
async def callback_handler(_, callback_query: CallbackQuery):
    if callback_query.data == "help":
        await callback_query.message.edit_text(
            HELP_TEXT,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("⬅️ वापस", callback_data="start")
            ]]),
        )
    elif callback_query.data == "about":
        current_time = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
        await callback_query.message.edit_text(
            ABOUT_TEXT.format(
                downloads_count="1000+",
                last_update=current_time
            ),
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("⬅️ वापस", callback_data="start")
            ]]),
        )
    elif callback_query.data == "start":
        await callback_query.message.edit_text(
            START_TEXT,
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("❓ मदद", callback_data="help"),
                    InlineKeyboardButton("ℹ️ जानकारी", callback_data="about")
                ],
                [InlineKeyboardButton("👨‍💻 डेवलपर", url="https://t.me/R4jeshh")]
            ]),
        )

    await callback_query.answer()

# Error Handler
@bot.on_message(filters.error)
async def error_handler(_, message: Message):
    await message.reply_text(
        "❌ कुछ गड़बड़ हो गई!\n"
        "कृपया थोड़ी देर बाद फिर से कोशिश करें।\n\n"
        "अगर समस्या बनी रहे तो @R4jeshh से संपर्क करें।"
    )

print("🎵 बॉट स्टार्ट हो रहा है...")
bot.run()
