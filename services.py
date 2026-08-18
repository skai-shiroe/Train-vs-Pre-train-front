"""Couche de service : appels API mis en cache pour l'interface.

Le cache évite de solliciter le backend à chaque rerun de Streamlit (un clic
sur un widget relance tout le script). Les données d'état (/health, /models)
sont mises en cache peu de temps ; les inférences ne le sont pas.
"""

from __future__ import annotations

import streamlit as st

from api_client import get_health, get_models


@st.cache_data(ttl=15, show_spinner=False)
def cached_health(base_url: str) -> dict:
    """Version mise en cache de ``GET /health``."""
    return get_health(base_url)


@st.cache_data(ttl=15, show_spinner=False)
def cached_models(base_url: str) -> list[dict]:
    """Version mise en cache de ``GET /models``."""
    return get_models(base_url)


def force_refresh() -> None:
    """Vide le cache de statut pour forcer un rechargement frais."""
    cached_health.clear()
    cached_models.clear()
