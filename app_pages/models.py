"""Page « Modèles & API » : tableau de bord de l'état du backend.

Affiche l'état de connexion, la liste détaillée des modèles (GET /models),
l'état de santé (GET /health) et le temps de réponse, plus la documentation
des endpoints exposés.
"""

from __future__ import annotations

import time

import pandas as pd
import streamlit as st

from api_client import ApiError, get_health, get_models
from services import cached_models, force_refresh
from ui import models_dataframe

st.markdown("## :material/dashboard: Modèles & API")
st.caption(
    "État du backend FastAPI, détail des deux modèles et documentation des "
    "endpoints. Cliquez sur « Rafraîchir » pour re-solliciter l'API."
)

if st.button("Rafraîchir les données", icon=":material/refresh:", type="primary"):
    force_refresh()
    st.rerun()

base = st.session_state.api_base

# ---------------------------------------------------------------------------
# Santé de l'API + latence
# ---------------------------------------------------------------------------
st.markdown("### :material/sensors: Santé de l'API")

with st.container(horizontal=True):
    try:
        start = time.perf_counter()
        health = get_health(base)
        latency_ms = (time.perf_counter() - start) * 1000
        st.metric("GET /health", health.get("status", "?"), border=True)
        st.metric("Latence", f"{latency_ms:.0f} ms", border=True)
        st.badge("API en ligne", icon=":material/check_circle:", color="green")
    except ApiError as exc:
        st.metric("GET /health", "—", border=True)
        st.badge("API injoignable", icon=":material/cloud_off:", color="red")
        st.caption(str(exc))

# ---------------------------------------------------------------------------
# Détail des modèles
# ---------------------------------------------------------------------------
st.markdown("### :material/view_module: Modèles")
try:
    models = cached_models(base)
    df = models_dataframe(models)
    st.dataframe(
        df,
        hide_index=True,
        column_config={
            "Modèle": st.column_config.TextColumn(width="large"),
            "Erreur": st.column_config.TextColumn(width="medium"),
        },
    )
except ApiError as exc:
    st.error(f"{exc.message}", icon=":material/error:")

# ---------------------------------------------------------------------------
# Documentation des endpoints
# ---------------------------------------------------------------------------
st.markdown("### :material/list_alt: Endpoints exposés")
endpoints = [
    {
        "Méthode": "GET",
        "Route": "/health",
        "Rôle": "Vérifie que l'API répond.",
        "Réponse": "{\"status\": \"ok\"}",
    },
    {
        "Méthode": "GET",
        "Route": "/models",
        "Rôle": "Liste les modèles et leur état (zero-shot / fine-tuné / entraîné).",
        "Réponse": "Liste d'objets ModelInfo",
    },
    {
        "Méthode": "POST",
        "Route": "/summarize",
        "Rôle": "Résume un texte avec un seul modèle (`t5` ou `scratch`).",
        "Réponse": "{model, summary, inference_seconds}",
    },
    {
        "Méthode": "POST",
        "Route": "/compare",
        "Rôle": "Résume un texte avec les deux modèles, côte à côte.",
        "Réponse": "{text, t5, scratch}",
    },
    {
        "Méthode": "POST",
        "Route": "/summarize-file",
        "Rôle": "Résume un fichier uploadé (`.txt` ou `.pdf`).",
        "Réponse": "{filename, extracted_chars, model, summary, inference_seconds}",
    },
]
import pandas as pd
st.dataframe(pd.DataFrame(endpoints), hide_index=True)

with st.expander("Réponses brutes de l'API", icon=":material/code:"):
    try:
        st.json({"health": get_health(base), "models": cached_models(base)})
    except ApiError as exc:
        st.error(f"{exc.message}", icon=":material/error:")
