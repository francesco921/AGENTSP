# main.py

from auth import ensure_access_token, get_profiles, select_us_profile
from amazon_api.campaigns import get_sp_campaigns
from amazon_api.targets import get_targets_for_campaign
from amazon_api.update_bids import update_target_bids


def main():
    print("=== AgentSP — Bid Manager MVP ===\n")

    # 1. Ottieni token
    access_token = ensure_access_token()

    # 2. Ottieni profili
    profiles = get_profiles(access_token)
    prof = select_us_profile(profiles)
    profile_id = prof["profileId"]

    # 3. Carica campagne
    camps = get_sp_campaigns(access_token, profile_id)
    camps_by_id = {str(c["campaignId"]): c for c in camps}

    sel = input("ID campagna da analizzare: ").strip()
    if sel not in camps_by_id:
        print("ID non valido.")
        return

    # 4. Carica targets della campagna
    print(f"\nCarico keyword della campagna {sel}...\n")
    targets = get_targets_for_campaign(access_token, profile_id, sel)

    if not targets:
        print("Nessun target trovato.")
        return

    # 5. Modifica bid
    print("\nMODIFICA BID IN CENTESIMI:")
    print("1 = aumenta")
    print("2 = diminuisci")
    choice = input("Scelta: ").strip()

    if choice not in ("1", "2"):
        print("Scelta non valida.")
        return

    cent = float(input("Di quanti centesimi (es. 5 = 0.05)?: ").strip())
    delta = round(cent / 100, 2)

    if choice == "2":
        delta = -delta

    print(f"\nApplico delta = {delta} USD a tutti i bid...\n")

    update_target_bids(access_token, profile_id, targets, delta)


if __name__ == "__main__":
    main()
