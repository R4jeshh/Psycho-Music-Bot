import os
import time
import yt_dlp
from datetime import datetime
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import re
import requests
from urllib.parse import urlparse

# Bot Configuration
BOT_TOKEN = os.environ.get("BOT_TOKEN", "YOUR_BOT_TOKEN")
bot = telebot.TeleBot(BOT_TOKEN)

# Constants
DOWNLOAD_LOCATION = "./downloads"
MAX_DURATION = 15  # minutes
MAX_FILESIZE = 50  # MB
OWNER_USERNAME = "R4jeshh"
BOT_USERNAME = bot.get_me().username

# Cleanup old files
def cleanup_old_files():
    if os.path.exists(DOWNLOAD_LOCATION):
        for file in os.listdir(DOWNLOAD_LOCATION):
            try:
                file_path = os.path.join(DOWNLOAD_LOCATION, file)
                os.remove(file_path)
            except:
                pass
    else:
        os.makedirs(DOWNLOAD_LOCATION)

# YouTube DL Configuration
ydl_opts = {
    'format': 'bestaudio/best',
    'prefer_ffmpeg': True,
    'outtmpl': f'{DOWNLOAD_LOCATION}/%(title)s.%(ext)s',
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'mp3',
        'preferredquality': '320',
    }],
    'noplaylist': True,
}

def format_bytes(size):
    units = ['B', 'KB', 'MB', 'GB']
    unit_index = 0
    while size >= 1024 and unit_index < len(units) - 1:
        size /= 1024
        unit_index += 1
    return f"{size:.2f}{units[unit_index]}"

def format_duration(seconds):
    minutes, seconds = divmod(int(seconds), 60)
    hours, minutes = divmod(minutes, 60)
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    else:
        return f"{minutes:02d}:{seconds:02d}"

def format_number(number):
    if number >= 1000000:
        return f"{number/1000000:.1f}M"
    elif number >= 1000:
        return f"{number/1000:.1f}K"
    return str(number)

def is_youtube_link(url):
    pattern = r"(?:https?:\/\/)?(?:www\.)?(?:youtube\.com|youtu\.be)\/(?:watch\?v=)?([^\s&]+)"
    return bool(re.match(pattern, url))

def download_thumbnail(url):
    try:
        response = requests.get(url)
        if response.status_code == 200:
            thumb_path = f"{DOWNLOAD_LOCATION}/thumb.jpg"
            with open(thumb_path, "wb") as f:
                f.write(response.content)
            return thumb_path
    except:
        return None

@bot.message_handler(commands=['start'])
def start(message):
    cleanup_old_files()  # Cleanup on start
    markup = InlineKeyboardMarkup()
    markup.row_width = 2
    markup.add(
        InlineKeyboardButton("❓ मदद", callback_data="help"),
        InlineKeyboardButton("ℹ️ जानकारी", callback_data="about"),
        InlineKeyboardButton("👨‍💻 डेवलपर", url=f"https://t.me/{OWNER_USERNAME}")
    )
    
    welcome_text = (
        f"👋 **नमस्कार! मैं म्यूजिक डाउनलोडर बॉट हूं**\n\n"
        f"🎵 मैं YouTube से गाने डाउनलोड करके HQ MP3 में भेज सकता हूं।\n\n"
        f"📝 **गाना डाउनलोड करने के लिए:**\n"
        f"• `/song गाने का नाम` या\n"
        f"• `/song YouTube लिंक`\n\n"
        f"⚡️ **फीचर्स:**\n"
        f"• Ultra HQ (320Kbps)\n"
        f"• इंस्टेंट डाउनलोड\n"
        f"• थम्बनेल सपोर्ट\n"
        f"• एरर फ्री डाउनलोड\n\n"
        f"🔥 **मुझे अपने ग्रुप में एड करें!**"
    )
    
    bot.reply_to(message, welcome_text, parse_mode='Markdown', reply_markup=markup)

