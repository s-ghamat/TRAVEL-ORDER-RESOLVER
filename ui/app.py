from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st
from api.resolver_service import resolve_sentence


st.set_page_config(
    page_title="Travel Order Resolver",
    page_icon="🚄",
    layout="wide",
)

st.title("🚄 Travel Order Resolver")
st.caption("Extraction automatique Départ / Arrivée à partir d'une phrase en français (projet NLP SNCF)")

col_left, col_right = st.columns([2, 1], gap="large")

with col_left:
    sentence = st.text_input(
        "Phrase utilisateur",
        value="Je voudrais aller de Paris à Lyon demain",
        placeholder="Ex: Je veux aller de Lille à Nice",
    )

    mode = st.radio(
        "Mode de résolution",
        options=["baseline", "spacy"],
        horizontal=True,
    )

    show_debug = st.toggle("Afficher les détails (debug)", value=True)

    if st.button("Résoudre l'itinéraire", type="primary"):
        result = resolve_sentence(sentence, mode=mode)

        if result.ok:
            st.success("Itinéraire trouvé ✅")
        else:
            st.error("Demande invalide ou ambiguë ❌")

        m1, m2, m3 = st.columns(3)
        m1.metric("Départ", result.departure or "—")
        m2.metric("Arrivée", result.arrival or "—")
        m3.metric("Confiance", f"{result.confidence * 100:.1f}%")

        if show_debug:
            st.subheader("Détails internes")
            st.json(result.debug or {})

with col_right:
    st.subheader("Fonctionnalités prévues")
    st.markdown(
        """
- Désambiguïsation interactive (Lyon, Paris, etc.)
- Justification NLP (règles, NER, fuzzy match)
- Itinéraire multi-étapes
- Carte interactive (OpenStreetMap)
"""
    )
