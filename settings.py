# settings.py

import os
from dotenv import load_dotenv

# Carica il file .env nella root del progetto
load_dotenv()

# ==========================================================
# VARIABILI DAL FILE .ENV
# ==========================================================

CLIENT_ID = os.getenv("AMAZON_ADS_CLIENT_ID")
CLIENT_SECRET = os.getenv("AMAZON_ADS_CLIENT_SECRET")
REDIRECT_URI = os.getenv("AMAZON_ADS_REDIRECT_URI")

if not CLIENT_ID or not CLIENT_SECRET or not REDIRECT_URI:
    raise RuntimeError(
        "Variabili .env mancanti. "
        "Devi avere AMAZON_ADS_CLIENT_ID, AMAZON_ADS_CLIENT_SECRET, AMAZON_ADS_REDIRECT_URI."
    )

# ==========================================================
# COSTANTI AMAZON ADS (FISSE)
# ==========================================================

API_BASE_URL = "https://advertising-api.amazon.com"
LWA_AUTHORIZE_URL = "https://www.amazon.com/ap/oa"
TOKEN_URL = "https://api.amazon.com/auth/o2/token"
SCOPE = "advertising::campaign_management"