@bot.message_handler(commands=['song', 'music', 'dl'])
def song(message):
    try:
        # Check query
        if len(message.text.split()) < 2:
            bot.reply_to(
                message,
                "⚠️ **गाने का नाम या लिंक दें!**\n\n"
                "📝 **सही तरीका:**\n"
                "`/song गाने का नाम`\n"
                "`/song YouTube लिंक`\n\n"
                "💡 **उदाहरण:**\n"
                "`/song Tum Hi Ho`\n"
                "`/song https://youtube.com/...`",
                parse_mode='Markdown'
            )
            return

        query = " ".join(message.text.split()[1:])
        status_msg = bot.reply_to(message, "🔍 गाना ढूंढ रहा हूं...", parse_mode='Markdown')

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # Update status to searching
                bot.edit_message_text(
                    "🔎 YouTube पर सर्च कर रहा हूं...",
                    chat_id=status_msg.chat.id,
                    message_id=status_msg.message_id
                )

                # Get video info
                try:
                    if is_youtube_link(query):
                        info = ydl.extract_info(query, download=False)
                    else:
                        info = ydl.extract_info(f"ytsearch:{query}", download=False)['entries'][0]
                except:
                    bot.edit_message_text(
                        "❌ गाना नहीं मिला! कृपया दूसरा गाना ट्राई करें।",
                        chat_id=status_msg.chat.id,
                        message_id=status_msg.message_id
                    )
                    return

                # Check duration
                if int(info['duration']) > MAX_DURATION * 60:
                    bot.edit_message_text(
                        f"❌ {MAX_DURATION} मिनट से लंबे गाने डाउनलोड नहीं कर सकता!",
                        chat_id=status_msg.chat.id,
                        message_id=status_msg.message_id
                    )
                    return

                # Check estimated file size
                if info.get('filesize') and info['filesize'] > MAX_FILESIZE * 1024 * 1024:
                    bot.edit_message_text(
                        f"❌ {MAX_FILESIZE}MB से बड़े फाइल डाउनलोड नहीं कर सकता!",
                        chat_id=status_msg.chat.id,
                        message_id=status_msg.message_id
                    )
                    return

                # Update status with details
                bot.edit_message_text(
                    f"📥 **डाउनलोड हो रहा है:**\n\n"
                    f"🎵 **{info['title']}**\n"
                    f"⏱ **समय:** {format_duration(info['duration'])}\n"
                    f"👁 **व्यूज:** {format_number(info['view_count'])}\n"
                    f"👤 **चैनल:** {info['uploader']}\n\n"
                    f"💫 कृपया थोड़ी प्रतीक्षा करें...",
                    chat_id=status_msg.chat.id,
                    message_id=status_msg.message_id,
                    parse_mode='Markdown'
                )

                # Download thumbnail
                thumb = None
                if info.get('thumbnail'):
                    thumb = download_thumbnail(info['thumbnail'])

                # Download audio
                try:
                    ydl.download([info['webpage_url']])
                except Exception as e:
                    bot.edit_message_text(
                        f"❌ डाउनलोड एरर!\n\n`{str(e)}`",
                        chat_id=status_msg.chat.id,
                        message_id=status_msg.message_id,
                        parse_mode='Markdown'
                    )
                    return

                # Find and send the file
                for file in os.listdir(DOWNLOAD_LOCATION):
                    if file.endswith(".mp3"):
                        audio_path = os.path.join(DOWNLOAD_LOCATION, file)
                        file_size = os.path.getsize(audio_path)

                        if file_size > MAX_FILESIZE * 1024 * 1024:
                            bot.edit_message_text(
                                f"❌ फाइल बहुत बड़ी है ({format_bytes(file_size)})!",
                                chat_id=status_msg.chat.id,
                                message_id=status_msg.message_id
                            )
                            os.remove(audio_path)
                            if thumb:
                                os.remove(thumb)
                            return

                        try:
                            with open(audio_path, 'rb') as audio:
                                bot.send_audio(
                                    message.chat.id,
                                    audio,
                                    caption=(
                                        f"🎵 **{info['title']}**\n"
                                        f"⏱ **समय:** {format_duration(info['duration'])}\n"
                                        f"💿 **साइज़:** {format_bytes(file_size)}\n"
                                        f"🎼 **बिटरेट:** 320Kbps\n\n"
                                        f"👤 **रिक्वेस्ट:** {message.from_user.first_name}\n"
                                        f"🤖 **बॉट:** @{BOT_USERNAME}\n"
                                        f"👨‍💻 **डेवलपर:** @{OWNER_USERNAME}"
                                    ),
                                    duration=info['duration'],
                                    performer=info['uploader'],
                                    title=info['title'],
                                    thumb=open(thumb, 'rb') if thumb else None,
                                    parse_mode='Markdown'
                                )
                        except Exception as e:
                            bot.edit_message_text(
                                f"❌ अपलोड एरर!\n\n`{str(e)}`",
                                chat_id=status_msg.chat.id,
                                message_id=status_msg.message_id,
                                parse_mode='Markdown'
                            )
                            return
                        finally:
                            # Cleanup
                            os.remove(audio_path)
                            if thumb:
                                os.remove(thumb)
                            try:
                                bot.delete_message(status_msg.chat.id, status_msg.message_id)
                            except:
                                pass
                        break

        except Exception as e:
            bot.edit_message_text(
                f"❌ प्रोसेसिंग एरर!\n\n`{str(e)}`",
                chat_id=status_msg.chat.id,
                message_id=status_msg.message_id,
                parse_mode='Markdown'
            )
            return

    except Exception as e:
        bot.reply_to(
            message,
            f"❌ कुछ गड़बड़ हो गई!\n\n`{str(e)}`\n\nबाद में फिर से कोशिश करें।",
            parse_mode='Markdown'
        )

