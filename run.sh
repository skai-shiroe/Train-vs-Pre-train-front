#!/usr/bin/env bash
# Lance le frontend Streamlit Train-vs-Pre-train (Linux / macOS).
#
# - Crée l'environnement virtuel (.venv) et installe les dépendances au
#   premier lancement si besoin.
# - Utilise toujours le Python du venv : pas besoin d'activer un venv à la main.
#
# Prérequis : le backend FastAPI doit tourner sur http://127.0.0.1:8000.
#
# Usage :  ./run.sh

set -euo pipefail
cd "$(dirname "$0")"

VENV=".venv"
PY="$VENV/bin/python"

if [ ! -x "$PY" ]; then
  echo "Création de l'environnement virtuel (.venv)..."
  python3 -m venv "$VENV"
  "$VENV/bin/pip" install --upgrade pip
  "$VENV/bin/pip" install -r requirements.txt
fi

echo "Lancement du frontend sur http://localhost:8501 (backend API requis sur :8000)"
exec "$PY" -m streamlit run streamlit_app.py --server.headless=true --server.port 8501