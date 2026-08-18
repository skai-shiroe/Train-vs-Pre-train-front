# Lance le frontend Streamlit Train-vs-Pre-train (Windows).
#
# - Crée l'environnement virtuel (.venv) et installe les dépendances au
#   premier lancement si besoin.
# - Utilise toujours le Python du venv : pas besoin d'activer un venv à la main
#   ni que `streamlit` soit sur le PATH.
#
# Prérequis : le backend FastAPI doit tourner sur http://127.0.0.1:8000.
#
# Usage :  .\run.ps1

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

$VenvPython = Join-Path $Root ".venv\Scripts\python.exe"

if (-not (Test-Path $VenvPython)) {
    Write-Host "Création de l'environnement virtuel (.venv)..."
    python -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw "Échec de la création du venv." }
    Write-Host "Installation des dépendances (requirements.txt)..."
    & $VenvPython -m pip install --upgrade pip
    & $VenvPython -m pip install -r requirements.txt
    if ($LASTEXITCODE -ne 0) { throw "Échec de l'installation des dépendances." }
}

Write-Host "Lancement du frontend sur http://localhost:8501 (backend API requis sur :8000)"
& $VenvPython -m streamlit run streamlit_app.py --server.headless=true --server.port 8501