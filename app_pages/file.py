"""Page « Résumer un fichier » : appelle ``POST /summarize-file``."""

from __future__ import annotations

import streamlit as st

from api_client import MODEL_ICONS, MODEL_LABELS, ApiError, summarize_file
from ui import render_summary_card, summary_actions

st.markdown("## :material/upload_file: Résumer un fichier")
st.caption(
    "Uploadiez un fichier **`.txt`** ou **`.pdf`** : le texte en est extrait "
    "côté backend puis résumé par le modèle choisi."
)

# Options.
opt_col, len_col = st.columns([1, 2])
model_choice = opt_col.segmented_control(
    "Modèle",
    ["t5", "scratch"],
    default="t5",
    format_func=lambda m: MODEL_LABELS[m],
)
max_tokens = len_col.slider(
    "Longueur maximale du résumé (tokens)",
    min_value=16,
    max_value=128,
    value=64,
    step=8,
)

uploaded = st.file_uploader(
    "Choisir un fichier (.txt ou .pdf)",
    type=["txt", "pdf"],
    accept_multiple_files=False,
    key="file_upload",
)

if uploaded is not None:
    meta = st.columns(4)
    meta[0].metric("Nom du fichier", uploaded.name)
    meta[1].metric("Taille", f"{len(uploaded.getvalue()):,} octets".replace(",", " "))
    meta[2].metric("Type", uploaded.type or "—")
    meta[3].metric("Modèle", model_choice)

submit = st.button(
    "Résumer le fichier",
    icon=":material/auto_awesome:",
    type="primary",
    disabled=uploaded is None,
    use_container_width=True,
    key="file_submit",
)

if submit and uploaded is not None:
    with st.spinner("Extraction du texte puis résumé…"):
        try:
            result = summarize_file(
                st.session_state.api_base,
                uploaded.name,
                uploaded.getvalue(),
                model_choice,
                int(max_tokens),
            )
        except ApiError as exc:
            st.error(f"{exc.message}", icon=":material/error:")
        else:
            st.toast("Fichier résumé !", icon=":material/check_circle:")
            st.space("small")

            info = st.columns(2)
            with info[0]:
                with st.container(border=True):
                    st.metric("Fichier", result.get("filename", "—"))
                    st.metric("Caractères extraits", f"{result.get('extracted_chars', 0):,}".replace(",", " "))
                    st.metric("Modèle", result.get("model", "—"))
                    st.metric("Temps d'inférence", f"{result.get('inference_seconds', 0):.2f} s")
            with info[1]:
                with st.container(border=True):
                    st.markdown("**À noter**")
                    st.caption(
                        "Le texte extrait du fichier est traité côté backend et "
                        "tronqué aux longueurs d'entraînement (512 tokens source). "
                        "Seule la longueur extraite est renvoyée par l'API."
                    )

            st.space("small")
            render_summary_card(result, title=f"{MODEL_LABELS[model_choice]} · "
                                              f"{MODEL_ICONS.get(model_choice, '')}")
            summary_actions(result, file_stem=uploaded.name)
            with st.expander("Réponse brute de l'API"):
                st.json(result)
