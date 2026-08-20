"""Tests unitaires du journal de télémétrie :mod:`monitoring` (aucune dépendance Streamlit)."""

from __future__ import annotations

import json

import pytest

import monitoring


@pytest.fixture
def empty_history(tmp_path, monkeypatch):
    """Isolée sur un fichier temporaire pour ne pas toucher la vraie donnée."""
    monkeypatch.setattr(monitoring, "DATA_DIR", tmp_path)
    monkeypatch.setattr(monitoring, "DATA_FILE", tmp_path / "requests.json")
    monitoring.clear()
    return tmp_path


def test_record_then_read(empty_history):
    monitoring.record(
        method="POST", path="/summarize", status_code=200, ok=True,
        duration_ms=1500.0, model="t5", inference_ms=1200.0,
        input_chars=500, output_chars=80,
    )
    records = monitoring.all_records()
    assert len(records) == 1
    assert records[0]["model"] == "t5"
    assert records[0]["ok"] is True


def test_read_empty(empty_history):
    assert monitoring.all_records() == []


def test_clear(empty_history):
    monitoring.record(method="GET", path="/health", status_code=200, ok=True,
                      duration_ms=10.0)
    monitoring.clear()
    assert monitoring.all_records() == []


def test_dump(empty_history):
    monitoring.record(method="GET", path="/health", status_code=200, ok=True,
                      duration_ms=5.0)
    blob = monitoring.dump(monitoring.all_records())
    parsed = json.loads(blob)
    assert isinstance(parsed, list) and len(parsed) == 1
