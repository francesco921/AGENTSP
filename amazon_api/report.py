# amazon_api/reports.py

import time
import json
import gzip
from io import BytesIO
from datetime import date, timedelta

import requests

from settings import API_BASE_URL, CLIENT_ID


# Intervalli di polling per la generazione del report
REPORT_POLL_INTERVAL = 5       # secondi
REPORT_POLL_TIMEOUT = 300      # secondi


def _common_headers(access_token: str, profile_id: str) -> dict:
    """
    Header standard per le chiamate Amazon Ads (reporting v3).
    """
    return {
        "Authorization": f"Bearer {access_token}",
        "Amazon-Ads-CustomerId": str(profile_id),
        "Amazon-Ads-ClientId": CLIENT_ID,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def create_sp_targeting_report(
    access_token: str,
    profile_id: str,
    start_date: date,
    end_date: date,
    campaign_ids=None,
) -> str:
    """
    Richiede la creazione di un report Targeting Sponsored Products (versione 3).

    ATTENZIONE:
    - Questo payload è un TEMPLATE basato sulla documentazione ufficiale v3:
      POST /reporting/reports
    - Potresti dover adattare:
        * reportTypeId (es. "spTargeting" oppure "sp_targeting")
        * i nomi delle colonne
        * la sintassi esatta dei filters

    Args:
        access_token: access token Amazon Ads
        profile_id: profileId Amazon Ads
        start_date: data di inizio (date)
        end_date: data di fine (date)
        campaign_ids: lista di campaignId da filtrare (opzionale)

    Returns:
        report_id (string)
    """

    url = f"{API_BASE_URL}/reporting/reports"

    headers = _common_headers(access_token, profile_id)

    # Date in formato ISO (AAAA-MM-GG) come richiesto dal v3
    start_str = start_date.isoformat()
    end_str = end_date.isoformat()

    # Nota: i nomi esatti delle colonne e del reportTypeId vanno verificati
    # sulla tua documentazione Amazon Ads (Targeting report, SPONSORED_PRODUCTS).
    configuration = {
        "adProduct": "SPONSORED_PRODUCTS",
        "reportTypeId": "spTargeting",  # eventualmente "sp_targeting" o simile
        "timeUnit": "SUMMARY",          # oppure "DAILY" se vuoi righe per giorno
        "format": "GZIP_JSON",
        "columns": [
            "campaignId",
            "adGroupId",
            "targetId",
            "impressions",
            "clicks",
            "cost",
            # nomi tipici per v3/v2, da verificare nel tuo account
            "purchases14d",
            "sales14d",
            # se disponibile direttamente
            # "acosClicks14d",
        ],
        "groupBy": ["targeting"],
    }

    filters = []
    if campaign_ids:
        # Sintassi tipica dei filtri v3; se da errore, controlla la doc v3.
        filters.append(
            {
                "field": "campaignId",
                "values": [str(cid) for cid in campaign_ids],
            }
        )

    if filters:
        configuration["filters"] = filters

    payload = {
        "name": "AgentSP SP Targeting report",
        "startDate": start_str,
        "endDate": end_str,
        "configuration": configuration,
    }

    resp = requests.post(url, headers=headers, json=payload)
    print("=== CREATE REPORT SP TARGETING ===")
    print(resp.status_code, resp.text)
    print("==================================\n")
    resp.raise_for_status()

    data = resp.json()
    report_id = data.get("reportId")
    if not report_id:
        raise RuntimeError(f"ReportId non presente nella risposta: {data}")

    return report_id


def wait_for_report(
    access_token: str,
    profile_id: str,
    report_id: str,
    timeout: int = REPORT_POLL_TIMEOUT,
    poll_interval: int = REPORT_POLL_INTERVAL,
) -> dict:
    """
    Polling su GET /reporting/reports/{reportId} finché il report non è pronto.

    Ritorna il JSON di meta-dati del report (contiene 'status' e 'location').
    """

    url = f"{API_BASE_URL}/reporting/reports/{report_id}"
    headers = _common_headers(access_token, profile_id)

    start_ts = time.time()

    while True:
        resp = requests.get(url, headers=headers)
        print("=== GET REPORT STATUS ===")
        print(resp.status_code, resp.text[:400])
        print("=========================\n")
        resp.raise_for_status()
        data = resp.json()

        status = data.get("status")
        if status == "SUCCESS":
            return data
        if status in ("FAILURE", "CANCELLED"):
            raise RuntimeError(f"Report {report_id} fallito con status={status}")

        if time.time() - start_ts > timeout:
            raise TimeoutError(
                f"Timeout in attesa del report {report_id}, ultimo status={status}"
            )

        time.sleep(poll_interval)


def download_report_gzip_json(location_url: str) -> list:
    """
    Scarica il file da location_url, assume GZIP + JSON lines.

    Restituisce una lista di dict, uno per riga.
    """

    resp = requests.get(location_url)
    resp.raise_for_status()

    content = resp.content

    # Decompressione GZIP
    with gzip.GzipFile(fileobj=BytesIO(content)) as gz:
        raw = gz.read().decode("utf-8")

    rows = []
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        rows.append(json.loads(line))
    return rows


def get_sp_targeting_metrics(
    access_token: str,
    profile_id: str,
    campaign_ids,
    timeframe_days: int,
) -> dict:
    """
    Wrapper alto livello:
    - calcola start/end date in base al timeframe richiesto
    - crea il report SP Targeting
    - attende la generazione
    - scarica e parsifica il GZIP JSON
    - restituisce un dict {targetId: metriche}

    Returns:
        {
          targetId (int o string): {
              "impressions": int,
              "clicks": int,
              "cost": float,
              "orders": int,
              "sales": float,
              "acos": float o None,
          },
          ...
        }
    """

    # Per sicurezza usiamo dati fino a ieri, non includiamo oggi (ritardi attribution)
    end = date.today() - timedelta(days=1)
    start = end - timedelta(days=timeframe_days - 1)

    report_id = create_sp_targeting_report(
        access_token=access_token,
        profile_id=profile_id,
        start_date=start,
        end_date=end,
        campaign_ids=campaign_ids,
    )

    meta = wait_for_report(access_token, profile_id, report_id)
    location = meta.get("location")
    if not location:
        raise RuntimeError(f"Nessuna 'location' nel meta report: {meta}")

    rows = download_report_gzip_json(location)

    metrics_by_target = {}

    for row in rows:
        tid = row.get("targetId")
        if tid is None:
            continue

        impressions = int(row.get("impressions", 0) or 0)
        clicks = int(row.get("clicks", 0) or 0)
        cost = float(row.get("cost", 0.0) or 0.0)

        # Nomina ordini tipica: purchases14d (v3) oppure attributedConversions14d (v2)
        orders = (
            row.get("purchases14d")
            or row.get("attributedConversions14d")
            or 0
        )
        orders = int(orders or 0)

        # Nomina vendite tipica: sales14d (v3) oppure attributedSales14d (v2)
        sales = (
            row.get("sales14d")
            or row.get("attributedSales14d")
            or 0.0
        )
        sales = float(sales or 0.0)

        acos = None
        if sales > 0 and cost > 0:
            acos = (cost / sales) * 100.0

        metrics_by_target[str(tid)] = {
            "impressions": impressions,
            "clicks": clicks,
            "cost": cost,
            "orders": orders,
            "sales": sales,
            "acos": acos,
        }

    return metrics_by_target
