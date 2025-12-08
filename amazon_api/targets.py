# amazon_api/targets.py

import json
import requests
from settings import API_BASE_URL, CLIENT_ID


def get_targets_for_campaign(access_token, profile_id, campaign_id):
    """
    Restituisce tutti i target (keyword, product, auto, ecc.) per una campagna SP.

    Nota importante:
    - Questo endpoint è principalmente "configurativo".
    - Le metriche di performance per timeframe (impressions, clicks, ordini, ACOS)
      NON sono garantite qui e vanno prese tramite i REPORT ufficiali di Amazon Ads.
    """

    url = f"{API_BASE_URL}/adsApi/v1/query/targets"

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Amazon-Ads-CustomerId": str(profile_id),
        "Amazon-Ads-ClientId": CLIENT_ID,
        "Amazon-Advertising-API-Scope": str(profile_id),
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    # Non filtriamo piu solo targetType = KEYWORD.
    # Così vediamo:
    # - keyword target
    # - product target
    # - auto target
    payload = {
        "adProductFilter": {"include": ["SPONSORED_PRODUCTS"]},
        "campaignIdFilter": {"include": [str(campaign_id)]},
        # "targetTypeFilter": {"include": ["KEYWORD"]},  # rimosso per includere tutto
        "stateFilter": {"include": ["ENABLED", "PAUSED"]},
        "maxResults": 1000,
    }

    resp = requests.post(url, headers=headers, json=payload)

    print("============================")
    print("=== QUERY TARGETS RESULT ===")
    print(resp.status_code, resp.text)
    print("============================\n")

    resp.raise_for_status()
    data = resp.json()

    targets = data.get("targets", [])
    print(f"Trovati {len(targets)} target.\n")

    # Log base per capire cosa arriva
    for t in targets:
        tid = t.get("targetId")
        target_type = t.get("targetType")
        td = t.get("targetDetails", {}) or {}

        kw = (td.get("keywordTarget") or {}).get("keyword")
        mt = (td.get("keywordTarget") or {}).get("matchType")
        bid = (t.get("bid") or {}).get("bid")

        # Product / auto, solo per debug veloce
        if not kw:
            if "asinCategoryTarget" in td:
                info = "asinCategoryTarget"
            elif "asinBrandTarget" in td:
                info = "asinBrandTarget"
            elif "productTarget" in td:
                info = "productTarget"
            elif "autoTarget" in td:
                info = "autoTarget"
            else:
                info = "other"
        else:
            info = "keywordTarget"

        print(f"- {tid} | type={target_type} | info={info} | kw={kw} | mt={mt} | bid={bid}")

    return targets
