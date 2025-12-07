import streamlit as st
import pandas as pd

from auth import ensure_access_token, get_profiles, select_us_profile
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
        "Token Amazon",
        "Profili",
        "Campagne",
        "Keyword",
        "Modifica Bid",
    ],
)

# Mappa bandiere e valute (usata in più sezioni)
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
# 1) GESTIONE TOKEN AMAZON (USA tokens.json)
# ==========================================================

def render_token_page() -> None:
    st.title("Token Amazon Ads")

    st.write(
        """
Questa schermata usa i token salvati in `tokens.json`.

Se è la prima volta che usi l'app:

1. Chiudi la dashboard.
2. Esegui da terminale `python main.py`.
3. Completa il login Amazon seguendo le istruzioni nel terminale.
4. Torna qui e premi il pulsante per caricare o fare refresh del token.
        """
    )

    if st.button("Carica o refresh token da tokens.json"):
        try:
            access_token = ensure_access_token()
            st.session_state["access_token"] = access_token
            st.success("Access token disponibile.")
            st.code(access_token)
        except Exception as e:
            st.error(f"Errore nel recupero del token: {e}")
            st.info(
                "Se non hai ancora autorizzato l'app, esegui `python main.py` da terminale."
            )


# ==========================================================
# 2) PROFILI AMAZON
# ==========================================================

def render_profile_page() -> None:
    st.title("Profili Amazon Ads")

    if "access_token" not in st.session_state:
        st.warning("Prima carica il token nella sezione 'Token Amazon'.")
        return

    access_token = st.session_state["access_token"]

    try:
        profiles = get_profiles(access_token)
    except Exception as e:
        st.error(f"Errore nel recupero dei profili: {e}")
        return

    if not profiles:
        st.warning("Nessun profilo trovato per questo account.")
        return

    st.subheader("Profili disponibili")

    cols = st.columns(len(profiles))

    for idx, prof in enumerate(profiles):
        with cols[idx]:
            country = (
                prof.get("countryCode")
                or prof.get("marketplaceString")
                or "NA"
            )
            currency = prof.get("currencyCode") or "NA"

            flag = FLAG_MAP.get(country, "🌍")
            cur_symbol = CURRENCY_MAP.get(currency, currency)

            # Card riassuntiva profilo
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

            # Solo profili US cliccabili
            is_us = country == "US" or currency == "USD"
            button_key = f"select_profile_{prof.get('profileId')}"

            if is_us:
                if st.button(
                    "Seleziona US",
                    key=button_key,
                    use_container_width=True,
                ):
                    try:
                        selected = select_us_profile(profiles)
                        st.session_state["profile"] = selected
                        st.success("Profilo US selezionato.")
                    except Exception as e:
                        st.error(f"Errore nella selezione del profilo US: {e}")
            else:
                st.button(
                    "Non disponibile",
                    key=button_key,
                    disabled=True,
                    use_container_width=True,
                )

    st.markdown("---")

    # PROFILO ATTIVO (card pulita con bandiera)
    if "profile" in st.session_state:
        st.subheader("Profilo attivo")

        prof = st.session_state["profile"]
        country = (
            prof.get("countryCode")
            or prof.get("marketplaceString")
            or "NA"
        )
        currency = prof.get("currencyCode") or "NA"

        flag = FLAG_MAP.get(country, "🌍")
        cur_symbol = CURRENCY_MAP.get(currency, currency)

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
        st.info("Nessun profilo attivo. Seleziona un profilo US.")


# ==========================================================
# 3) CAMPAGNE
# ==========================================================

def build_campaign_dataframe(campaigns: list[dict]) -> pd.DataFrame:
    rows = []
    for c in campaigns:
        campaign_id = c.get("campaignId")
        name = c.get("name")
        asin = (
            c.get("asin")
            or (c.get("tags", {}) or {}).get("ASIN")
            or (c.get("attributes", {}) or {}).get("asin")
        )
        rows.append(
            {
                "Campaign ID": campaign_id,
                "Nome campagna": name,
                "ASIN": asin,
            }
        )
    return pd.DataFrame(rows)


