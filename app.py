import streamlit as st
import pandas as pd

from auth import (
    build_login_url,
    exchange_code_for_tokens,
    ensure_access_token,
    get_profiles,
    select_profile
)

from amazon_api.campaigns import get_sp_campaigns
from amazon_api.targets import get_targets_for_campaign
from amazon_api.update_bids import update_target_bids


# ==========================================================
# CONFIGURAZIONE DASHBOARD
# ==========================================================

st.set_page_config(page_title="AgentSP MVP", layout="wide")
st.sidebar.title("AgentSP ADS Manager MVP")

menu = st.sidebar.radio(
    "Navigazione",
    [
        "Login Amazon",
        "Profili",
        "Campagne",
        "Keyword",
        "Modifica Bid",
    ],
)

FLAG_MAP = {
    "US": "🇺🇸",
    "IT": "🇮🇹",
    "ES": "🇪🇸",
    "FR": "🇫🇷",
    "DE": "🇩🇪",
    "UK": "🇬🇧",
    "GB": "🇬🇧",
}
CURRENCY_MAP = {
    "USD": "$",
    "EUR": "€",
    "GBP": "£",
}


# ==========================================================
# 1) LOGIN AMAZON (OAuth diretto in Streamlit)
# ==========================================================

def render_login_page():
    st.title("Login Amazon Ads API")

    params = st.query_params

    # Se Amazon rimanda con “?code=XXXX”
    if "code" in params:
        code = params["code"]
        st.info("Codice ricevuto da Amazon. Genero i token...")

        try:
            tokens = exchange_code_for_tokens(code)
            st.success("Login completato!")
            st.json(tokens)
            st.session_state["access_token"] = tokens["access_token"]
            return
        except Exception as e:
            st.error(f"Errore durante il login: {e}")

    # Prova a usare token già in memoria
    try:
        token = ensure_access_token()
        st.success("Token valido già presente.")
        st.code(token)
    except:
        st.warning("Non sei autenticato.")

    st.markdown("---")

    login_url = build_login_url()
    st.markdown(f"[**Clicca qui per accedere con Amazon Ads**]({login_url})", unsafe_allow_html=True)


# ==========================================================
# 2) PROFILI AMAZON
# ==========================================================

