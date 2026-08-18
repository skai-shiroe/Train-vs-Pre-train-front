"""Page « Résumer un texte » : appelle ``POST /summarize``."""

from __future__ import annotations

import streamlit as st

from api_client import MODEL_ICONS, MODEL_LABELS, ApiError, summarize
from ui import render_summary_card, text_stats

st.markdown("## :material/description: Résumer un texte")
st.caption("Choisissez un modèle, collez un texte, et générez un résumé.")

# Options en haut : modèle + longueur du résumé.
opt_col, len_col = st.columns([1, 2])
model_choice = opt_col.segmented_control(
    "Modèle",
    ["t5", "scratch"],
    default="t5",
    format_func=lambda m: {k: MODEL_LABELS[k] for k in MODEL_LABELS}[m],
)
max_tokens = len_col.slider(
    "Longueur maximale du résumé (tokens)",
    min_value=16,
    max_value=128,
    value=64,
    step=8,
    help="Budget de tokens générés pour le résumé.",
)

# Zone de texte.
text = st.text_area(
    "Texte à résumer",
    height=200,
    placeholder="Collez ici un article (idéalement de presse) à résumer…",
    label_visibility="collapsed",
    key="summarize_text",
)

# Statistiques sur le texte saisi.
if text.strip():
    stats = text_stats(text)
    with st.container(horizontal=True):
        st.caption(f"{stats['chars']:,} caractères · {stats['words']:,} mots"
                   f" · {stats['sentences']:,} phrases")

submit = st.button(
    "Générer le résumé",
    icon=":material/auto_awesome:",
    type="primary",
    disabled=not text.strip(),
    use_container_width=True,
    key="summarize_submit",
)

if submit:
    with st.spinner(f"Résumé en cours avec {MODEL_ICONS.get(model_choice, '')} "
                    f"`{model_choice}`… (l'inférence CPU peut prendre quelques secondes)"):
        try:
            result = summarize(
                st.session_state.api_base,
                text,
                model_choice,
                int(max_tokens),
            )
        except ApiError as exc:
            st.error(f"{exc.message}", icon=":material/error:")
        else:
            st.toast("Résumé généré !", icon=":material/check_circle:")
            st.space("small")
            render_summary_card(result, title=f"{MODEL_LABELS[model_choice]} "
                                              f"({MODEL_ICONS.get(model_choice, '')})")
            with st.expander("Réponse brute de l'API"):
                st.json(result)