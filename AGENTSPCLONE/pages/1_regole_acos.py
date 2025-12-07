import streamlit as st

from db.database import (
    init_db,
    get_all_rules,
    create_rule,
    delete_rule,
    set_rule_enabled,
)

# Inizializza DB (idempotente)
init_db()

st.set_page_config(page_title="Automazione", layout="wide")
st.title("Automazione")


TIMEFRAME_OPTIONS = {
    "14 giorni": 14,
    "30 giorni": 30,
    "60 giorni": 60,
    "90 giorni": 90,
    "Lifetime": -1,
}

FREQUENCY_OPTIONS = [3, 5, 7, 10, 15]

MATCH_TYPES = ["Tutti", "exact", "phrase", "broad"]


def format_rule_type(rt: str) -> str:
    if rt == "ACOS_BAND":
        return "ACOS band"
    if rt == "LOW_TRAFFIC":
        return "Low traffic"
    return rt


def format_conditions(r: dict) -> str:
    if r["rule_type"] == "ACOS_BAND":
        amin = r.get("acos_min")
        amax = r.get("acos_max")
        if amin is None and amax is None:
            return "-"
        if amin is not None and amax is not None:
            return f"{amin:.1f} - {amax:.1f} % ACOS"
        if amin is not None:
            return f"ACOS >= {amin:.1f} %"
        if amax is not None:
            return f"ACOS <= {amax:.1f} %"
        return "-"
    if r["rule_type"] == "LOW_TRAFFIC":
        cmax = r.get("clicks_max")
        if cmax is not None:
            return f"Click < {int(cmax)}"
        return "-"
    return "-"


def do_rerun():
    if hasattr(st, "rerun"):
        st.rerun()
    elif hasattr(st, "experimental_rerun"):
        st.experimental_rerun()


def ui_toggle(label: str, value: bool, key: str) -> bool:
    if hasattr(st, "toggle"):
        return st.toggle(label, value=value, key=key)
    return st.checkbox(label, value=value, key=key)


st.subheader("Crea nuova regola")

# Selezione tipo regola fuori dalla form per permettere il rerender immediato dei campi condizione
rule_type = st.selectbox(
    "Tipo regola",
    options=["ACOS_BAND", "LOW_TRAFFIC"],
    format_func=format_rule_type,
    key="rule_type_select",
)

with st.form("create_rule_form"):
    col1, col2, col3 = st.columns(3)

    with col1:
        name = st.text_input("Nome regola", value="Regola ACOS")
        # Mostro solo il tipo selezionato, la scelta vera e propria è sopra la form
        st.markdown(f"**Tipo regola selezionato:** {format_rule_type(rule_type)}")
        marketplace = st.text_input("Marketplace (es. US, IT, DE)", value="US")

    with col2:
        timeframe_label = st.selectbox(
            "Timeframe",
            options=list(TIMEFRAME_OPTIONS.keys()),
            index=0,
        )
        timeframe_days = TIMEFRAME_OPTIONS[timeframe_label]

        frequency_days = st.selectbox(
            "Frequenza esecuzione (giorni)",
            options=FREQUENCY_OPTIONS,
            index=0,
        )

        match_type_label = st.selectbox(
            "Match type",
            options=MATCH_TYPES,
            index=0,
        )

    with col3:
        adjustment_type = st.selectbox(
            "Tipo di aggiustamento",
            options=["ABS", "PCT"],
            format_func=lambda x: "Valore assoluto" if x == "ABS" else "Percentuale",
        )
        adjustment_value = st.number_input(
            "Valore aggiustamento",
            value=0.05,
            step=0.01,
            format="%.2f",
        )

        enabled = st.checkbox("Regola attiva", value=True)

    st.markdown("### Condizioni logiche")

    colc1, _ = st.columns(2)

    acos_min = None
    acos_max = None
    clicks_min = None
    clicks_max = None

    with colc1:
        if rule_type == "ACOS_BAND":
            acos_min = st.number_input(
                "ACOS minimo (%)",
                value=0.0,
                step=0.5,
                format="%.2f",
            )
            acos_max = st.number_input(
                "ACOS massimo (%)",
                value=20.0,
                step=0.5,
                format="%.2f",
            )
            clicks_min = None
            clicks_max = None

        elif rule_type == "LOW_TRAFFIC":
            clicks_threshold = st.number_input(
                "Click inferiori a",
                value=10,
                step=1,
                min_value=1,
            )
            clicks_min = 0
            clicks_max = clicks_threshold
            acos_min = None
            acos_max = None

    submit = st.form_submit_button("Crea regola")

    if submit:
        match_type = None if match_type_label == "Tutti" else match_type_label

        data = {
            "name": name,
            "rule_type": rule_type,
            "campaign_id": None,
            "marketplace": marketplace or None,
            "match_type": match_type,
            "acos_min": acos_min,
            "acos_max": acos_max,
            "clicks_min": clicks_min,
            "clicks_max": clicks_max,
            "adjustment_type": adjustment_type,
            "adjustment_value": float(adjustment_value),
            "timeframe_days": timeframe_days,
            "frequency_days": int(frequency_days),
            "enabled": 1 if enabled else 0,
        }

        rule_id = create_rule(data)
        st.success(f"Regola creata con ID: {rule_id}")
        do_rerun()

st.markdown("---")

st.subheader("Regole esistenti")

rules = get_all_rules()

if not rules:
    st.info("Non ci sono ancora regole configurate.")
else:
    header_cols = st.columns([1, 3, 2, 3, 2, 2, 2, 2, 2, 2])
    header_cols[0].markdown("**ID**")
    header_cols[1].markdown("**Nome**")
    header_cols[2].markdown("**Tipo**")
    header_cols[3].markdown("**Condizioni**")
    header_cols[4].markdown("**Marketplace**")
    header_cols[5].markdown("**Delta**")
    header_cols[6].markdown("**Timeframe**")
    header_cols[7].markdown("**Frequenza**")
    header_cols[8].markdown("**Stato**")
    header_cols[9].markdown("**Azioni**")

    for r in rules:
        cols = st.columns([1, 3, 2, 3, 2, 2, 2, 2, 2, 2])

        rule_id = r["id"]
        enabled_flag = bool(r["enabled"])

        delta_str = (
            f"{r['adjustment_value']:+.2f}"
            + (" (ABS)" if r["adjustment_type"] == "ABS" else " (%)")
        )

        timeframe_str = next(
            (label for label, val in TIMEFRAME_OPTIONS.items() if val == r["timeframe_days"]),
            str(r["timeframe_days"]),
        )

        cond_str = format_conditions(r)

        with cols[0]:
            st.write(rule_id)
        with cols[1]:
            st.write(r["name"])
        with cols[2]:
            st.write(format_rule_type(r["rule_type"]))
        with cols[3]:
            st.write(cond_str)
        with cols[4]:
            st.write(r.get("marketplace") or "-")
        with cols[5]:
            st.write(delta_str)
        with cols[6]:
            st.write(timeframe_str)
        with cols[7]:
            st.write(f"{r['frequency_days']}g")
        with cols[8]:
            st.write("Attiva")
            new_enabled = ui_toggle(
                "",
                value=enabled_flag,
                key=f"enabled_{rule_id}",
            )
            if new_enabled != enabled_flag:
                set_rule_enabled(rule_id, new_enabled)
                do_rerun()
        with cols[9]:
            if st.button("Elimina", key=f"delete_{rule_id}"):
                delete_rule(rule_id)
                do_rerun()
