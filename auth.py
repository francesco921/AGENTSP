# auth.py

import json
import time
import requests
from urllib.parse import urlencode

from settings import (
    CLIENT_ID,
    CLIENT_SECRET,
    REDIRECT_URI,
    TOKEN_URL,
    LWA_AUTHORIZE_URL,
    SCOPE,
)

TOKEN_FILE = "tokens.json"


# ==========================================================
# SALVATAGGIO / CARICAMENTO TOKEN
# ==========================================================

def save_tokens(data: dict) -> None:
    with open(TOKEN_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def load_tokens() -> dict | None:
    try:
        with open(TOKEN_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return None


# ==========================================================
# URL DI LOGIN (per app.py)
# ==========================================================

def build_login_url() -> str:
    params = {
        "client_id": CLIENT_ID,
        "scope": SCOPE,
        "response_type": "code",
        "redirect_uri": REDIRECT_URI,
    }
    return f"{LWA_AUTHORIZE_URL}?{urlencode(params)}"


# ==========================================================
# SCAMBIO CODE -> TOKEN
# ==========================================================

def exchange_code_for_tokens(code: str) -> dict:
    payload = {
        "grant_type": "authorization_code",
        "code": code,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "redirect_uri": REDIRECT_URI,
    }

    r = requests.post(TOKEN_URL, data=payload)
    r.raise_for_status()
    data = r.json()

    token_data = {
        "access_token": data["access_token"],
        "refresh_token": data["refresh_token"],
        "expires_at": time.time() + data["expires_in"],
    }
    save_tokens(token_data)
    return token_data


# ==========================================================
# REFRESH TOKEN
# ==========================================================

def refresh_access_token(refresh_token: str) -> dict:
    payload = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "redirect_uri": REDIRECT_URI,
    }

    r = requests.post(TOKEN_URL, data=payload)
    r.raise_for_status()
    data = r.json()

    token_data = {
        "access_token": data["access_token"],
        "refresh_token": refresh_token,
        "expires_at": time.time() + data["expires_in"],
    }
    save_tokens(token_data)
    return token_data


# ==========================================================
# ACCESS TOKEN VALIDO
# ==========================================================

def ensure_access_token() -> str:
    tokens = load_tokens()

    if not tokens:
        raise RuntimeError("Nessun token presente. Effettua il login Amazon Ads dalla UI.")

    # ancora valido
    if time.time() < tokens["expires_at"] - 60:
        return tokens["access_token"]

    # scaduto → refresh
    refreshed = refresh_access_token(tokens["refresh_token"])
    return refreshed["access_token"]


# ==========================================================
# PROFILI AMAZON
# ==========================================================

def get_profiles(access_token: str) -> list[dict]:
    from settings import API_BASE_URL  # import locale per evitare cicli

    url = f"{API_BASE_URL}/v2/profiles"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Amazon-Advertising-API-ClientId": CLIENT_ID,
    }

    r = requests.get(url, headers=headers)
    r.raise_for_status()
    return r.json()


def select_profile(profiles: list[dict], profile_id: str | int) -> dict:
    for p in profiles:
        if str(p["profileId"]) == str(profile_id):
            return p
    raise ValueError("Profilo non trovato.")
