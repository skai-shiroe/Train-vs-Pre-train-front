"""Gestion du thème (mode sombre / clair) de l'application Streamlit.

Streamlit fixe son thème au démarrage depuis ``.streamlit/config.toml`` (ici
``base = "dark"``). Pour permettre à l'utilisateur de basculer entre les modes
sans redémarrer le serveur, on injecte :

- un petit script qui change l'attribut ``data-theme`` de l'élément ``<html>``
  (Streamlit applique ses variables de thème via des sélecteurs
  ``[data-theme="dark"/"light"]``) ;
- des *overrides* CSS de secours pour les surfaces principales, afin de
  garantir un rendu clair/sombre net quel que soit le mode.

Le choix est conservé dans ``st.session_state`` et survit aux reruns.
"""

from __future__ import annotations

import streamlit as st

#: Libellés d'affichage -> valeurs ``data-theme`` de Streamlit.
MODE_LABELS = {
    "Sombre": "dark",
    "Clair": "light",
}

#: Overrides CSS appliqués selon le mode. On cible les variables de thème de
#: Streamlit ainsi que quelques surfaces clés, avec ``!important`` pour
#: garantir la prise en compte au-dessus des styles par défaut.
_CSS = """
html[data-theme="light"] {
  --primary-color: #0068c9 !important;
  --background-color: #ffffff !important;
  --secondary-background-color: #f8f9fa !important;
  --text-color: #262730 !important;
  --link-color: #0068c9 !important;
  --border-color: #e0e0e0 !important;
  --code-background-color: #f6f8fa !important;
  --code-text-color: #24292f !important;
}
html[data-theme="dark"] {
  --primary-color: #60a5fa !important;
  --background-color: #0f172a !important;
  --secondary-background-color: #1e293b !important;
  --text-color: #f1f5f9 !important;
  --link-color: #60a5fa !important;
  --border-color: #334155 !important;
  --code-background-color: #1e293b !important;
  --code-text-color: #cbd5e1 !important;
}
"""


def theme_controls() -> str:
    """Affiche le sélecteur de thème dans la sidebar et retourne le thème choisi.

    À appeler dans le bloc ``with st.sidebar:``.
    """
    st.session_state.setdefault("theme", "dark")
    theme = st.session_state.theme

    if "theme_toggle" not in st.session_state:
        st.session_state.theme_toggle = "Sombre" if theme == "dark" else "Clair"

    choice = st.sidebar.radio(
        "Thème",
        options=["Sombre", "Clair"],
        key="theme_toggle",
        horizontal=True,
        help="Bascule entre le mode sombre (défaut) et le mode clair.",
    )
    theme = MODE_LABELS[choice]
    st.session_state.theme = theme

    if theme == "dark":
        st.sidebar.caption(":material/dark_mode: Mode sombre actif")
    else:
        st.sidebar.caption(":material/light_mode: Mode clair actif")

    return theme


def inject_theme(theme: str) -> None:
    """Injecte le CSS de thème et le script de bascule dans le document principal.

    À appeler **hors** du contexte ``st.sidebar`` (dans le corps principal),
    sinon le CSS ne cible pas le document de l'application (chaque élément est
    rendu dans son propre iframe) et le mode ne s'applique pas.

    Le script cible ``window.parent.document`` pour agir sur le ``<html>`` de la
    page réelle, avec repli sur ``document`` si nécessaire.
    """
    st.markdown(
        f"""<style>{_CSS}</style>
<script>
(function() {{
  try {{
    var doc = window.parent.document;
    doc.documentElement.setAttribute('data-theme', '{theme}');
  }} catch (e) {{
    document.documentElement.setAttribute('data-theme', '{theme}');
  }}
}})();
</script>""",
        unsafe_allow_html=True,
    )


def apply_theme() -> str:
    """Affiche le sélecteur (sidebar) puis injecte le thème (corps principal).

    Retourne le thème sélectionné. À appeler au début de la page, le sélecteur
    étant rendu dans la barre latérale et l'injection dans le corps principal.
    """
    theme = theme_controls()
    inject_theme(theme)
    return theme
