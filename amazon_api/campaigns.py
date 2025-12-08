# amazon_api/campaigns.py

import json
import requests
from settings import API_BASE_URL, CLIENT_ID


def get_sp_campaigns(access_token, profile_id):
    url = f"{API_BASE_URL}/sp/campaigns/list"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Amazon-Advertising-API-Scope": str(profile_id),
        "Amazon-Advertising-API-ClientId": CLIENT_ID,
        "Accept": "application/vnd.spcampaign.v3+json",
        "Content-Type": "application/vnd.spcampaign.v3+json",
    }
    payload = {
        "campaignFilter": {
            "campaignTypes": ["SPONSORED_PRODUCTS"],
            "stateFilter": ["ENABLED", "PAUSED"],
        },
        "maxResults": 1000,
    }

    resp = requests.post(url, headers=headers, json=payload)
    print("=== CAMPAIGNS ===")
    print(resp.status_code, resp.text)
    print("==================\n")

    resp.raise_for_status()
    data = resp.json()

    camps = data.get("campaigns", [])
    print(f"Trovate {len(camps)} campagne.\n")
    for c in camps:
        print(f"- ID: {c['campaignId']} | Nome: {c['name']} | Stato: {c['state']}")
    print()
    return camps