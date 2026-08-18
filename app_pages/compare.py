"""Page « Comparer les modèles » : appelle ``POST /compare``.

Affiche les résumés des deux modèles côte à côte. Si le modèle from scratch
est indisponible (aucun checkpoint configuré), l'API renvoie un 503 : la page
se replie alors sur ``POST /summarize`` pour T5 et le signale clairement.
"""

from __future__ import annotations

import streamlit as st

from api_client import MODEL_ICONS, MODEL_LABELS, ApiError, compare, summarize
from services import cached_models
from ui import render_summary_card, text_stats

st.markdown("## :material/compare: Comparer les modèles")
st.caption(
    "Le même texte est résumé par **T5** et par le **Transformer from scratch**, "
    "pour un affichage côte à côte (analyse comparative)."
)


def _render_side_by_side(result: dict) -> None:
    """Affiche les résumés côte à côte, avec le texte source en haut."""
    source = result.get("text", "")
    with st.container(border=True):
        st.markdown("**Texte source**")
        st.caption(source)

    t5 = result.get("t5")
    scratch = result.get("scratch")

    col_left, col_right = st.columns(2)
    with col_left:
        if t5:
            render_summary_card(t5, title=f"{MODEL_LABELS['t5']} · "
                                          f"{MODEL_ICONS['t5']}")
        else:
            st.error("Résumé T5 manquant.", icon=":material/error:")
    with col_right:
        if scratch:
            render_summary_card(scratch, title=f"{MODEL_LABELS['scratch']} · "
                                               f"{MODEL_ICONS['scratch']}")
        else:
            with st.container(border=True):
                st.markdown(f"#### {MODEL_ICONS['scratch']} "
                            f"{MODEL_LABELS['scratch']}")
                st.badge("Indisponible", icon=":material/error:", color="red")
                st.caption(
                    "Aucun checkpoint from-scratch configuré. Configurez "
                    "`SCRATCH_CHECKPOINT_PATH` côté backend pour activer ce modèle."
                )

    with st.expander("Réponse brute de l'API"):
        st.json(result)


# Vérifier la disponibilité des modèles (pour guider l'utilisateur).
try:
    models = cached_models(st.session_state.api_base)
    availability = {info.get("name"): info.get("available", False) for info in models}
except ApiError:
    availability = {}
t5_ok = availability.get("t5", False)
scratch_ok = availability.get("scratch", False)

if not t5_ok:
    st.warning(
        "Le modèle **T5** est actuellement indisponible (API injoignable ou erreur). "
        "Vérifiez que le backend est démarré.",
        icon=":material/error:",
    )
elif not scratch_ok:
    st.info(
        "Le modèle **from scratch** est indisponible (aucun checkpoint configuré). "
        "Seul **T5** sera affiché.",
        icon=":material/info:",
    )

# Options.
opt_col, len_col = st.columns([1, 2])
with opt_col:
    st.caption("Modèles comparés")
    st.markdown(
        f"{MODEL_ICONS['t5']} **T5** · {MODEL_ICONS['scratch']} **from scratch**"
    )
max_tokens = len_col.slider(
    "Longueur maximale de chaque résumé (tokens)",
    min_value=16,
    max_value=128,
    value=64,
    step=8,
)

text = st.text_area(
    "Texte à comparer",
    height=200,
    placeholder="Collez ici un article à résumer par les deux modèles…",
    label_visibility="collapsed",
    key="compare_text",
)

if text.strip():
    stats = text_stats(text)
    st.caption(f"{stats['chars']:,} caractères · {stats['words']:,} mots · "
               f"{stats['sentences']:,} phrases")

submit = st.button(
    "Comparer les deux modèles",
    icon=":material/compare:",
    type="primary",
    disabled=not text.strip(),
    use_container_width=True,
    key="compare_submit",
)

if submit:
    if not t5_ok:
        st.error(
            "Impossible de comparer : le modèle T5 est indisponible.",
            icon=":material/error:",
        )
    elif scratch_ok:
        # Les deux modèles sont disponibles : utiliser /compare.
        with st.spinner("Comparaison en cours avec les deux modèles…"):
            try:
                result = compare(st.session_state.api_base, text, int(max_tokens))
            except ApiError as exc:
                st.error(f"{exc.message}", icon=":material/error:")
            else:
                st.toast("Comparaison terminée !", icon=":material/check_circle:")
                _render_side_by_side(result)
    else:
        # Scratch indisponible : repli sur T5 seul.
        with st.spinner("Résumé T5 en cours (scratch indisponible)…"):
            try:
                t5_result = summarize(st.session_state.api_base, text, "t5", int(max_tokens))
            except ApiError as exc:
                st.error(f"{exc.message}", icon=":material/error:")
            else:
                st.toast("Résumé T5 généré (scratch indisponible).",
                         icon=":material/info:")
                _render_side_by_side({"text": text, "t5": t5_result, "scratch": None})
