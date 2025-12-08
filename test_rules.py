from rules.engine import (
    apply_rule_to_target,
    apply_rules_to_target,
)


def print_header(title: str):
    print("\n" + "=" * 60)
    print(title)
    print("=" * 60)


def main():
    # Target fittizio: una keyword/target qualsiasi
    target = {
        "target_id": "T123",
        "campaign_id": "C456",
        "keyword_text": "example keyword",
        "match_type": "exact",
        "marketplace": "US",
        "bid": 0.50,         # 0,50$
        "acos": 25.0,        # 25%
        "clicks": 5,
        "impressions": 1000,
    }

    print_header("TARGET INIZIALE")
    print(target)

    # 1) Regola ACOS: 20–30% → +0.05 (assoluto)
    rule_abs = {
        "id": 1,
        "name": "ACOS 20-30 +0.05",
        "rule_type": "ACOS_BAND",
        "campaign_id": None,
        "marketplace": "US",
        "match_type": "exact",
        "acos_min": 20,
        "acos_max": 30,
        "clicks_min": None,
        "clicks_max": None,
        "adjustment_type": "ABS",
        "adjustment_value": 0.05,
    }

    new_bid, action = apply_rule_to_target(target, rule_abs)
    print_header("REGOLA 1 - ACOS 20-30 +0.05")
    print("Old bid:", target["bid"])
    print("New bid:", new_bid)
    print("Action:", action)

    # 2) Regola ACOS: 20–30% → +10% (percentuale)
    rule_pct = {
        "id": 2,
        "name": "ACOS 20-30 +10%",
        "rule_type": "ACOS_BAND",
        "campaign_id": None,
        "marketplace": "US",
        "match_type": "exact",
        "acos_min": 20,
        "acos_max": 30,
        "clicks_min": None,
        "clicks_max": None,
        "adjustment_type": "PCT",
        "adjustment_value": 10,   # +10%
    }

    new_bid2, action2 = apply_rule_to_target(target, rule_pct)
    print_header("REGOLA 2 - ACOS 20-30 +10%")
    print("Old bid:", target["bid"])
    print("New bid:", new_bid2)
    print("Action:", action2)

    # 3) Regola LOW_TRAFFIC: meno di 10 click → +0.02
    rule_low_traffic = {
        "id": 3,
        "name": "LOW TRAFFIC < 10 click +0.02",
        "rule_type": "LOW_TRAFFIC",
        "campaign_id": None,
        "marketplace": "US",
        "match_type": "exact",
        "acos_min": None,
        "acos_max": None,
        "clicks_min": 0,
        "clicks_max": 10,
        "adjustment_type": "ABS",
        "adjustment_value": 0.02,
    }

    new_bid3, action3 = apply_rule_to_target(target, rule_low_traffic)
    print_header("REGOLA 3 - LOW TRAFFIC < 10 +0.02")
    print("Old bid:", target["bid"])
    print("New bid:", new_bid3)
    print("Action:", action3)

    # 4) Applicare PIÙ REGOLE in sequenza sullo stesso target
    rules = [rule_abs, rule_pct, rule_low_traffic]
    final_bid, logs = apply_rules_to_target(target, rules)

    print_header("APPLICAZIONE SEQUENZIALE DI 3 REGOLE")
    print("Old bid:", target["bid"])
    print("Final bid:", final_bid)
    print("Dettaglio per regola:")
    for log in logs:
        print(log)


if __name__ == "__main__":
    main()
