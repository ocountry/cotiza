"""Configuration module - loads environment variables and sets up MongoDB + logging."""

import os
import logging
from pathlib import Path
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Google OAuth configuration
GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID')
GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET')
GOOGLE_REDIRECT_URI = os.environ.get(
    'GOOGLE_REDIRECT_URI',
    'http://localhost:8001/api/auth/google/callback'
)
FRONTEND_URL = os.environ.get('FRONTEND_URL', 'http://localhost:3000')
GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"

# LLM configuration
LLM_API_KEY = os.environ.get('LLM_API_KEY')
LLM_PROVIDER = os.environ.get('LLM_PROVIDER', 'openai')
LLM_MODEL = os.environ.get('LLM_MODEL', 'gpt-4o-mini')
LLM_API_URL = os.environ.get(
    'LLM_API_URL',
    'https://api.openai.com/v1/chat/completions'
)

# Notification webhook
NOTIFICATION_WEBHOOK_URL = os.environ.get('NOTIFICATION_WEBHOOK_URL')

# Price check interval
PRICE_CHECK_INTERVAL_HOURS = int(os.environ.get('PRICE_CHECK_INTERVAL_HOURS', 12))

# Firecrawl configuration
FIRECRAWL_MODE = os.environ.get('FIRECRAWL_MODE', 'cloud').lower()
FIRECRAWL_API_KEY = os.environ.get('FIRECRAWL_API_KEY')
FIRECRAWL_SELFHOSTED_URL = os.environ.get('FIRECRAWL_SELFHOSTED_URL')