from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st
import pandas as pd

from api.resolver_service import resolve_sentence
from api.stations import Station
from api.pathfinder import build_itinerary


def station_label(sta: Station) -> str:
    return f"{sta.station_name} (UIC: {sta.uic_code})"


# ------------------------------------------------------------
# Page config
# ------------------------------------------------------------
st.set_page_config(
    page_title="Travel Order Resolver",
    page_icon="🚄",
    layout="wide",
)

st.title("🚄 Travel Order Resolver")
st.caption(
    "Résolution d’ordres de voyage en français · NLP + données SNCF · projet universitaire"
)

# ------------------------------------------------------------
# Sidebar (global controls)
# ------------------------------------------------------------
with st.sidebar:
    st.header("⚙️ Paramètres")

    mode = st.radio(
        "Résolveur NLP",
        ["baseline", "spacy"],
        help="Baseline = règles + fuzzy · spaCy = NER (EntityRuler)",
    )

    helpful_mode = st.toggle(
        "Helpful mode",
        value=True,
        help="Proposer des choix interactifs au lieu de retourner INVALID",
    )

    show_debug = st.toggle(
        "Afficher debug détaillé",
        value=False,
    )

    st.divider()
    st.markdown(
        """
**Logique de l’interface**
1. Compréhension NLP  
2. Désambiguïsation des gares  
3. Itinéraire + carte  
"""
    )

# ------------------------------------------------------------
# Main input
# ------------------------------------------------------------
sentence = st.text_input(
    "📝 Phrase utilisateur",
    value="Je voudrais aller de Paris à Lyon demain",
    placeholder="Ex: Je veux aller de Lille à Nice",
)

if st.button("🔍 Résoudre la demande", type="primary"):
    res = resolve_sentence(sentence, mode=mode, helpful=helpful_mode)

    # ============================================================
    # STEP 1 — NLP 
    # ============================================================
    st.subheader("① Compréhension NLP")

    if not res.ok and not res.followup_question:
        st.error("❌ La demande n’a pas pu être comprise.")
        if show_debug:
            st.json(res.debug or {})
        st.stop()

    if res.ok:
        col1, col2, col3 = st.columns(3)
        col1.metric("Ville départ", res.departure)
        col2.metric("Ville arrivée", res.arrival)
        col3.metric("Confiance", f"{res.confidence * 100:.1f}%")

        with st.expander("🧠 Détails de raisonnement (timeline NLP)", expanded=True):
            st.markdown(
                f"""
- **Résolveur utilisé** : `{res.debug.get('resolver')}`
- **Force NLP** : `{res.debug.get('confidence_strength')}`
- **Présence littérale départ** : `{res.debug.get('departure_literal_in_sentence')}`
- **Présence littérale arrivée** : `{res.debug.get('arrival_literal_in_sentence')}`
- **Nb gares départ candidates** : `{res.debug.get('departure_candidates_count')}`
- **Nb gares arrivée candidates** : `{res.debug.get('arrival_candidates_count')}`
- **Pénalité ambiguïté** : `{res.debug.get('ambiguity_penalty')}`
- **Pénalité contamination** : `{res.debug.get('contamination_penalty')}`
"""
            )

    else:
        st.warning(res.followup_question)
        st.subheader("Sélection manuelle (fallback NLP)")

        cands = res.proposed_candidates or []
        if not cands:
            st.info("Aucune suggestion trouvée.")
            if show_debug:
                st.json(res.debug or {})
            st.stop()

        dep_choice = st.selectbox("Gare de départ", cands, format_func=station_label)
        arr_choice = st.selectbox("Gare d’arrivée", cands, format_func=station_label)

        steps = build_itinerary(dep_choice, arr_choice)
        st.success("Itinéraire construit à partir de la sélection manuelle.")

        df = pd.DataFrame(
            [
                {
                    "Étape": step.label,
                    "Gare": step.station.station_name,
                    "Distance depuis précédent (km)": round(step.distance_km_from_prev, 1),
                }
                for step in steps
            ]
        )
        st.dataframe(df, use_container_width=True, hide_index=True)

        st.map(
            pd.DataFrame(
                [
                    {
                        "latitude": step.station.latitude,
                        "longitude": step.station.longitude,
                    }
                    for step in steps
                ]
            )
        )

        if show_debug:
            st.json(res.debug or {})
        st.stop()

    # ============================================================
    # STEP 2 — Station disambiguation
    # ============================================================
    st.subheader("② Désambiguïsation des gares SNCF")

    dep_candidates = res.departure_candidates or []
    arr_candidates = res.arrival_candidates or []

    col_dep, col_arr = st.columns(2)

    with col_dep:
        st.markdown("**Gare de départ**")
        if len(dep_candidates) == 1:
            dep_choice = dep_candidates[0]
            st.success(dep_choice.station_name)
        else:
            dep_choice = st.selectbox(
                "Choisissez la gare de départ",
                dep_candidates,
                format_func=station_label,
            )

    with col_arr:
        st.markdown("**Gare d’arrivée**")
        if len(arr_candidates) == 1:
            arr_choice = arr_candidates[0]
            st.success(arr_choice.station_name)
        else:
            arr_choice = st.selectbox(
                "Choisissez la gare d’arrivée",
                arr_candidates,
                format_func=station_label,
            )

    # ============================================================
    # STEP 3 — Itinerary + map
    # ============================================================
    st.subheader("③ Itinéraire et visualisation")

    steps = build_itinerary(dep_choice, arr_choice)

    df_steps = pd.DataFrame(
        [
            {
                "#": i,
                "Type": step.label,
                "Gare": step.station.station_name,
                "Distance depuis précédent (km)": round(step.distance_km_from_prev, 1),
            }
            for i, step in enumerate(steps)
        ]
    )

    st.dataframe(df_steps, use_container_width=True, hide_index=True)

    st.map(
        pd.DataFrame(
            [
                {
                    "latitude": step.station.latitude,
                    "longitude": step.station.longitude,
                }
                for step in steps
            ]
        )
    )

    if show_debug:
        st.subheader("🔎 Debug brut")
        st.json(res.debug or {})
