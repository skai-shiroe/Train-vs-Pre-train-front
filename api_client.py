"""Client HTTP pour l'API backend Train-vs-Pre-train (FastAPI).

Chaque fonction appelle un endpoint de l'API et renvoie une structure Python
simple (``dict`` / ``list``). En cas de problème (serveur injoignable, erreur
applicative, modèle indisponible) elle lève une :class:`ApiError` dont le
message est directement affichable dans l'interface.
"""

from __future__ import annotations

import time
from typing import Any

import requests

import monitoring

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
    """Exécute une requête HTTP, normalise les erreurs et journalise la télémétrie.

    Chaque appel — succès comme échec — est mesuré (latence totale) puis enregistré
    dans le module :mod:`monitoring` pour alimenter la page « Monitoring ».
    """
    url = f"{base_url.rstrip('/')}{path}"
    start = time.perf_counter()
    try:
        resp = requests.request(method, url, timeout=REQUEST_TIMEOUT, **kwargs)
    except requests.RequestException as exc:
        duration_ms = (time.perf_counter() - start) * 1000
        message = (
            f"Impossible de joindre l'API sur {base_url}. "
            f"Vérifiez que le backend uvicorn est démarré. Détail : {exc}"
        )
        monitoring.record(
            method=method,
            path=path,
            status_code=None,
            ok=False,
            duration_ms=duration_ms,
            params=_request_params(path, **kwargs),
            error=message,
        )
        raise ApiError(message) from exc

    duration_ms = (time.perf_counter() - start) * 1000
    status_code = resp.status_code

    if resp.status_code >= 400:
        detail = _extract_detail(resp)
        monitoring.record(
            method=method,
            path=path,
            status_code=status_code,
            ok=False,
            duration_ms=duration_ms,
            model=_request_model(path, **kwargs),
            params=_request_params(path, **kwargs),
            error=detail,
        )
        raise ApiError(detail, status_code=status_code)

    try:
        body = resp.json()
    except ValueError as exc:
        message = f"Réponse non JSON reçue de {url}."
        monitoring.record(
            method=method,
            path=path,
            status_code=status_code,
            ok=False,
            duration_ms=duration_ms,
            params=_request_params(path, **kwargs),
            error=message,
        )
        raise ApiError(message) from exc

    _record_success(method, path, status_code, duration_ms, body, kwargs)
    return body


# ---------------------------------------------------------------------------
# Télémétrie : extrapolation de métriques depuis la requête / la réponse
# ---------------------------------------------------------------------------
def _request_model(path: str, **kwargs: Any) -> str | None:
    """Extrait le nom du modèle depuis la requête (body JSON ou query params)."""
    body = kwargs.get("json") or {}
    return body.get("model") or (kwargs.get("params") or {}).get("model")


def _request_params(path: str, **kwargs: Any) -> dict[str, Any]:
    """Params pertinents à journaliser (modèle, tokens, nom de fichier…)."""
    body = kwargs.get("json") or {}
    params = dict(kwargs.get("params") or {})
    text = body.get("text")
    if text is not None:
        params["_input_chars"] = len(text)
    for key in ("model", "filename", "max_new_tokens", "extracted_chars"):
        if key in body:
            params[key] = body[key]
    return params


def _record_success(
    method: str,
    path: str,
    status_code: int,
    duration_ms: float,
    body: Any,
    kwargs: dict[str, Any],
) -> None:
    """Extrait les métriques d'un appel réussi et les journalise."""
    params = _request_params(path, **kwargs)
    input_chars = params.get("_input_chars")

    if path == "/summarize":
        monitoring.record(
            method=method, path=path, status_code=status_code, ok=True,
            duration_ms=duration_ms,
            model=body.get("model"),
            inference_ms=_ms(body.get("inference_seconds")),
            input_chars=input_chars,
            output_chars=len(body.get("summary", "")),
            params=params,
            summary_preview=body.get("summary"),
        )
    elif path == "/compare":
        t5 = body.get("t5") or {}
        scratch = body.get("scratch") or {}
        monitoring.record(
            method=method, path=path, status_code=status_code, ok=True,
            duration_ms=duration_ms,
            model="compare",
            inference_ms=_ms(t5.get("inference_seconds")),
            input_chars=input_chars,
            output_chars=len(t5.get("summary", "")) + len(scratch.get("summary", "")),
            params=params,
            summary_preview=t5.get("summary"),
        )
    elif path == "/summarize-file":
        monitoring.record(
            method=method, path=path, status_code=status_code, ok=True,
            duration_ms=duration_ms,
            model=body.get("model"),
            inference_ms=_ms(body.get("inference_seconds")),
            input_chars=body.get("extracted_chars"),
            output_chars=len(body.get("summary", "")),
            extracted_chars=body.get("extracted_chars"),
            params={
                **params,
                "filename": body.get("filename"),
                "model": body.get("model"),
            },
            summary_preview=body.get("summary"),
        )
    else:
        # /health et /models : on journalise la latence, sans inférence.
        monitoring.record(
            method=method, path=path, status_code=status_code, ok=True,
            duration_ms=duration_ms,
            params=params,
        )


def _ms(value: Any) -> float | None:
    """Convertit une durée en secondes (API) en millisecondes. ``None`` si absente."""
    if value is None:
        return None
    try:
        return round(float(value) * 1000, 3)
    except (TypeError, ValueError):
        return None


def get_health(base_url: str) -> dict[str, Any]:
    """``GET /health`` — vérifie que l'API répond."""
    return _request("GET", base_url, "/health")


def get_health_detail(base_url: str) -> dict[str, Any]:
    """``GET /health/detail`` — diagnostic approfondi (uptime, mémoire, modèles…)."""
    return _request("GET", base_url, "/health/detail")


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
