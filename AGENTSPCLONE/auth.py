# auth.py

import os
import json
import time
from urllib.parse import urlencode, urlparse, parse_qs
import requests

from settings import (
    CLIENT_ID,
    CLIENT_SECRET,
    REDIRECT_URI,
    TOKENS_FILE,
    LWA_TOKEN_URL,
    LWA_AUTH_URL,
    API_BASE_URL
)


def load_tokens():
    if not os.path.exists(TOKENS_FILE):
        return None
    with open(TOKENS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_tokens(data):
    with open(TOKENS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def get_auth_url():
    params = {
        "client_id": CLIENT_ID,
        "scope": "cpc_advertising:campaign_management",
        "response_type": "code",
        "redirect_uri": REDIRECT_URI
    }
    return f"{LWA_AUTH_URL}?{urlencode(params)}"


def exchange_code_for_tokens(auth_code):
    data = {
        "grant_type": "authorization_code",
        "code": auth_code,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "redirect_uri": REDIRECT_URI,
    }
    resp = requests.post(LWA_TOKEN_URL, data=data)
    print("=== TOKEN (auth_code) ===")
    print(resp.status_code, resp.text)
    print("=========================")

    resp.raise_for_status()
    token_data = resp.json()
    token_data["obtained_at"] = int(time.time())
    save_tokens(token_data)
    return token_data


def refresh_access_token(refresh_token):
    data = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET
    }
    resp = requests.post(LWA_TOKEN_URL, data=data)
    print("=== TOKEN (refresh) ===")
    print(resp.status_code, resp.text)
    print("=========================")

    resp.raise_for_status()
    token_data = resp.json()
    if "refresh_token" not in token_data:
        token_data["refresh_token"] = refresh_token
    token_data["obtained_at"] = int(time.time())
    save_tokens(token_data)
    return token_data


def ensure_access_token():
    tokens = load_tokens()
    if not tokens:
        print("Nessun token trovato, avvio login...")
        print("Apri nel browser questo URL:")
        print(get_auth_url())
        url = input("\nIncolla qui la URL di redirect: ").strip()

        parsed = urlparse(url)
        qs = parse_qs(parsed.query)
        if "code" not in qs:
            raise RuntimeError("Nessun parametro 'code' nella URL")
        return exchange_code_for_tokens(qs["code"][0])["access_token"]

    now = int(time.time())
    if now > tokens["obtained_at"] + tokens["expires_in"] - 300:
        print("Access token scaduto. Faccio refresh...")
        tokens = refresh_access_token(tokens["refresh_token"])

    return tokens["access_token"]


def get_profiles(access_token):
    url = f"{API_BASE_URL}/v2/profiles"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Amazon-Advertising-API-ClientId": CLIENT_ID,
        "Accept": "application/json",
    }
    resp = requests.get(url, headers=headers)
    print("=== PROFILES ===")
    print(resp.status_code, resp.text)
    print("=================")

    resp.raise_for_status()
    return resp.json()


def select_us_profile(profiles):
    us = [p for p in profiles if p.get("countryCode") == "US"]
    if not us:
        raise RuntimeError("Nessun profilo US trovato.")
    prof = us[0]
    print("\n== PROFILO US SELEZIONATO ==")
    print(json.dumps(prof, indent=2))
    print("=============================\n")
    return prof