def render_campaign_page() -> None:
    st.title("Campagne Sponsored Products")

    if "profile" not in st.session_state or "access_token" not in st.session_state:
        st.warning("Assicurati di aver caricato il token e selezionato un profilo.")
        return

    access_token = st.session_state["access_token"]
    profile_id = st.session_state["profile"]["profileId"]

    try:
        campaigns = get_sp_campaigns(access_token, profile_id)
    except Exception as e:
        st.error(f"Errore nel recupero delle campagne: {e}")
        return

    if not campaigns:
        st.warning("Nessuna campagna trovata.")
        return

    st.session_state["campaigns"] = campaigns

    df = build_campaign_dataframe(campaigns)

    st.subheader("Elenco campagne")

    # Filtri a menu a tendina con ricerca
    unique_names = ["Tutte"] + sorted(
        df["Nome campagna"].dropna().astype(str).unique().tolist()
    )
    unique_asin = ["Tutti"] + sorted(
        [
            a
            for a in df["ASIN"].dropna().astype(str).unique().tolist()
            if a != "None"
        ]
    )

    col_f1, col_f2 = st.columns([2, 1])
    with col_f1:
        filtro_nome = st.selectbox(
            "Filtra per nome campagna",
            options=unique_names,
            index=0,
        )
    with col_f2:
        filtro_asin = st.selectbox(
            "Filtra per ASIN",
            options=unique_asin,
            index=0,
        )

    filtered_df = df.copy()
    if filtro_nome != "Tutte":
        filtered_df = filtered_df[
            filtered_df["Nome campagna"] == filtro_nome
        ]
    if filtro_asin != "Tutti":
        filtered_df = filtered_df[
            filtered_df["ASIN"].astype(str) == filtro_asin
        ]

    st.dataframe(filtered_df, use_container_width=True)

    st.markdown("---")
    st.subheader("Seleziona campagne")

    if filtered_df.empty:
        st.warning("Nessuna campagna corrisponde ai filtri.")
        return

    labels = [
        f"{row['Campaign ID']} – {row['Nome campagna']} ({row['ASIN'] or 'no ASIN'})"
        for _, row in filtered_df.iterrows()
    ]
    campaign_ids = filtered_df["Campaign ID"].tolist()

    # Pre selezione delle campagne già salvate (se presenti)
    default_selection: list[str] = []
    if "selected_campaigns" in st.session_state:
        for cid in st.session_state["selected_campaigns"]:
            if cid in campaign_ids:
                default_selection.append(
                    labels[campaign_ids.index(cid)]
                )

    selected_labels = st.multiselect(
        "Campagne da includere",
        options=labels,
        default=default_selection or labels,  # di default tutte
    )

    selected_ids = [
        campaign_ids[labels.index(lbl)] for lbl in selected_labels
    ]

    st.session_state["selected_campaigns"] = selected_ids

    # Compatibilità con vecchia logica (singola campagna)
    if selected_ids:
        st.session_state["selected_campaign"] = selected_ids[0]

    if selected_ids:
        st.info(
            "Campagne selezionate: "
            + ", ".join(str(cid) for cid in selected_ids)
        )
    else:
        st.warning("Nessuna campagna selezionata.")


# ==========================================================
# 4) KEYWORD / TARGETS DELLE CAMPAGNE SELEZIONATE
# ==========================================================

