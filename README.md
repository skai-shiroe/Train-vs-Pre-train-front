# Train vs Pre-train — Frontend (Streamlit)

Interface utilisateur moderne, sombre et responsive pour l'API
[Train-vs-Pre-train](https://github.com/skai-shiroe/Train-vs-Pre-train-api) :
elle permet de **résumer un texte** ou un **fichier** et de **comparer** les
deux modèles de résumé automatique (un Transformer entraîné **from scratch** et
une baseline **T5** fine-tunée, entraînés sur le corpus **XSum**).

## ✨ Fonctionnalités

| Page | Description |
|---|---|
| **Accueil** | Présentation du projet, cartes des modèles, KPIs, accès rapide. |
| **Résumer un texte** | `POST /summarize` — résume un texte avec `t5` ou `scratch`. |
| **Comparer les modèles** | `POST /compare` — résumés **côte à côte** (T5 vs scratch). |
| **Résumer un fichier** | `POST /summarize-file` — upload `.txt` / `.pdf`. |
| **Modèles & API** | `GET /health` + `GET /models` — tableau de bord de l'API. |
| **Documentation** | Guide des endpoints, exemples (cURL / Python), configuration. |

Points d'attention UX :
- Si le modèle **from scratch** est indisponible (aucun checkpoint), la page de
  comparaison se **replie proprement sur T5** et le signale au lieu d'afficher
  une erreur brutale.
- Chaque résumé affiche ses **métriques** (temps d'inférence, caractères,
  mots, phrases) + la **réponse brute** de l'API (JSON) dans un expandeur.
- Barre latérale partagée : **URL de l'API** modifiable, indicateur en ligne,
  disponibilité des deux modèles, bouton **Rafraîchir** (vide le cache).

## 🚀 Démarrage rapide

### Prérequis
- Python 3.11+
- Le **backend FastAPI** doit tourner sur `http://127.0.0.1:8000`
  (voir le dépôt [Train-vs-Pre-train-api](https://github.com/skai-shiroe/Train-vs-Pre-train-api)).

### Installation

```bash
python -m venv .venv
# Windows (PowerShell) : .venv\Scripts\Activate.ps1
# Linux / macOS        : source .venv/bin/activate
pip install -r requirements.txt
```

### Lancer

```bash
streamlit run streamlit_app.py
# ou, en module :
python -m streamlit run streamlit_app.py
```

Puis ouvrir **http://localhost:8501**. Le CORS du backend autorise déjà ce
port (le front Streamlit appelle l'API depuis le serveur Python, donc pas de
blocage navigateur).

> Si l'API est sur une autre adresse, changez l'**URL de l'API** dans la barre
> latérale de l'application (champ mémorisé en session, défaut
> `http://127.0.0.1:8000`).

## 🗂️ Structure

```
Train-vs-Pre-train-front/
├── streamlit_app.py      # Point d'entrée : navigation + barre latérale partagée
├── api_client.py         # Client HTTP (requests) vers l'API FastAPI
├── services.py           # Appels API mis en cache (@st.cache_data)
├── ui.py                 # Helpers d'affichage (cartes, badges, stats, dataframes)
├── app_pages/
│   ├── home.py           # Accueil
│   ├── summarize.py      # Résumer un texte
│   ├── compare.py        # Comparer les modèles
│   ├── file.py           # Résumer un fichier
│   ├── models.py         # Modèles & API
│   └── docs.py           # Documentation
├── .streamlit/
│   └── config.toml       # Thème sombre (slate/bleu, Inter + JetBrains Mono)
├── requirements.txt
└── README.md
```

## 🔧 Détails techniques

- **Multi-pages** via `st.navigation` (dossier `app_pages/`).
- **Client HTTP** léger dans `api_client.py` : chaque fonction correspond à un
  endpoint, lève une `ApiError` lisible et normalise les erreurs FastAPI.
- **Cache** des appels d'état (`/health`, `/models`) avec `@st.cache_data`
  (TTL 15 s) pour ne pas solliciter le backend à chaque rerun ; les inférences
  ne sont volontairement **pas** cachées.
- **Thème** personnalisé dans `.streamlit/config.toml` (palette sombre
  professionnelle, sans CSS custom).

## 🧪 Test

1. Démarrer le backend : `uvicorn app.main:app --port 8000` (dépôt api).
2. Démarrer le frontend : `streamlit run streamlit_app.py`.
3. Depuis la page **Modèles & API**, vérifier que `/health` répond et que T5
   est disponible (le from-scratch renvoie 503 tant qu'aucun checkpoint
   n'est configuré côté backend).

