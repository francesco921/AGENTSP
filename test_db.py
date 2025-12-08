from db.database import (
    create_rule,
    get_all_rules,
    get_rule,
    update_rule,
    delete_rule,
    set_rule_enabled,
)


def main():
    print("=== CREO UNA REGOLA ===")
    rule_id = create_rule({
        "name": "Test ACOS 0-20",
        "rule_type": "ACOS_BAND",
        "campaign_id": None,         # tutte le campagne
        "marketplace": "US",
        "match_type": None,          # tutti i match
        "acos_min": 0,
        "acos_max": 20,
        "clicks_min": None,
        "clicks_max": None,
        "adjustment_type": "ABS",    # valore assoluto
        "adjustment_value": 0.05,    # +0.05
        "timeframe_days": 14,
        "frequency_days": 3,
        "enabled": 1
    })
    print("Regola creata con ID:", rule_id)

    print("\n=== TUTTE LE REGOLE DOPO INSERT ===")
    rules = get_all_rules()
    for r in rules:
        print(r)

    print("\n=== LEGGO LA REGOLA SINGOLA ===")
    r = get_rule(rule_id)
    print(r)

    print("\n=== AGGIORNO LA REGOLA (nome + adjustment_value) ===")
    update_rule(rule_id, {
        "name": "Test ACOS 0-20 UPDATED",
        "adjustment_value": 0.10
    })
    r = get_rule(rule_id)
    print(r)

    print("\n=== DISABILITO LA REGOLA ===")
    set_rule_enabled(rule_id, False)
    r = get_rule(rule_id)
    print("enabled:", r["enabled"])

    print("\n=== RIABILITO LA REGOLA ===")
    set_rule_enabled(rule_id, True)
    r = get_rule(rule_id)
    print("enabled:", r["enabled"])

    print("\n=== CANCELLO LA REGOLA ===")
    delete_rule(rule_id)
    rules = get_all_rules()
    print("Regole rimaste:", rules)


if __name__ == "__main__":
    main()