def build_targets_dataframe(all_targets: list[dict]) -> pd.DataFrame:
    rows = []

    for t in all_targets:
        td = t.get("targetDetails", {}) or {}

        # Keyword target (classico)
        kw_data = td.get("keywordTarget") or {}
        kws = kw_data.get("keyword")
        match_type = kw_data.get("matchType")

        # Altri target (product / auto) best effort
        target_type = t.get("targetType")
        if not kws:
            if "asinCategoryTarget" in td:
                asin_cat = td["asinCategoryTarget"]
                kws = asin_cat.get("categoryName") or asin_cat.get(
                    "asinCategoryId"
                )
            elif "asinBrandTarget" in td:
                asin_brand = td["asinBrandTarget"]
                kws = asin_brand.get("brandName") or asin_brand.get(
                    "brandId"
                )
            elif "productTarget" in td:
                p_t = td["productTarget"]
                kws = p_t.get("asin") or p_t.get("expression")
            elif "autoTarget" in td:
                a_t = td["autoTarget"]
                kws = a_t.get("expression") or a_t.get("type")
                match_type = a_t.get("type")

        # BID numerico
        bid_obj = t.get("bid") or {}
        bid = bid_obj.get("bid")

        impressions = t.get("impressions")
        clicks = t.get("clicks")
        cost = t.get("cost")

        # CPC
        cpc = None
        if clicks and cost is not None and clicks > 0:
            try:
                cpc = cost / clicks
            except Exception:
                cpc = None

        # Ordini (best effort)
        orders = (
            t.get("orders")
            or t.get("purchases")
            or t.get("attributedConversions14d")
            or t.get("attributedConversions7d")
        )
        acos = t.get("acos")

        rows.append(
            {
                "CAMPAIGN_ID": t.get("campaignId"),
                "TARGET_ID": t.get("targetId"),
                "TARGET_TYPE": target_type,
                "KWS / TARGET": kws,
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


def render_keyword_page() -> None:
    st.title("Keyword / Targets delle campagne selezionate")

    if (
        "profile" not in st.session_state
        or "access_token" not in st.session_state
    ):
        st.warning("Seleziona prima profilo e token.")
        return

    # Recupera la lista di campagne selezionate
    selected_campaigns = st.session_state.get("selected_campaigns")
    if not selected_campaigns:
        # Fallback vecchia logica: singola campagna
        single = st.session_state.get("selected_campaign")
        if single:
            selected_campaigns = [single]

    if not selected_campaigns:
        st.warning("Seleziona almeno una campagna nella sezione 'Campagne'.")
        return

    access_token = st.session_state["access_token"]
    profile_id = st.session_state["profile"]["profileId"]

    all_targets: list[dict] = []
    errors: list[str] = []

    for cid in selected_campaigns:
        try:
            t_camp = get_targets_for_campaign(access_token, profile_id, cid)
            all_targets.extend(t_camp)
        except Exception as e:
            errors.append(f"Errore su campagna {cid}: {e}")

    if errors:
        for msg in errors:
            st.error(msg)

    if not all_targets:
        st.warning("Nessun target trovato per le campagne selezionate.")
        return

    st.session_state["targets"] = all_targets
    st.success(f"Trovati {len(all_targets)} target totali.")

    df = build_targets_dataframe(all_targets)

    st.subheader("Tabella keyword / targets")

    page_size = st.selectbox(
        "Righe da visualizzare",
        options=[100, 200, 500, 1000],
        index=0,
    )

    df_view = df.head(page_size)
    st.dataframe(df_view, use_container_width=True)

    with st.expander("Dati raw (debug)"):
        st.json(all_targets)


# ==========================================================
# 5) MODIFICA MANUALE BID
# ==========================================================

def render_bid_page() -> None:
    st.title("Modifica manuale dei bid")

    if (
        "targets" not in st.session_state
        or "profile" not in st.session_state
        or "access_token" not in st.session_state
    ):
        st.warning("Carica prima i target nella sezione 'Keyword'.")
        return

    access_token = st.session_state["access_token"]
    profile_id = st.session_state["profile"]["profileId"]
    targets = st.session_state["targets"]

    st.subheader("Impostazioni modifica bid")

    action = st.radio("Azione", ["Aumenta", "Diminuisci"])
    cent = st.number_input(
        "Centesimi (esempio: 5 significa 0.05)",
        min_value=1,
        max_value=200,
        value=5,
    )

    delta = cent / 100
    if action == "Diminuisci":
        delta = -delta

    st.write(f"Delta applicato per ogni target: {delta:.2f} USD")

    if st.button("Applica modifica ai bid"):
        try:
            result = update_target_bids(access_token, profile_id, targets, delta)
        except Exception as e:
            st.error(f"Errore durante l'update dei bid: {e}")
        else:
            st.success("Bid aggiornati correttamente.")
            st.json(result)


# ==========================================================
# ROUTING PRINCIPALE
# ==========================================================

if menu == "Token Amazon":
    render_token_page()
elif menu == "Profili":
    render_profile_page()
elif menu == "Campagne":
    render_campaign_page()
elif menu == "Keyword":
    render_keyword_page()
elif menu == "Modifica Bid":
    render_bid_page()