@bot.message_handler(commands=['help'])
def help(message):
    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("🎵 गाना डाउनलोड करें", callback_data="song_help"),
        InlineKeyboardButton("👨‍💻 डेवलपर", url=f"https://t.me/{OWNER_USERNAME}")
    )
    
    help_text = (
        "📚 **मदद | Help Menu**\n\n"
        "🎵 **गाना डाउनलोड कैसे करें?**\n\n"
        "1️⃣ `/song` कमांड का उपयोग करें\n"
        "2️⃣ गाने का नाम या YouTube लिंक दें\n"
        "3️⃣ बॉट गाना खोजेगा और डाउनलोड करेगा\n"
        "4️⃣ आपको HQ MP3 फाइल मिल जाएगी\n\n"
        "⚠️ **सीमाएं:**\n"
        f"• अधिकतम अवधि: {MAX_DURATION} मिनट\n"
        f"• अधिकतम साइज़: {MAX_FILESIZE}MB\n"
        "• फॉर्मेट: MP3 (320Kbps)\n\n"
        "❓ **समस्या है?**\n"
        f"👉 @{OWNER_USERNAME} से संपर्क करें"
    )
    
    bot.reply_to(message, help_text, parse_mode='Markdown', reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    try:
        if call.data == "help":
            markup = InlineKeyboardMarkup()
            markup.add(
                InlineKeyboardButton("⬅️ वापस", callback_data="start"),
                InlineKeyboardButton("👨‍💻 डेवलपर", url=f"https://t.me/{OWNER_USERNAME}")
            )
            
            help_text = (
                "📚 **मदद | Help Menu**\n\n"
                "🎵 **गाना डाउनलोड कैसे करें?**\n\n"
                "1️⃣ `/song` कमांड का उपयोग करें\n"
                "2️⃣ गाने का नाम या YouTube लिंक दें\n"
                "3️⃣ बॉट गाना खोजेगा और डाउनलोड करेगा\n"
                "4️⃣ आपको HQ MP3 फाइल मिल जाएगी\n\n"
                "⚠️ **सीमाएं:**\n"
                f"• अधिकतम अवधि: {MAX_DURATION} मिनट\n"
                f"• अधिकतम साइज़: {MAX_FILESIZE}MB\n"
                "• फॉर्मेट: MP3 (320Kbps)\n\n"
                "❓ **समस्या है?**\n"
                f"👉 @{OWNER_USERNAME} से संपर्क करें"
            )
            
            bot.edit_message_text(
                help_text,
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                reply_markup=markup,
                parse_mode='Markdown'
            )

        elif call.data == "about":
            markup = InlineKeyboardMarkup()
            markup.add(InlineKeyboardButton("⬅️ वापस", callback_data="start"))
            
            about_text = (
                "🤖 **बॉट के बारे में**\n\n"
                "🎵 **नाम:** Music Downloader\n"
                f"👨‍💻 **डेवलपर:** @{OWNER_USERNAME}\n"
                "🎞 **सोर्स:** YouTube\n"
                "🎹 **क्वालिटी:** 320Kbps MP3\n\n"
                "⚡️ **फीचर्स:**\n"
                "• Ultra HQ ऑडियो\n"
                "• इंस्टेंट डाउनलोड\n"
                "• थम्बनेल सपोर्ट\n"
                "• क्लीन UI\n"
                "• एरर फ्री\n\n"
                f"**📅 लास्ट अपडेट:** {datetime.now().strftime('%Y-%m-%d')}"
            )
            
            bot.edit_message_text(
                about_text,
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                reply_markup=markup,
                parse_mode='Markdown'
            )

        elif call.data == "start":
            markup = InlineKeyboardMarkup()
            markup.row_width = 2
            markup.add(
                InlineKeyboardButton("❓ मदद", callback_data="help"),
                InlineKeyboardButton("ℹ️ जानकारी", callback_data="about"),
                InlineKeyboardButton("👨‍💻 डेवलपर", url=f"https://t.me/{OWNER_USERNAME}")
            )
            
            start_text = (
                "👋 **नमस्कार! मैं म्यूजिक डाउनलोडर बॉट हूं**\n\n"
                "🎵 मैं YouTube से गाने डाउनलोड करके HQ MP3 में भेज सकता हूं।\n\n"
                "📝 **गाना डाउनलोड करने के लिए:**\n"
                "• `/song गाने का नाम` या\n"
                "• `/song YouTube लिंक`\n\n"
                "⚡️ **फीचर्स:**\n"
                "• Ultra HQ (320Kbps)\n"
                "• इंस्टेंट डाउनलोड\n"
                "• थम्बनेल सपोर्ट\n"
                "• एरर फ्री डाउनलोड\n\n"
                "🔥 **मुझे अपने ग्रुप में एड करें!**"
            )
            
            bot.edit_message_text(
                start_text,
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                reply_markup=markup,
                parse_mode='Markdown'
            )

        elif call.data == "song_help":
            markup = InlineKeyboardMarkup()
            markup.add(InlineKeyboardButton("⬅️ वापस", callback_data="help"))
            
            song_help_text = (
                "🎵 **गाना डाउनलोड करने के लिए:**\n\n"
                "1️⃣ गाने का नाम या YouTube लिंक कॉपी करें\n"
                "2️⃣ बॉट को `/song` के साथ भेजें\n"
                "3️⃣ गाना डाउनलोड होने का इंतजार करें\n"
                "4️⃣ आपको MP3 फाइल मिल जाएगी\n\n"
                "💡 **उदाहरण:**\n"
                "`/song Tum Hi Ho`\n"
                "`/song https://youtube.com/...`"
            )
            
            bot.edit_message_text(
                song_help_text,
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                reply_markup=markup,
                parse_mode='Markdown'
            )

        bot.answer_callback_query(call.id)

    except Exception as e:
        print(f"Callback Error: {e}")

print("🎵 बॉट स्टार्ट हो रहा है...")
while True:
    try:
        cleanup_old_files()  # Initial cleanup
        bot.polling(none_stop=True)
    except Exception as e:
        print(f"Bot Error: {e}")
        time.sleep(10)