def render_profile_page():
    st.title("Profili Amazon Ads")

    try:
        access_token = ensure_access_token()
    except:
        st.warning("Effettua prima il login nella pagina 'Login Amazon'.")
        return

    try:
        profiles = get_profiles(access_token)
    except Exception as e:
        st.error(f"Errore nel recupero dei profili: {e}")
        return

    if not profiles:
        st.warning("Nessun profilo trovato.")
        return

    st.subheader("Profili disponibili")

    cols = st.columns(len(profiles))

    for idx, prof in enumerate(profiles):
        with cols[idx]:

            country = prof.get("countryCode") or prof.get("marketplaceString") or "NA"
            currency = prof.get("currencyCode") or "NA"

            flag = FLAG_MAP.get(country, "🌍")
            cur_symbol = CURRENCY_MAP.get(currency, currency)

            st.markdown(
                f"""
                <div style="border-radius: 12px; padding: 12px; background-color: #f5f5f5; text-align: center;">
                    <div style="font-size: 32px;">{flag}</div>
                    <div style="font-weight: 600; margin-top: 4px;">Profilo {country}</div>
                    <div style="font-size: 12px; color: #666;">
                        {country} • {cur_symbol}
                    </div>
                    <div style="font-size: 10px; color: #999; margin-top: 4px;">
                        profileId: {prof.get("profileId")}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            button_key = f"select_profile_{prof.get('profileId')}"

            if st.button(
                "Seleziona questo profilo",
                key=button_key,
                use_container_width=True,
            ):
                st.session_state["profile"] = prof
                st.success("Profilo attivato.")

    st.markdown("---")

    if "profile" in st.session_state:
        prof = st.session_state["profile"]

        country = prof.get("countryCode") or prof.get("marketplaceString")
        currency = prof.get("currencyCode")
        flag = FLAG_MAP.get(country, "🌍")
        cur_symbol = CURRENCY_MAP.get(currency, currency)

        st.subheader("Profilo attivo")
        st.markdown(
            f"""
            <div style="border-radius: 12px; padding: 12px; background-color: #eef6ff; text-align: center;">
                <div style="font-size: 32px;">{flag}</div>
                <div style="font-weight: 600; margin-top: 4px;">Profilo {country}</div>
                <div style="font-size: 12px; color: #666;">
                    {country} • {cur_symbol}
                </div>
                <div style="font-size: 10px; color: #999; margin-top: 4px;">
                    profileId: {prof.get("profileId")}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.info("Nessun profilo attivo.")


# ==========================================================
# 3) CAMPAGNE
# ==========================================================

def build_campaign_dataframe(campaigns: list[dict]) -> pd.DataFrame:
    rows = []
    for c in campaigns:
        asin = (
            c.get("asin")
            or (c.get("tags", {}) or {}).get("ASIN")
            or (c.get("attributes", {}) or {}).get("asin")
        )
        rows.append(
            {
                "Campaign ID": c.get("campaignId"),
                "Nome campagna": c.get("name"),
                "ASIN": asin,
            }
        )
    return pd.DataFrame(rows)


def render_campaign_page():
    st.title("Campagne Sponsored Products")

    if "profile" not in st.session_state:
        st.warning("Seleziona prima un profilo.")
        return

    try:
        access_token = ensure_access_token()
    except:
        st.warning("Non autenticato.")
        return

    profile_id = st.session_state["profile"]["profileId"]

    try:
        campaigns = get_sp_campaigns(access_token, profile_id)
    except Exception as e:
        st.error(f"Errore recupero campagne: {e}")
        return

    if not campaigns:
        st.warning("Nessuna campagna trovata.")
        return

    st.session_state["campaigns"] = campaigns

    df = build_campaign_dataframe(campaigns)

    st.subheader("Elenco campagne")
    st.dataframe(df, use_container_width=True)

    st.subheader("Seleziona campagne")

    labels = [
        f"{row['Campaign ID']} – {row['Nome campagna']} ({row['ASIN'] or 'no ASIN'})"
        for _, row in df.iterrows()
    ]

    ids = df["Campaign ID"].tolist()

    selected = st.multiselect(
        "Campagne da includere",
        options=labels,
        default=labels,
    )

    selected_ids = [ids[labels.index(lbl)] for lbl in selected]
    st.session_state["selected_campaigns"] = selected_ids

    if selected_ids:
        st.info(f"Campagne selezionate: {', '.join(str(i) for i in selected_ids)}")
    else:
        st.warning("Nessuna campagna selezionata.")


# ==========================================================
# 4) KEYWORD / TARGETS
# ==========================================================

def build_targets_dataframe(all_targets: list[dict]) -> pd.DataFrame:
    rows = []
    for t in all_targets:

        td = t.get("targetDetails", {}) or {}

        # Keyword target
        kw_data = td.get("keywordTarget") or {}
        kws = kw_data.get("keyword")
        match_type = kw_data.get("matchType")

        # Bid
        bid_obj = t.get("bid") or {}
        bid = bid_obj.get("bid")

        impressions = t.get("impressions")
        clicks = t.get("clicks")
        cost = t.get("cost")

        cpc = None
        if clicks and cost and clicks > 0:
            cpc = cost / clicks

        orders = (
            t.get("orders")
            or t.get("purchases")
            or t.get("attributedConversions14d")
        )

        acos = t.get("acos")

        rows.append(
            {
                "CAMPAIGN_ID": t.get("campaignId"),
                "TARGET_ID": t.get("targetId"),
                "TARGET": kws,
                "MATCH_TYPE": match_type,
                "BID": bid,
                "IMPRESSIONS": impressions,
                "CLICKS": clicks,
                "CPC": cpc,
                "ORDINI": orders,
                "ACOS": acos,
            }
        )

    return pd.DataFrame(rows)


def render_keyword_page():
    st.title("Keyword / Targets delle campagne selezionate")

    if "profile" not in st.session_state:
        st.warning("Seleziona prima un profilo.")
        return

    if "selected_campaigns" not in st.session_state:
        st.warning("Seleziona almeno una campagna.")
        return

    try:
        access_token = ensure_access_token()
    except:
        st.warning("Non autenticato.")
        return

    profile_id = st.session_state["profile"]["profileId"]
    selected_campaigns = st.session_state["selected_campaigns"]

    all_targets = []
    for cid in selected_campaigns:
        try:
            t = get_targets_for_campaign(access_token, profile_id, cid)
            all_targets.extend(t)
        except Exception as e:
            st.error(f"Errore campagna {cid}: {e}")

    if not all_targets:
        st.warning("Nessun target trovato.")
        return

    st.session_state["targets"] = all_targets
    st.success(f"Trovati {len(all_targets)} targets totali.")

    df = build_targets_dataframe(all_targets)

    st.dataframe(df, use_container_width=True)


# ==========================================================
# 5) MODIFICA BID
# ==========================================================

def render_bid_page():
    st.title("Modifica manuale Bid")

    if "targets" not in st.session_state:
        st.warning("Prima carica i targets.")
        return

    access_token = ensure_access_token()
    profile_id = st.session_state["profile"]["profileId"]
    targets = st.session_state["targets"]

    action = st.radio("Azione", ["Aumenta", "Diminuisci"])
    cent = st.number_input("Centesimi (5 = 0.05)", min_value=1, max_value=300, value=5)

    delta = cent / 100
    if action == "Diminuisci":
        delta = -delta

    st.write(f"Delta applicato: {delta} USD")

    if st.button("Applica"):
        try:
            result = update_target_bids(access_token, profile_id, targets, delta)
            st.success("Bid aggiornati.")
            st.json(result)
        except Exception as e:
            st.error(f"Errore update bid: {e}")


# ==========================================================
# ROUTING
# ==========================================================

if menu == "Login Amazon":
    render_login_page()
elif menu == "Profili":
    render_profile_page()
elif menu == "Campagne":
    render_campaign_page()
elif menu == "Keyword":
    render_keyword_page()
elif menu == "Modifica Bid":
    render_bid_page()
