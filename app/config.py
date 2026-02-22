import os
from dotenv import load_dotenv

# Load .env explicitly
basedir = os.path.abspath(os.path.dirname(__file__))
# Check if .env is in parent directory (backend/) or current app dir
env_path = os.path.join(basedir, '..', '.env')
print(f"DEBUG: Attempting to load .env from {env_path}")
print(f"DEBUG: .env exists? {os.path.exists(env_path)}")
load_dotenv(env_path)

class Config:
    MONGO_URI = os.getenv("MONGO_URI")
    print(f"DEBUG: MONGO_URI from env: {MONGO_URI}")
    JWT_SECRET = os.getenv("JWT_SECRET")
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    DB_NAME = os.getenv("DB_NAME", "mindly_db")
    
    # WhatsApp Cloud API Configuration
    WHATSAPP_ACCESS_TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN")
    WHATSAPP_VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN")
    WHATSAPP_PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID")
    
    if not MONGO_URI:
        # Fallback or error - let PyMongo handle it, but maybe print a warning?
        print("WARNING: MONGO_URI is not set in environment variables.")
