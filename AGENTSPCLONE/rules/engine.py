# rules/engine.py

from typing import Any, Dict, List, Tuple, Optional


def matches_filters(target: Dict[str, Any], rule: Dict[str, Any]) -> bool:
    """Controlla filtri base: campaign, marketplace, match type."""
    if rule.get("campaign_id") and target.get("campaign_id") != rule["campaign_id"]:
        return False

    if rule.get("marketplace") and target.get("marketplace") != rule["marketplace"]:
        return False

    if rule.get("match_type") and target.get("match_type") != rule["match_type"]:
        return False

    return True


def rule_condition_matches(target: Dict[str, Any], rule: Dict[str, Any]) -> bool:
    """Verifica le condizioni specifiche della regola."""
    rule_type = rule.get("rule_type")

    if rule_type == "ACOS_BAND":
        acos = target.get("acos")
        if acos is None:
            return False

        acos_min = rule.get("acos_min")
        acos_max = rule.get("acos_max")

        if acos_min is not None and acos < acos_min:
            return False
        if acos_max is not None and acos > acos_max:
            return False

        return True

    if rule_type == "LOW_TRAFFIC":
        clicks = target.get("clicks")
        if clicks is None:
            return False

        clicks_max = rule.get("clicks_max")
        clicks_min = rule.get("clicks_min") or 0

        if clicks < clicks_min:
            return False
        if clicks_max is not None and clicks >= clicks_max:
            return False

        return True

    # Tipo non riconosciuto, per sicurezza non applicare
    return False


def compute_delta(bid: float, rule: Dict[str, Any]) -> float:
    """Calcola la variazione del bid in base alla regola."""
    adjustment_type = rule.get("adjustment_type")
    value = rule.get("adjustment_value", 0.0) or 0.0

    if adjustment_type == "ABS":
        # valore in valuta (es: +0.05 o -0.02)
        return float(value)

    if adjustment_type == "PCT":
        # percentuale del bid (es: +10 o -5)
        return bid * float(value) / 100.0

    return 0.0


def apply_rule_to_target(
    target: Dict[str, Any],
    rule: Dict[str, Any],
    min_bid: Optional[float] = None,
    max_bid: Optional[float] = None,
) -> Tuple[float, str]:
    """
    Applica una singola regola a un target.

    Ritorna:
        new_bid, action_string
    """
    if not matches_filters(target, rule):
        return target["bid"], "SKIP_FILTER"

    if not rule_condition_matches(target, rule):
        return target["bid"], "SKIP_CONDITION"

    current_bid = float(target["bid"])
    delta = compute_delta(current_bid, rule)

    if delta == 0:
        return current_bid, "NO_ACTION"

    new_bid = current_bid + delta

    # limiti
    if min_bid is not None:
        new_bid = max(min_bid, new_bid)
    if max_bid is not None:
        new_bid = min(max_bid, new_bid)

    # arrotonda a centesimi
    new_bid = round(new_bid, 2)

    if new_bid > current_bid:
        action = "INCREASE"
    elif new_bid < current_bid:
        action = "DECREASE"
    else:
        action = "NO_ACTION"

    return new_bid, action


def apply_rules_to_target(
    target: Dict[str, Any],
    rules: List[Dict[str, Any]],
    min_bid: Optional[float] = None,
    max_bid: Optional[float] = None,
) -> Tuple[float, List[Dict[str, Any]]]:
    """
    Applica più regole in sequenza allo stesso target.

    Ritorna:
        new_bid,
        lista di log per ogni regola applicata
    """
    bid = float(target["bid"])
    logs: List[Dict[str, Any]] = []

    for rule in rules:
        new_bid, action = apply_rule_to_target(
            {**target, "bid": bid},
            rule,
            min_bid=min_bid,
            max_bid=max_bid,
        )

        logs.append(
            {
                "rule_id": rule.get("id"),
                "old_bid": bid,
                "new_bid": new_bid,
                "action": action,
            }
        )

        bid = new_bid

    return bid, logs
