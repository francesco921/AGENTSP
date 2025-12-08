# amazon_api/update_bids.py

import requests
import json
from settings import API_BASE_URL, CLIENT_ID

def update_target_bids(access_token, profile_id, targets, delta):

    url = f"{API_BASE_URL}/adsApi/v1/update/targets"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Amazon-Ads-CustomerId": str(profile_id),
        "Amazon-Ads-ClientId": CLIENT_ID,
        "Amazon-Advertising-API-Scope": str(profile_id),
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

    updates = []
    for t in targets:
        tid = t.get("targetId")
        old_bid = (t.get("bid") or {}).get("bid")

        if old_bid is None:
            continue

        new_bid = round(old_bid + delta, 2)
        if new_bid < 0.02:
            new_bid = 0.02

        updates.append({
            "targetId": tid,
            "bid": {"bid": new_bid}
        })

    payload = {"targets": updates}

    print("\n=== BIDS UPDATE REQUEST ===")
    print(json.dumps(payload, indent=2))
    print("============================")

    resp = requests.post(url, headers=headers, json=payload)

    print("\n=== BIDS UPDATE RESPONSE ===")
    print(resp.status_code, resp.text)
    print("============================")

    resp.raise_for_status()
    return resp.json()
