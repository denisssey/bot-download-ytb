import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.environ["BOT_TOKEN"]

DOWNLOAD_DIR = os.path.join(os.path.dirname(__file__), "downloads")
MAX_DURATION = 10 * 60
MAX_FILESIZE = 50 * 1024 * 1024

os.makedirs(DOWNLOAD_DIR, exist_ok=True)