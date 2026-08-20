"""Tests unitaires des helpers d'affichage (:mod:`ui`) — mode clair/sombre compris.

Lancement :
    pytest tests/test_ui.py
"""

from __future__ import annotations

import pandas as pd
import pytest

from ui import (
    comparison_table,
    export_comparison,
    summary_metrics,
    text_stats,
    token_overlap,
)


def test_text_stats():
    stats = text_stats("Hello world. Another sentence here!")
    assert stats["words"] == 5
    assert stats["sentences"] == 2
    assert stats["chars"] == len("Hello world. Another sentence here!")


def test_summary_metrics_proportions():
    source = "a b c d e f g h"
    summary = "a b c"
    m = summary_metrics(summary, source)
    assert m["words"] == 3
    assert m["pct_source_words"] == pytest.approx(37.5)
    assert m["pct_source_chars"] is not None


def test_summary_metrics_empty_source():
    m = summary_metrics("hello", "")
    assert m["pct_source_words"] is None


def test_token_overlap_identical():
    assert token_overlap("The cat sat on the mat", "the cat sat on the mat") == pytest.approx(1.0)


def test_token_overlap_disjoint():
    assert token_overlap("hello world", "foo bar baz") == pytest.approx(0.0)


def test_token_overlap_empty():
    assert token_overlap("", "anything") == 0.0


def test_comparison_table_columns():
    t5 = {"summary": "A short summary.", "inference_seconds": 1.2}
    scratch = {"summary": "A rather longer summary here.", "inference_seconds": 3.4}
    df = comparison_table("The source article text.", t5, scratch)
    assert isinstance(df, pd.DataFrame)
    assert list(df.columns) == ["Métrique", "T5", "Scratch"]
    # Contient au moins les lignes attendues.
    metrics = set(df["Métrique"])
    assert "Mots" in metrics and "Temps d'inférence" in metrics


def test_comparison_table_scratch_none():
    t5 = {"summary": "Only T5 available.", "inference_seconds": 0.9}
    df = comparison_table("The source.", t5, None)
    assert "Scratch" in df.columns
    # Pas de crash avec un modèle absent.


def test_export_comparison_content():
    t5 = {"summary": "Hello.", "inference_seconds": 1.0}
    scratch = None
    out = export_comparison("Source text.", t5, scratch)
    assert "# Comparaison des résumés" in out
    assert "Source text." in out
    assert "Hello." in out
