"""Télémétrie locale du frontend : journal persistant de chaque appel au backend.

Contrairement aux données temps réel (`/health`, `/models`), ce module conserve
un **historique durable sur disque** (fichier JSON) de toutes les requêtes émises
par ce frontend : endpoint, modèle, code HTTP, latence totale, temps d'inférence
serviteur, tailles d'entrée/sortie et aperçu de la réponse.

Ce module alimente la page « Monitoring » et n'a aucune dépendance vis-à-vis de
Streamlit : il peut être utilisé, et testé, de façon isolée.

Chaque enregistrement est écrit **atomiquement** (fichier temporaire puis
renommage) pour ne jamais corrompre l'historique en cas de crash. Un échec
d'écriture n'empêche jamais l'application de fonctionner normalement.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Emplacement du fichier d'historique (ignoré par Git, voir .gitignore).
DATA_DIR = Path(__file__).resolve().parent / ".metrics"
DATA_FILE = DATA_DIR / "requests.json"

# Garde-fou : on ne conserve jamais plus de ce nombre d'enregistrements.
MAX_RECORDS = 5000


def record(
    *,
    method: str,
    path: str,
    status_code: int | None,
    ok: bool,
    duration_ms: float,
    model: str | None = None,
    inference_ms: float | None = None,
    input_chars: int | None = None,
    output_chars: int | None = None,
    extracted_chars: int | None = None,
    params: dict[str, Any] | None = None,
    summary_preview: str | None = None,
    error: str | None = None,
) -> None:
    """Ajoute un enregistrement au journal, en écrivant atomiquement sur disque.

    Args:
        method: Verbe HTTP (GET / POST).
        path: Route appelée (ex. ``/summarize``).
        status_code: Code HTTP renvoyé (``None`` si injoignable).
        ok: ``True`` si l'appel a abouti (code < 400).
        duration_ms: Latence totale mesurée côté client (aller-retour).
        model: Nom du modèle (``t5``, ``scratch``) ou ``compare``.
        inference_ms: Temps d'inférence serveur (champ ``inference_seconds``).
        input_chars: Longueur (caractères) du texte d'entrée.
        output_chars: Longueur (caractères) du/des résumé(s) produits.
        extracted_chars: Nombre de caractères extraits (endpoint fichier).
        params: Paramètres de la requête (modèle, tokens, etc.).
        summary_preview: Aperçu de la réponse (résumé) pour inspection.
        error: Message d'erreur éventuel.
    """
    entry: dict[str, Any] = {
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
        "method": method,
        "path": path,
        "status_code": status_code,
        "ok": bool(ok),
        "duration_ms": round(float(duration_ms), 3),
        "model": model,
        "inference_ms": inference_ms,
        "input_chars": input_chars,
        "output_chars": output_chars,
        "extracted_chars": extracted_chars,
        "params": params or {},
        "summary_preview": summary_preview,
        "error": error,
    }
    history = _read()
    history.append(entry)
    if len(history) > MAX_RECORDS:
        history = history[-MAX_RECORDS:]
    _write(history)


def _read() -> list[dict[str, Any]]:
    """Lit l'historique depuis le disque (retourne ``[]`` s'il n'existe pas)."""
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        return data if isinstance(data, list) else []
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def _write(history: list[dict[str, Any]]) -> None:
    """Écrit l'historique atomiquement. Ne lève jamais (télémétrie non bloquante)."""
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        tmp = DATA_FILE.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(history, fh, ensure_ascii=False, indent=1)
        os.replace(tmp, DATA_FILE)
    except OSError:
        # La télémétrie ne doit jamais faire échouer l'application.
        pass


def all_records() -> list[dict[str, Any]]:
    """Retourne la liste complète des enregistrements (du plus ancien au plus récent)."""
    return _read()


def clear() -> None:
    """Vide complètement l'historique (réinitialise le journal)."""
    _write([])


def dump(records: list[dict[str, Any]]) -> str:
    """Sérialise l'historique en JSON (pour export)."""
    return json.dumps(records, ensure_ascii=False, indent=1)