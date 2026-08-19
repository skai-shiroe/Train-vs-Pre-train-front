"""Point d'entrée du frontend Streamlit — Train vs Pre-train.

Construit la navigation multi-pages (``st.navigation``) et un panneau latéral
partagé : configuration de l'URL de l'API, indicateur de connexion et état de
disponibilité des deux modèles.

Lancer : ``streamlit run streamlit_app.py`` (le backend FastAPI doit tourner
sur le port 8000, voir le dépôt Train-vs-Pre-train-api).
"""

from __future__ import annotations

import streamlit as st

from api_client import DEFAULT_BASE_URL, MODEL_ICONS, ApiError
from services import cached_health, cached_models, force_refresh

st.set_page_config(
    page_title="Train vs Pre-train — Résumé automatique",
    page_icon=":material/summarize:",
    layout="wide",
)

# État partagé entre toutes les pages.
st.session_state.setdefault("api_base", DEFAULT_BASE_URL)


def render_sidebar() -> None:
    """Panneau latéral commun : connexion + disponibilité des modèles."""
    base = st.session_state.api_base

    with st.sidebar:
        st.header("Train vs Pre-train", anchor=False)
        st.caption("Résumé automatique : Transformer from scratch **vs** T5")

        st.subheader("Connexion API", anchor=False)
        st.text_input(
            "URL de l'API",
            key="api_base",
            help="Adresse du backend FastAPI (uvicorn). Ex. http://127.0.0.1:8000",
        )

        cols = st.columns([1, 1])
        with cols[0]:
            if st.button("Rafraîchir", icon=":material/refresh:", use_container_width=True):
                force_refresh()
                st.rerun()

        _health_indicator(base)

        st.subheader("Modèles", anchor=False)
        _models_indicator(base)

        st.space("medium")
        st.caption("Frontend v1.0 — Streamlit · Consomme l'API FastAPI du backend")


def _health_indicator(base: str) -> None:
    try:
        health = cached_health(base)
        st.badge("API en ligne", icon=":material/sensors:", color="green")
        st.caption(f"`GET /health` → `{health.get('status', '?')}`")
    except ApiError as exc:
        st.badge("API injoignable", icon=":material/cloud_off:", color="red")
        st.caption(str(exc))


def _models_indicator(base: str) -> None:
    try:
        models = cached_models(base)
        for info in models:
            name = info.get("name", "?")
            available = info.get("available", False)
            icon = MODEL_ICONS.get(name, "")
            if available:
                st.markdown(f"{icon} **{name}** — :green-badge[Disponible]")
            else:
                st.markdown(f"{icon} **{name}** — :red-badge[Indisponible]")
    except ApiError:
        st.caption("Modèles inconnus : API injoignable.")


# Navigation multi-pages.
pages = st.navigation(
    {
        "": [
            st.Page("app_pages/home.py", title="Accueil", icon=":material/home:"),
        ],
        "Résumé": [
            st.Page("app_pages/summarize.py", title="Résumer un texte", icon=":material/description:"),
            st.Page("app_pages/compare.py", title="Comparer les modèles", icon=":material/compare:"),
            st.Page("app_pages/file.py", title="Résumer un fichier", icon=":material/upload_file:"),
        ],
        "Information": [
            st.Page("app_pages/models.py", title="Modèles & API", icon=":material/dashboard:"),
            st.Page("app_pages/monitor.py", title="Monitoring", icon=":material/monitor_heart:"),
            st.Page("app_pages/docs.py", title="Documentation", icon=":material/menu_book:"),
        ],
    },
    position="top",
)

render_sidebar()

page = pages
page.run()
