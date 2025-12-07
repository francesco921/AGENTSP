# scheduler/runner.py

import time
from datetime import datetime
from typing import Any, Dict, List

from db.database import (
    init_db,
    get_due_rules,
    update_rule_last_run,
    log_rule_execution,
)
from rules.engine import apply_rule_to_target


# -------------------------------------------
# Queste funzioni vanno collegate al tuo codice Amazon
# -------------------------------------------

def fetch_targets_for_rule(rule: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    TODO: integra con il tuo modulo amazon_api.

    Deve restituire una lista di dict del tipo:

    {
        "target_id": "123",
        "campaign_id": "456",
        "keyword_text": "example",
        "match_type": "exact",
        "marketplace": "US",
        "bid": 0.5,
        "acos": 25.3,
        "clicks": 23,
        "impressions": 1234,
    }

    Usa rule["timeframe_days"] per decidere il periodo di analisi.
    """
    raise NotImplementedError("Collega fetch_targets_for_rule al modulo amazon_api.")


def update_bid_in_amazon(target: Dict[str, Any], new_bid: float) -> None:
    """
    TODO: integra con la tua funzione che aggiorna il bid su Amazon.

    Di solito:
      - prendi profile_id e campaign_id dal target
      - chiami l'endpoint UpdateBids per il target_id specifico
    """
    raise NotImplementedError("Collega update_bid_in_amazon al modulo amazon_api.")


# -------------------------------------------
# Logica scheduler
# -------------------------------------------

def process_single_rule(rule: Dict[str, Any]) -> None:
    """Scarica i target per una regola, applica il motore e aggiorna i bid."""
    now = datetime.utcnow()

    try:
        targets = fetch_targets_for_rule(rule)
    except NotImplementedError as exc:
        # Se non hai ancora collegato Amazon, esci senza rompere lo scheduler
        print(f"[RULE {rule.get('id')}] fetch_targets_for_rule non implementato: {exc}")
        return

    print(f"[RULE {rule.get('id')}] Trovati {len(targets)} target da valutare")

    for t in targets:
        old_bid = float(t["bid"])

        new_bid, action = apply_rule_to_target(t, rule)

        # Log sempre, anche se NO_ACTION
        log_rule_execution(
            rule_id=rule["id"],
            run_at=now,
            target=t,
            old_bid=old_bid,
            new_bid=new_bid if action in ("INCREASE", "DECREASE") else old_bid,
            action=action,
            message="",
        )

        if action in ("INCREASE", "DECREASE") and new_bid != old_bid:
            try:
                update_bid_in_amazon(t, new_bid)
                print(
                    f"[RULE {rule.get('id')}] Target {t.get('target_id')} "
                    f"bid {old_bid} -> {new_bid} ({action})"
                )
            except NotImplementedError as exc:
                print(
                    f"[RULE {rule.get('id')}] update_bid_in_amazon non implementato: {exc}"
                )

    update_rule_last_run(rule["id"], now)


def run_once_for_due_rules() -> None:
    """Esegue una sola scansione delle regole dovute."""
    init_db()
    now = datetime.utcnow()
    rules = get_due_rules(now)

    if not rules:
        print("[SCHEDULER] Nessuna regola da eseguire in questo momento.")
        return

    print(f"[SCHEDULER] Regole da eseguire: {[r['id'] for r in rules]}")

    for rule in rules:
        process_single_rule(rule)


def run_scheduler_loop(poll_interval_seconds: int = 3600) -> None:
    """
    Loop continuo. Ogni poll_interval_seconds controlla quali regole sono "due".

    Per uso reale puoi lanciare:
        python -m scheduler.runner
    o importare run_scheduler_loop da un altro modulo.
    """
    init_db()
    print("[SCHEDULER] Avviato. Controllo regole ogni", poll_interval_seconds, "secondi")

    while True:
        try:
            run_once_for_due_rules()
        except Exception as exc:
            print("[SCHEDULER] Errore durante l'esecuzione delle regole:", exc)

        time.sleep(poll_interval_seconds)


if __name__ == "__main__":
    # Avvio diretto dello scheduler
    run_scheduler_loop()
