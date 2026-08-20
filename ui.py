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


def _fmt_seconds(seconds: Any) -> str:
    """Formate une durée en secondes, ou « — » si absente/invalide."""
    try:
        value = float(seconds)
    except (TypeError, ValueError):
        return "—"
    if value != value:  # NaN
        return "—"
    return f"{value:.2f} s"


def summary_metrics(summary: str, source: str) -> dict[str, Any]:
    """Métriques d'un résumé relativement à son texte source.

    Retourne les longueurs du résumé et leur proportion (%) par rapport au
    texte source, ce qui permet de comparer l'effort de condensation.
    """
    s = text_stats(summary)
    src = text_stats(source)
    return {
        "chars": s["chars"],
        "words": s["words"],
        "sentences": s["sentences"],
        "pct_source_words": (s["words"] / src["words"] * 100) if src["words"] else None,
        "pct_source_chars": (s["chars"] / src["chars"] * 100) if src["chars"] else None,
    }


def _tokens(text: str) -> set[str]:
    """Ensemble des tokens normalisés d'un texte (minuscules, hors ponctuation)."""
    return {w for w in re.findall(r"\w+", text.lower())}


def token_overlap(a: str, b: str) -> float:
    """Similarité de Jaccard entre les ensembles de tokens de deux textes.

    Proche de 1 quand les deux résumés sont très similaires, proche de 0 quand
    ils partagent peu de contenu. Permet de chiffrer l'accord deux modèles.
    """
    ta, tb = _tokens(a), _tokens(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def comparison_table(source: str, t5: dict[str, Any], scratch: dict[str, Any]) -> pd.DataFrame:
    """Construit le tableau de comparaison quantitative T5 vs Scratch.

    Args:
        source: Texte source original.
        t5: Sous-objet ``t5`` de la réponse de ``/compare``.
        scratch: Sous-objet ``scratch`` de la réponse de ``/compare``.

    Returns:
        Un DataFrame avec une colonne par modèle et une ligne par métrique.
    """
    t5_sum = (t5 or {}).get("summary", "")
    sc_sum = (scratch or {}).get("summary", "")
    m5 = summary_metrics(t5_sum, source)
    ms = summary_metrics(sc_sum, source)

    def _pct(v: float | None) -> str:
        return f"{v:.0f}%" if v is not None else "—"

    rows = [
        ("Mots", f"{m5['words']}", f"{ms['words']}"),
        ("Caractères", f"{m5['chars']}", f"{ms['chars']}"),
        ("Phrases", f"{m5['sentences']}", f"{ms['sentences']}"),
        ("Longueur (% du source)", _pct(m5["pct_source_words"]),
         _pct(ms["pct_source_words"])),
        ("Temps d'inférence", _fmt_seconds((t5 or {}).get("inference_seconds")),
         _fmt_seconds((scratch or {}).get("inference_seconds"))),
    ]

    df = pd.DataFrame(rows, columns=["Métrique", "T5", "Scratch"])

    t5_words = m5["words"]
    sc_words = ms["words"]
    if t5_words and sc_words:
        leader = "T5" if t5_words < sc_words else "Scratch"
        df = pd.concat([
            df,
            pd.DataFrame([{"Métrique": "Résumé le plus concis",
                           "T5": "✓" if leader == "T5" else "",
                           "Scratch": "✓" if leader == "Scratch" else ""}]),
        ], ignore_index=True)

    if t5_sum and sc_sum:
        overlap = token_overlap(t5_sum, sc_sum)
        df = pd.concat([
            df,
            pd.DataFrame([{"Métrique": "Similarité des 2 résumés (Jaccard)",
                           "T5": f"{overlap:.0%}", "Scratch": f"{overlap:.0%}"}]),
        ], ignore_index=True)

    return df


def export_comparison(source: str, t5: dict[str, Any], scratch: dict[str, Any]) -> str:
    """Sérialise une comparaison complète en texte Markdown exportable."""
    lines = [
        "# Comparaison des résumés — Train vs Pre-train",
        "",
        "## Texte source",
        source,
        "",
        "## Résumé T5",
        (t5 or {}).get("summary", "").strip() or "—",
        "",
        "## Résumé Scratch",
        (scratch or {}).get("summary", "").strip() or "—",
        "",
        "## Temps d'inférence",
        f"- T5 : {_fmt_seconds((t5 or {}).get('inference_seconds'))}",
        f"- Scratch : {_fmt_seconds((scratch or {}).get('inference_seconds'))}",
        "",
    ]
    return "\n".join(lines)



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
        cols[3].metric("Temps d'inférence", _fmt_seconds(seconds))


def summary_actions(payload: dict[str, Any], *, file_stem: str = "resume") -> None:
    """Boutons copier / télécharger pour un résumé (permet l'export du résultat).

    ``st.code`` affiche un bouton de copie natif dans le coin supérieur droit ;
    le bouton de téléchargement met le résumé à disposition en ``.md``.
    """
    summary = (payload.get("summary") or "").strip()
    model = payload.get("model", "resume")
    with st.expander("Copier / télécharger ce résumé", icon=":material/content_copy:"):
        if summary:
            st.code(summary, language="text")
            st.download_button(
                "Télécharger le résumé (.md)",
                data=summary,
                file_name=f"{file_stem}_{model}.md",
                mime="text/markdown",
                icon=":material/download:",
                use_container_width=True,
            )
        else:
            st.caption("Aucun résumé à exporter.")


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
