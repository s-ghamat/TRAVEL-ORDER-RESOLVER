from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st
import pandas as pd

from api.resolver_service import resolve_sentence
from api.stations import Station


def _station_label(st: Station) -> str:
    return f"{st.station_name}  (UIC: {st.uic_code})"


st.set_page_config(page_title="Travel Order Resolver", page_icon="🚄", layout="wide")

st.title("🚄 Travel Order Resolver — Station-aware")
st.caption("NLP Départ/Arrivée + désambiguïsation stations SNCF + carte")

col_left, col_right = st.columns([2, 1], gap="large")

with col_left:
    sentence = st.text_input(
        "Phrase utilisateur",
        value="Je voudrais aller de Paris à Lyon demain",
        placeholder="Ex: Je veux aller de Lille à Nice",
    )

    mode = st.radio("Mode de résolution", ["baseline", "spacy"], horizontal=True)
    show_debug = st.toggle("Afficher le debug", value=True)

    if st.button("Résoudre", type="primary"):
        res = resolve_sentence(sentence, mode=mode)

        if not res.ok:
            st.error("Demande invalide ou ambiguë ❌")
            if show_debug:
                st.json(res.debug or {})
            st.stop()

        st.success("Extraction réussie ✅")

        m1, m2, m3 = st.columns(3)
        m1.metric("Ville départ", res.departure or "—")
        m2.metric("Ville arrivée", res.arrival or "—")
        m3.metric("Confiance", f"{res.confidence * 100:.1f}%")

        st.divider()
        st.subheader("Choix des gares (désambiguïsation)")

        # Departure station choice
        dep_candidates = res.departure_candidates or []
        if len(dep_candidates) == 0:
            st.warning("Aucune gare trouvée pour le départ (dataset).")
            dep_choice = None
        elif len(dep_candidates) == 1:
            dep_choice = dep_candidates[0]
            st.info(f"Départ: {dep_choice.station_name}")
        else:
            dep_choice = st.selectbox(
                "Gare de départ",
                options=dep_candidates,
                format_func=_station_label,
                index=0,
            )

        # Arrival station choice
        arr_candidates = res.arrival_candidates or []
        if len(arr_candidates) == 0:
            st.warning("Aucune gare trouvée pour l’arrivée (dataset).")
            arr_choice = None
        elif len(arr_candidates) == 1:
            arr_choice = arr_candidates[0]
            st.info(f"Arrivée: {arr_choice.station_name}")
        else:
            arr_choice = st.selectbox(
                "Gare d’arrivée",
                options=arr_candidates,
                format_func=_station_label,
                index=0,
            )

        st.divider()
        st.subheader("Carte (aperçu)")

        points = []
        if dep_choice is not None:
            points.append({"name": "Départ", "lat": dep_choice.latitude, "lon": dep_choice.longitude})
        if arr_choice is not None:
            points.append({"name": "Arrivée", "lat": arr_choice.latitude, "lon": arr_choice.longitude})

        if points:
            df = pd.DataFrame(points)
            df = df.rename(columns={"lat": "latitude", "lon": "longitude"})
            st.map(df)
        else:
            st.info("Sélectionnez des gares pour afficher la carte.")

        if show_debug:
            st.subheader("Debug")
            st.json(res.debug or {})

with col_right:
    st.subheader("Pourquoi c’est différent")
    st.markdown(
        """
**UI orientée “résolution” :**
- Extraction villes (NLP)
- Puis **choix de gares** (désambiguïsation)
- Puis **carte immédiate**
  
C’est plus “produit” et gère un vrai problème SNCF :  
**une ville ≠ une gare**.
"""
    )
