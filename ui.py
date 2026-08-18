"""Helpers d'affichage réutilisés par les différentes pages.

Ces fonctions ne font pas d'appel réseau : elles mettent en forme les données
récupérées par :mod:`api_client` pour un rendu cohérent et lisible.
"""

from __future__ import annotations

import re
from typing import Any

import pandas as pd
import streamlit as st

from api_client import MODEL_ICONS, MODEL_LABELS, MODEL_SHORT_DESC


# ---------------------------------------------------------------------------
# Statistiques de texte
# ---------------------------------------------------------------------------
def text_stats(text: str) -> dict[str, int]:
    """Calcule quelques statistiques simples sur un texte."""
    words = len(text.split())
    sentences = len(re.findall(r"[.!?…](?:\s|$)", text)) or (1 if text.strip() else 0)
    return {"chars": len(text), "words": words, "sentences": sentences}


# ---------------------------------------------------------------------------
# Badges d'état
# ---------------------------------------------------------------------------
def availability_badge(available: bool, *, mode: str | None = None) -> None:
    """Affiche un badge vert/rouge selon la disponibilité du modèle."""
    if available:
        label = mode or "Disponible"
        st.badge(label, icon=":material/check_circle:", color="green")
    else:
        st.badge("Indisponible", icon=":material/error:", color="red")


# ---------------------------------------------------------------------------
# Carte de résultat d'un résumé
# ---------------------------------------------------------------------------
def render_summary_card(payload: dict[str, Any], *, title: str | None = None) -> None:
    """Rend une carte contenant un résumé et ses métriques.

    Args:
        payload: Dictionnaire retourné par ``/summarize`` ou le sous-objet
            ``t5`` / ``scratch`` de ``/compare``.
        title: Titre optionnel de la carte.
    """
    model = payload.get("model", "?")
    summary = payload.get("summary", "")
    seconds = payload.get("inference_seconds")

    stats = text_stats(summary)

    with st.container(border=True):
        head = title or MODEL_LABELS.get(model, model)
        st.markdown(f"#### {MODEL_ICONS.get(model, '')} {head}")
        availability_badge(True, mode=_mode_label(payload))
        st.space("small")
        st.markdown(summary)
        st.space("small")

        cols = st.columns(4)
        cols[0].metric("Caractères", f"{stats['chars']:,}".replace(",", " "))
        cols[1].metric("Mots", f"{stats['words']:,}".replace(",", " "))
        cols[2].metric("Phrases", f"{stats['sentences']:,}".replace(",", " "))
        if seconds is not None:
            cols[3].metric("Temps d'inférence", f"{seconds:.2f} s")


def _mode_label(payload: dict[str, Any]) -> str:
    """Libellé d'état court (Disponible / mode du modèle si renseigné)."""
    detail = payload.get("detail") or {}
    mode = detail.get("mode")
    if mode:
        return {"trained": "Entraîné", "fine_tuned": "Fine-tuné",
                "zero_shot": "Zero-shot"}.get(mode, mode)
    return "Disponible"


# ---------------------------------------------------------------------------
# Tableau des modèles (page /models)
# ---------------------------------------------------------------------------
def models_dataframe(models: list[dict[str, Any]]) -> pd.DataFrame:
    """Convertit la réponse de ``/models`` en DataFrame pour l'affichage."""
    rows = []
    for info in models:
        detail = info.get("detail") or {}
        rows.append(
            {
                "Modèle": MODEL_LABELS.get(info.get("name", ""), info.get("name", "")),
                "Disponible": "Oui" if info.get("available") else "Non",
                "Mode": _mode_label(info),
                "ID Hugging Face": detail.get("hf_id", "—"),
                "Baseline": detail.get("baseline", "—"),
                "Révision": detail.get("revision", "—"),
                "Paramètres": _human_params(detail.get("parameters")),
                "Écart d'architectures": _arch_summary(detail),
                "Erreur": info.get("error") or "—",
            }
        )
    return pd.DataFrame(rows)


def _human_params(value: str | None) -> str:
    """Formate un nombre de paramètres lisiblement (60 506 624)."""
    if not value:
        return "—"
    try:
        return f"{int(value):,}".replace(",", " ")
    except (TypeError, ValueError):
        return str(value)


def _arch_summary(detail: dict[str, Any]) -> str:
    """Résume les champs d'architecture du modèle scratch, le cas échéant."""
    keys = ("d_model", "encoder_layers", "decoder_layers", "num_heads")
    parts = [f"{k}={detail[k]}" for k in keys if detail.get(k) is not None]
    return ", ".join(parts) if parts else "—"
