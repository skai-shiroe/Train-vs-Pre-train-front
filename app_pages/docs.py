"""Page « Documentation » : guide de l'API et de la configuration."""

from __future__ import annotations

import pandas as pd
import streamlit as st

st.markdown("## :material/menu_book: Documentation")
st.caption(
    "Tout savoir sur l'API backend, ses endpoints, ses schémas et sa configuration. "
    "La doc interactive complète est disponible sur **Swagger UI** (`/docs`)."
)

# ---------------------------------------------------------------------------
# Accès rapide à Swagger
# ---------------------------------------------------------------------------
base = st.session_state.api_base
with st.container(border=True):
    st.markdown("**Documentation interactive (Swagger UI)**")
    st.page_link(
        f"{base}/docs",
        label=f"Ouvrir {base}/docs",
        icon=":material/open_in_new:",
    )
    st.caption("Toutes les routes sont testables directement depuis le navigateur.")

# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
st.markdown("### :material/list_alt: Endpoints")
endpoints = [
    {
        "Méthode": "GET",
        "Route": "/health",
        "Corps": "—",
        "Réponse": '{"status": "ok"}',
        "Erreurs": "—",
    },
    {
        "Méthode": "GET",
        "Route": "/models",
        "Corps": "—",
        "Réponse": "[ModelInfo…] — état de chaque modèle",
        "Erreurs": "—",
    },
    {
        "Méthode": "POST",
        "Route": "/summarize",
        "Corps": '{"text", "model": "t5|scratch", "max_new_tokens"}',
        "Réponse": "{model, summary, inference_seconds}",
        "Erreurs": "503 si modèle indisponible",
    },
    {
        "Méthode": "POST",
        "Route": "/compare",
        "Corps": '{"text", "max_new_tokens"}',
        "Réponse": "{text, t5, scratch}",
        "Erreurs": "503 si scratch indisponible",
    },
    {
        "Méthode": "POST",
        "Route": "/summarize-file",
        "Corps": "multipart `file` + query `model` / `max_new_tokens`",
        "Réponse": "{filename, extracted_chars, model, summary, inference_seconds}",
        "Erreurs": "422 si format non supporté (.txt/.pdf uniquement)",
    },
]
st.dataframe(pd.DataFrame(endpoints), hide_index=True)

# ---------------------------------------------------------------------------
# Exemples d'appels
# ---------------------------------------------------------------------------
st.markdown("### :material/terminal: Exemples d'appels")
tabs = st.tabs(["cURL", "Python (requests)", "Python (requests + fichier)"])

with tabs[0]:
    st.code(
        f'''# Résumer avec T5
curl -X POST {base}/summarize \\
  -H "Content-Type: application/json" \\
  -d '{{"text": "Your article here.", "model": "t5", "max_new_tokens": 64}}'

# Comparer les deux modèles
curl -X POST {base}/compare \\
  -H "Content-Type: application/json" \\
  -d '{{"text": "Your article here.", "max_new_tokens": 64}}'

# Résumer un fichier
curl -X POST "{base}/summarize-file?model=t5&max_new_tokens=64" \\
  -F "file=@/chemin/vers/document.pdf"''',
        language="bash",
    )

with tabs[1]:
    st.code(
        f'''import requests

base = "{base}"

resp = requests.post(
    f"{{base}}/summarize",
    json={{"text": "Votre article ici.", "model": "t5", "max_new_tokens": 64}},
    timeout=180,
)
print(resp.json())
# -> {{"model": "t5", "summary": "…", "inference_seconds": 2.9}}''',
        language="python",
    )

with tabs[2]:
    st.code(
        f'''import requests

base = "{base}"
with open("document.pdf", "rb") as f:
    resp = requests.post(
        f"{{base}}/summarize-file",
        files={{"file": ("document.pdf", f)}},
        params={{"model": "t5", "max_new_tokens": 64}},
        timeout=180,
    )
print(resp.json())''',
        language="python",
    )

# ---------------------------------------------------------------------------
# Schémas
# ---------------------------------------------------------------------------
st.markdown("### :material/data_object: Schémas de données")
st.markdown(
    """- **ModelInfo** : `name` (`t5`/`scratch`), `available`, `detail` (dict d'informations), `error`.
- **SummarizeRequest** : `text` (≥1 char), `model`, `max_new_tokens` (>0, défaut 64).
- **SummarizeResponse** : `model`, `summary`, `inference_seconds`.
- **CompareRequest** : `text`, `max_new_tokens`.
- **CompareResponse** : `text`, `t5` (SummarizeResponse), `scratch` (SummarizeResponse).
- **FileSummarizeResponse** : hérite de SummarizeResponse + `filename`, `extracted_chars`."""
)

# ---------------------------------------------------------------------------
# Configuration (variables d'environnement du backend)
# ---------------------------------------------------------------------------
st.markdown("### :material/settings: Configuration du backend")
st.markdown(
    """Le backend lit sa configuration depuis des variables d'environnement :

| Variable | Rôle | Défaut |
|---|---|---|
| `T5_CHECKPOINT_PATH` | Chemin vers `best.pt` de T5 fine-tuné | non défini → zero-shot |
| `SCRATCH_CHECKPOINT_PATH` | Chemin vers `best.pt` du from-scratch | non défini → 503 |
| `T5_HF_ID` | Identifiant Hugging Face de T5 | `t5-small` |
| `MAX_SOURCE_TOKENS` / `MAX_TARGET_TOKENS` | Troncatures | `512` / `64` |
| `DEFAULT_BATCH_SIZE` | Taille de lot d'inférence | `8` |

Le décodage utilise la **recherche en faisceau** (`num_beams=4`, `no_repeat_ngram_size=3`),
alignée sur les réglages d'évaluation du repo ML."""
)

# ---------------------------------------------------------------------------
# Dépôts
# ---------------------------------------------------------------------------
st.markdown("### :material/link: Dépôts du projet")
st.markdown(
    """- **Frontend (ce dépôt)** : [skai-shiroe/Train-vs-Pre-train-front](https://github.com/skai-shiroe/Train-vs-Pre-train-front)
- **Backend API** : [skai-shiroe/Train-vs-Pre-train-api](https://github.com/skai-shiroe/Train-vs-Pre-train-api)
- **Repo ML** : [skai-shiroe/Train-vs-Pre-train](https://github.com/skai-shiroe/Train-vs-Pre-train)"""
)
