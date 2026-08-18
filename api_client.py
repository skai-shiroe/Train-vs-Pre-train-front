"""Client HTTP pour l'API backend Train-vs-Pre-train (FastAPI).

Chaque fonction appelle un endpoint de l'API et renvoie une structure Python
simple (``dict`` / ``list``). En cas de problème (serveur injoignable, erreur
applicative, modèle indisponible) elle lève une :class:`ApiError` dont le
message est directement affichable dans l'interface.
"""

from __future__ import annotations

from typing import Any

import requests

#: URL par défaut du backend FastAPI (uvicorn sur le port 8000).
DEFAULT_BASE_URL = "http://127.0.0.1:8000"

#: Timeout global (secondes). L'inférence CPU en beam search peut être lente.
REQUEST_TIMEOUT = 180

#: Modèles exposés par l'API.
MODELS = ("t5", "scratch")

#: Libellés lisibles pour l'interface.
MODEL_LABELS = {
    "t5": "T5 fine-tuné (baseline pré-entraînée)",
    "scratch": "Transformer from scratch",
}

#: Icônes Material affichées pour chaque modèle.
MODEL_ICONS = {
    "t5": ":material/memory:",
    "scratch": ":material/tune:",
}

#: Description courte de chaque modèle.
MODEL_SHORT_DESC = {
    "t5": "Modèle pré-entraîné (t5-small) fine-tuné sur le corpus XSum.",
    "scratch": "Transformer encodeur-décodeur entraîné entièrement from scratch.",
}


class ApiError(Exception):
    """Erreur remontée à l'interface, avec un message en français lisible."""

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        payload: Any | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.payload = payload


def _extract_detail(resp: requests.Response) -> str:
    """Extrait le message d'erreur renvoyé par FastAPI (champ ``detail``)."""
    try:
        data = resp.json()
    except ValueError:
        return f"Erreur API ({resp.status_code}) : {resp.text[:300]}"

    if isinstance(data, dict) and "detail" in data:
        detail = data["detail"]
        if isinstance(detail, str):
            return f"Erreur API ({resp.status_code}) : {detail}"
        if isinstance(detail, list):
            messages = []
            for item in detail:
                if isinstance(item, dict):
                    loc = ".".join(str(p) for p in item.get("loc", []))
                    msg = item.get("msg", "erreur de validation")
                    messages.append(f"{loc} : {msg}" if loc else msg)
                else:
                    messages.append(str(item))
            return "Erreur de validation : " + "; ".join(messages)
        return f"Erreur API ({resp.status_code}) : {detail}"
    return f"Erreur API ({resp.status_code}) : {resp.text[:300]}"


def _request(method: str, base_url: str, path: str, **kwargs: Any) -> Any:
    """Exécute une requête HTTP et normalise les erreurs."""
    url = f"{base_url.rstrip('/')}{path}"
    try:
        resp = requests.request(method, url, timeout=REQUEST_TIMEOUT, **kwargs)
    except requests.RequestException as exc:
        raise ApiError(
            f"Impossible de joindre l'API sur {base_url}. "
            f"Vérifiez que le backend uvicorn est démarré. Détail : {exc}"
        ) from exc

    if resp.status_code >= 400:
        raise ApiError(_extract_detail(resp), status_code=resp.status_code)

    try:
        return resp.json()
    except ValueError as exc:
        raise ApiError(f"Réponse non JSON reçue de {url}.") from exc


def get_health(base_url: str) -> dict[str, Any]:
    """``GET /health`` — vérifie que l'API répond."""
    return _request("GET", base_url, "/health")


def get_models(base_url: str) -> list[dict[str, Any]]:
    """``GET /models`` — liste les modèles et leur état."""
    return _request("GET", base_url, "/models")


def summarize(
    base_url: str,
    text: str,
    model: str,
    max_new_tokens: int,
) -> dict[str, Any]:
    """``POST /summarize`` — résume un texte avec un modèle donné."""
    if model not in MODELS:
        raise ApiError(f"Modèle inconnu : {model!r}. Attendu : {', '.join(MODELS)}.")
    return _request(
        "POST",
        base_url,
        "/summarize",
        json={"text": text, "model": model, "max_new_tokens": max_new_tokens},
    )


def compare(base_url: str, text: str, max_new_tokens: int) -> dict[str, Any]:
    """``POST /compare`` — résume un texte avec les deux modèles."""
    return _request(
        "POST",
        base_url,
        "/compare",
        json={"text": text, "max_new_tokens": max_new_tokens},
    )


def summarize_file(
    base_url: str,
    filename: str,
    content: bytes,
    model: str,
    max_new_tokens: int,
) -> dict[str, Any]:
    """``POST /summarize-file`` — résume le contenu d'un fichier uploadé."""
    if model not in MODELS:
        raise ApiError(f"Modèle inconnu : {model!r}. Attendu : {', '.join(MODELS)}.")
    files = {"file": (filename, content)}
    params = {"model": model, "max_new_tokens": max_new_tokens}
    return _request("POST", base_url, "/summarize-file", files=files, params=params)
