# settings.py

import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
env_path = BASE_DIR / ".env"

# Carica il file .env esplicito
load_dotenv(dotenv_path=env_path)

# Legge sia le nostre chiavi generiche che quelle "Amazon style"
CLIENT_ID = os.getenv("CLIENT_ID") or os.getenv("AMAZON_ADS_CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET") or os.getenv("AMAZON_ADS_CLIENT_SECRET")
REDIRECT_URI = os.getenv("REDIRECT_URI") or os.getenv("AMAZON_ADS_REDIRECT_URI")

TOKENS_FILE = "tokens.json"

API_BASE_URL = "https://advertising-api.amazon.com"
LWA_TOKEN_URL = "https://api.amazon.com/auth/o2/token"
LWA_AUTH_URL = "https://www.amazon.com/ap/oa"
