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


def _station_label(sta: Station) -> str:
    return f"{sta.station_name} (UIC: {sta.uic_code})"


st.set_page_config(page_title="Travel Order Resolver", page_icon="🚄", layout="wide")

st.title("🚄 Travel Order Resolver — Helpful + Itinerary")
st.caption("NLP Départ/Arrivée + désambiguïsation gares + itinéraire multi-étapes + carte")

left, right = st.columns([2, 1], gap="large")

with right:
    st.subheader("Mode")
    helpful_mode = st.toggle("Helpful mode (proposer des choix au lieu de INVALID)", value=True)
    show_debug = st.toggle("Afficher le debug", value=True)

    st.subheader("Étapes (optionnel)")
    st.caption("Ajoute des gares intermédiaires manuellement (UI différente des autres).")
    via_text = st.text_input("Via (séparées par des virgules)", value="", placeholder="Ex: Dijon, Lyon Part-Dieu")

with left:
    sentence = st.text_input(
        "Phrase utilisateur",
        value="Je veux aller de Paris à Lyon",
        placeholder="Ex: Je voudrais partir de Bordeaux vers Marseille",
    )
    mode = st.radio("Résolveur", ["baseline", "spacy"], horizontal=True)

    if st.button("Résoudre", type="primary"):
        res = resolve_sentence(sentence, mode=mode, helpful=helpful_mode)

        # ----------------------------
        # Case A: NLP success
        # ----------------------------
        if res.ok:
            st.success("Extraction réussie ✅")

            c1, c2, c3 = st.columns(3)
            c1.metric("Ville départ", res.departure or "—")
            c2.metric("Ville arrivée", res.arrival or "—")
            c3.metric("Confiance", f"{res.confidence * 100:.1f}%")

            st.divider()
            st.subheader("Choix des gares")

            dep_candidates = res.departure_candidates or []
            arr_candidates = res.arrival_candidates or []

            # Departure station
            dep_choice = None
            if len(dep_candidates) == 0:
                st.warning("Aucune gare trouvée pour le départ (dataset).")
            elif len(dep_candidates) == 1:
                dep_choice = dep_candidates[0]
                st.info(f"Départ: {dep_choice.station_name}")
            else:
                dep_choice = st.selectbox("Gare de départ", dep_candidates, format_func=_station_label, index=0)

            # Arrival station
            arr_choice = None
            if len(arr_candidates) == 0:
                st.warning("Aucune gare trouvée pour l’arrivée (dataset).")
            elif len(arr_candidates) == 1:
                arr_choice = arr_candidates[0]
                st.info(f"Arrivée: {arr_choice.station_name}")
            else:
                arr_choice = st.selectbox("Gare d’arrivée", arr_candidates, format_func=_station_label, index=0)

            # Parse "via" as free text 
            via_list: list[Station] = []
            if via_text.strip():
                from api.stations import load_stations, station_candidates_from_free_text

                stations_df = load_stations(PROJECT_ROOT / "data" / "sncf_clean" / "stations_clean.csv")
                for chunk in [c.strip() for c in via_text.split(",") if c.strip()]:
                    cands = station_candidates_from_free_text(stations_df, chunk, limit=5)
                    if cands:
                        via_list.append(cands[0])

            if dep_choice and arr_choice:
                st.divider()
                st.subheader("Itinéraire (sequence de points)")

                steps = build_itinerary(dep_choice, arr_choice, via=via_list)

                # Display steps as a table
                rows = []
                for i, step in enumerate(steps):
                    rows.append(
                        {
                            "#": i,
                            "Type": step.label,
                            "Gare": step.station.station_name,
                            "UIC": step.station.uic_code,
                            "Distance depuis précédent (km)": round(step.distance_km_from_prev, 1),
                        }
                    )
                st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

                # Map
                st.subheader("Carte (aperçu)")
                pts = [{"name": r["Type"], "latitude": step.station.latitude, "longitude": step.station.longitude} for step, r in zip(steps, rows)]
                st.map(pd.DataFrame(pts))

            if show_debug:
                st.subheader("Debug")
                st.json(res.debug or {})

        # ----------------------------
        # Case B: NLP failed
        # ----------------------------
        else:
            if res.followup_question:
                st.warning(res.followup_question)

                cands = res.proposed_candidates or []
                if not cands:
                    st.info("Aucune suggestion trouvée. Essayez de préciser la phrase.")
                    if show_debug:
                        st.json(res.debug or {})
                    st.stop()

                # Two pickers: user selects departure and arrival station directly
                st.subheader("Sélection manuelle (fallback)")
                dep_pick = st.selectbox("Départ (gare)", cands, format_func=_station_label, index=0)
                arr_pick = st.selectbox("Arrivée (gare)", cands, format_func=_station_label, index=min(1, len(cands) - 1))

                if st.button("Construire itinéraire avec ces choix"):
                    steps = build_itinerary(dep_pick, arr_pick, via=[])

                    rows = []
                    for i, step in enumerate(steps):
                        rows.append(
                            {
                                "#": i,
                                "Type": step.label,
                                "Gare": step.station.station_name,
                                "UIC": step.station.uic_code,
                                "Distance depuis précédent (km)": round(step.distance_km_from_prev, 1),
                            }
                        )
                    st.success("Itinéraire construit ✅")
                    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

                    st.subheader("Carte (aperçu)")
                    pts = [{"name": r["Type"], "latitude": step.station.latitude, "longitude": step.station.longitude} for step, r in zip(steps, rows)]
                    st.map(pd.DataFrame(pts))

            else:
                st.error("Demande invalide ou ambiguë ❌")

            if show_debug:
                st.subheader("Debug")
                st.json(res.debug or {})
