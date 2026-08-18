"""Page d'accueil : présentation du projet et accès rapide."""

from __future__ import annotations

import streamlit as st

from api_client import MODEL_ICONS, MODEL_LABELS, MODEL_SHORT_DESC, ApiError
from services import cached_models
from ui import availability_badge

st.markdown("## :material/waving_hand: Bienvenue")
st.markdown(
    "Cette application met en regard **deux modèles de résumé automatique** "
    "entraînés sur le corpus **XSum** (articles de presse BBC) : un "
    "**Transformer entraîné from scratch** et une baseline **T5 fine-tunée**. "
    "Collez un texte, uploadiez un fichier, et comparez leurs résumés."
)

# ---------------------------------------------------------------------------
# KPIs rapides
# ---------------------------------------------------------------------------
with st.container(horizontal=True):
    st.metric("Modèles exposés", "2", border=True)
    st.metric("Corpus", "XSum · BBC", border=True)
    st.metric("Méthode de décodage", "Beam search", border=True)
    st.metric("Frontend", "Streamlit", border=True)

# ---------------------------------------------------------------------------
# Cartes des modèles
# ---------------------------------------------------------------------------
st.markdown("### :material/view_module: Les deux modèles")
col_left, col_right = st.columns(2)

try:
    models = cached_models(st.session_state.api_base)
    by_name = {info.get("name"): info for info in models}
except ApiError:
    by_name = {}

for col, name in ((col_left, "t5"), (col_right, "scratch")):
    with col:
        with st.container(border=True):
            st.markdown(f"### {MODEL_ICONS.get(name, '')} {MODEL_LABELS.get(name, name)}")
            info = by_name.get(name) or {}
            availability_badge(
                info.get("available", False),
                mode=(info.get("detail") or {}).get("mode"),
            )
            st.caption(MODEL_SHORT_DESC.get(name, ""))

            detail = (info or {}).get("detail") or {}
            rows = [
                ("ID Hugging Face", detail.get("hf_id", "—")),
                ("Révision", detail.get("revision", "—")),
                ("Baseline", detail.get("baseline", "—")),
                ("Paramètres", f"{detail.get('parameters', '—')}"),
            ]
            for label, value in rows:
                st.markdown(f"**{label}** — `{value}`")

            error = (info or {}).get("error")
            if error:
                st.space("small")
                st.caption(f":orange[→ {error}]")

# ---------------------------------------------------------------------------
# Comment ça marche
# ---------------------------------------------------------------------------
st.markdown("### :material/timeline: Comment ça marche")
steps = st.columns(3, border=True)
with steps[0]:
    st.markdown("**:material/description: 1. Choisissez un texte**")
    st.caption("Collez un article ou chargez un fichier `.txt` / `.pdf`.")
with steps[1]:
    st.markdown("**:material/compare: 2. Résumez ou comparez**")
    st.caption("Un modèle seul, ou les deux côte à côte pour l'analyse comparative.")
with steps[2]:
    st.markdown("**:material/query_stats: 3. Analysez**")
    st.caption("Temps d'inférence, longueur du résumé, état des modèles, API.")

# ---------------------------------------------------------------------------
# Liens rapides
# ---------------------------------------------------------------------------
st.markdown("### :material/touch_app: Accès rapide")
quick = st.columns(2)
with quick[0]:
    st.page_link("app_pages/summarize.py", label="Résumer un texte", icon=":material/description:")
    st.page_link("app_pages/compare.py", label="Comparer les deux modèles", icon=":material/compare:")
with quick[1]:
    st.page_link("app_pages/file.py", label="Résumer un fichier", icon=":material/upload_file:")
    st.page_link("app_pages/docs.py", label="Documentation de l'API", icon=":material/menu_book:")

# ---------------------------------------------------------------------------
# Note de domaine
# ---------------------------------------------------------------------------
with st.expander("À propos du domaine d'entraînement", icon=":material/lightbulb:"):
    st.markdown(
        "Les deux modèles sont entraînés sur **XSum**, des articles de presse "
        "de la BBC. Sur un texte hors de ce domaine (ex. une phrase générique), "
        "la qualité des résumés se dégrade, en particulier pour le modèle "
        "from scratch qui peut halluciner du contenu sans rapport. C'est un "
        "résultat qualitatif pertinent pour l'analyse comparative."
    )
