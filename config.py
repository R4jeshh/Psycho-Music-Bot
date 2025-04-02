import os
from dotenv import load_dotenv

load_dotenv()

# Bot credentials
API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")

# User Account Session
SESSION_NAME = os.getenv("SESSION_NAME")

# Optional configurations
DURATION_LIMIT = 60  # in minutes
COMMAND_PREFIXES = ["/", "!", "."]
