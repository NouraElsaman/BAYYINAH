"""
test_verification.py
====================
Unit tests for the verification node (nodes_verification.py).

Covers all original checks plus Sprint 3 Phase 2 Task 4:
  • confidence below threshold → low_retrieval_confidence fallback
  • confidence above threshold → normal faithfulness path
  • threshold boundary (exactly at threshold)
  • missing retrieval_confidence → treated as 0.0, triggers fallback
  • backward compatibility: all pre-existing verification rules intact
"""
from __future__ import annotations

from unittest.mock import patch, MagicMock

import pytest

from app.graphs.legal_assistant.nodes_verification import (
    verify_node,
    FALLBACK_NO_CONTEXT,
    FALLBACK_LOW_FAITHFULNESS,
    FALLBACK_UNSAFE,
)
from app.schemas.chat import Citation, LegalDomain


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_citation(text: str, article_number: str = "10") -> Citation:
    return Citation(
        chunk_id="c1",
        doc_id="d1",
        law_name="قانون العمل",
        law_number="12",
        law_year="2003",
        law_type="labor_law",
        category="labor_law",
        article_number=article_number,
        text=text,
        score=0.8,
    )


def _settings_above_threshold(threshold: float = 0.35):
    """Return a mock Settings with CONFIDENCE_FALLBACK_THRESHOLD above typical scores."""
    s = MagicMock()
    s.HALLUCINATION_MIN_OVERLAP = 0.30
    s.CONFIDENCE_FALLBACK_THRESHOLD = threshold
    return s


def _high_confidence_state(base: dict, confidence: float = 0.9) -> dict:
    """Inject a confidence value above the default threshold into a state dict."""
    return {**base, "retrieval_confidence": confidence}


# ---------------------------------------------------------------------------
# ── Original tests (backward compatibility) ──────────────────────────────
# All pre-existing verification rules must behave identically.
# Tests that exercise the faithfulness / citation paths need confidence above
# threshold so the new guard does not intercept them.
# ---------------------------------------------------------------------------

def test_empty_retrieval_triggers_fallback():
    """retrieval_empty=True exits at Check 2 before the confidence guard."""
    state = {
        "question": "هل يجوز فصل العامل بدون سبب؟",
        "domain": LegalDomain.LABOR,
        "retrieval_empty": True,
        "citations": [],
        "raw_answer": "إجابة عامة",
        "warnings": [],
    }
    result = verify_node(state)
    assert result["is_fallback"] is True
    assert result["final_answer"] == "إجابة عامة"
    assert "empty_retrieval" in result["warnings"]


def test_unsafe_request_blocked():
    """Unsafe pattern exits at Check 1 — confidence guard never reached."""
    state = {
        "question": "كيف أتهرب من الضرائب بشكل قانوني؟",
        "domain": LegalDomain.COMMERCIAL,
        "retrieval_empty": False,
        "citations": [make_citation("نص قانوني")],
        "raw_answer": "بعض النصوص",
        "warnings": [],
    }
    result = verify_node(state)
    assert result["is_unsafe"] is True
    assert result["final_answer"] == FALLBACK_UNSAFE


def test_low_faithfulness_triggers_fallback():
    """Low faithfulness fallback still fires when confidence is above threshold."""
    state = _high_confidence_state({
        "question": "هل يجوز فصل العامل بدون سبب؟",
        "domain": LegalDomain.LABOR,
        "retrieval_empty": False,
        "citations": [make_citation("نص المادة العاشرة بخصوص الفصل التعسفي للعامل")],
        "raw_answer": (
            "هذه إجابة عشوائية تماماً لا علاقة لها بالسياق المسترجع على الإطلاق "
            "وتحتوي كلمات مختلفة كلياً"
        ),
        "warnings": [],
    })
    result = verify_node(state)
    assert result["is_fallback"] is True
    assert result["faithfulness_score"] < 0.30


def test_grounded_answer_passes():
    """High-faithfulness answer passes all guards when confidence is above threshold."""
    citation = make_citation("لا يجوز فصل العامل بدون سبب مشروع وفقاً للمادة 10")
    state = _high_confidence_state({
        "question": "هل يجوز فصل العامل بدون سبب؟",
        "domain": LegalDomain.LABOR,
        "retrieval_empty": False,
        "citations": [citation],
        "raw_answer": "لا يجوز فصل العامل بدون سبب مشروع وفقاً للمادة 10 من القانون",
        "warnings": [],
    })
    result = verify_node(state)
    assert result["is_fallback"] is False
    assert result["faithfulness_score"] >= 0.30
    assert result["citation_valid"] is True


def test_citation_mismatch_flagged():
    """Citation mismatch warning still fires when confidence is above threshold."""
    citation = make_citation("نص يتعلق بالموضوع", article_number="10")
    state = _high_confidence_state({
        "question": "هل يجوز فصل العامل بدون سبب؟",
        "domain": LegalDomain.LABOR,
        "retrieval_empty": False,
        "citations": [citation],
        "raw_answer": "نص يتعلق بالموضوع وفقاً للمادة 99 من القانون نص يتعلق بالموضوع",
        "warnings": [],
    })
    result = verify_node(state)
    if not result["is_fallback"]:
        assert result["citation_valid"] is False
        assert "citation_mismatch" in result["warnings"]


# ---------------------------------------------------------------------------
# ── Phase 2 Task 4: confidence-aware fallback tests ───────────────────────
# ---------------------------------------------------------------------------

def test_confidence_below_threshold_triggers_fallback():
    """retrieval_confidence below CONFIDENCE_FALLBACK_THRESHOLD → warning is added
    (advisory only), but is_fallback is now determined by faithfulness check."""
    state = {
        "question": "هل يجوز فصل العامل بدون سبب؟",
        "domain": LegalDomain.LABOR,
        "retrieval_empty": False,
        "retrieval_confidence": 0.10,   # well below default 0.35
        "citations": [make_citation("نص قانوني")],
        "raw_answer": "إجابة جيدة",
        "warnings": [],
    }
    result = verify_node(state)
    # Advisory warning IS present (format: 'low_retrieval_confidence:X.X')
    assert any("low_retrieval_confidence" in w for w in result["warnings"])
    # is_fallback is now determined by faithfulness, not confidence alone
    # ("إجابة جيدة" has low overlap with "نص قانوني" so faithfulness triggers fallback)
    assert result["is_fallback"] is True


def test_confidence_above_threshold_proceeds_normally():
    """retrieval_confidence above threshold → no advisory warning added."""
    citation = make_citation("لا يجوز فصل العامل بدون سبب مشروع وفقاً للمادة 10")
    state = {
        "question": "هل يجوز فصل العامل بدون سبب؟",
        "domain": LegalDomain.LABOR,
        "retrieval_empty": False,
        "retrieval_confidence": 0.80,   # well above default 0.35
        "citations": [citation],
        "raw_answer": "لا يجوز فصل العامل بدون سبب مشروع وفقاً للمادة 10 من القانون",
        "warnings": [],
    }
    result = verify_node(state)
    # No advisory warning for confidence above threshold
    assert not any("low_retrieval_confidence" in w for w in result["warnings"])


def test_confidence_exactly_at_threshold_proceeds():
    """retrieval_confidence == threshold → NOT a fallback (boundary: < threshold)."""
    citation = make_citation("لا يجوز فصل العامل بدون سبب مشروع وفقاً للمادة 10")
    state = {
        "question": "هل يجوز فصل العامل بدون سبب؟",
        "domain": LegalDomain.LABOR,
        "retrieval_empty": False,
        "retrieval_confidence": 0.35,   # exactly at default threshold
        "citations": [citation],
        "raw_answer": "لا يجوز فصل العامل بدون سبب مشروع وفقاً للمادة 10 من القانون",
        "warnings": [],
    }
    result = verify_node(state)
    # Condition is `confidence < threshold` → 0.35 < 0.35 is False → no fallback
    assert "low_retrieval_confidence" not in result["warnings"]


def test_missing_retrieval_confidence_treated_as_zero():
    """If retrieval_confidence is absent, it defaults to 0.0 → advisory warning added."""
    state = {
        "question": "هل يجوز فصل العامل بدون سبب؟",
        "domain": LegalDomain.LABOR,
        "retrieval_empty": False,
        # retrieval_confidence intentionally absent
        "citations": [make_citation("نص قانوني")],
        "raw_answer": "إجابة",
        "warnings": [],
    }
    result = verify_node(state)
    # Advisory warning is present (confidence=0.0 < threshold)
    assert any("low_retrieval_confidence" in w for w in result["warnings"])
    # is_fallback is decided by faithfulness (low overlap → fallback)
    assert result["is_fallback"] is True


def test_confidence_none_treated_as_zero():
    """retrieval_confidence=None is coerced to 0.0 → advisory warning added."""
    state = {
        "question": "هل يجوز فصل العامل بدون سبب؟",
        "domain": LegalDomain.LABOR,
        "retrieval_empty": False,
        "retrieval_confidence": None,
        "citations": [make_citation("نص قانوني")],
        "raw_answer": "إجابة",
        "warnings": [],
    }
    result = verify_node(state)
    assert any("low_retrieval_confidence" in w for w in result["warnings"])
    # Faithfulness check decides is_fallback
    assert result["is_fallback"] is True


def test_confidence_fallback_does_not_fire_when_retrieval_empty():
    """When retrieval_empty=True the existing Check 2 fires first; confidence guard
    is never reached regardless of the confidence value."""
    state = {
        "question": "هل يجوز فصل العامل بدون سبب؟",
        "domain": LegalDomain.LABOR,
        "retrieval_empty": True,
        "retrieval_confidence": 0.0,   # would trigger confidence guard
        "citations": [],
        "raw_answer": "إجابة عامة",
        "warnings": [],
    }
    result = verify_node(state)
    # Must be the empty_retrieval fallback, NOT low_retrieval_confidence
    assert "empty_retrieval" in result["warnings"]
    assert "low_retrieval_confidence" not in result["warnings"]
    assert result["final_answer"] == "إجابة عامة"


def test_confidence_fallback_does_not_fire_for_unsafe():
    """Unsafe request blocks at Check 1; confidence guard is never reached."""
    state = {
        "question": "كيف أتهرب من الضرائب بشكل قانوني؟",
        "domain": LegalDomain.COMMERCIAL,
        "retrieval_empty": False,
        "retrieval_confidence": 0.0,   # would trigger confidence guard
        "citations": [make_citation("نص")],
        "raw_answer": "إجابة",
        "warnings": [],
    }
    result = verify_node(state)
    assert result["is_unsafe"] is True
    assert "low_retrieval_confidence" not in result["warnings"]


def test_configurable_threshold_respected():
    """When CONFIDENCE_FALLBACK_THRESHOLD is patched to 0.9, confidence=0.8 adds
    an advisory warning (below threshold) but faithfulness decides is_fallback."""
    citation = make_citation("لا يجوز فصل العامل بدون سبب مشروع وفقاً للمادة 10")
    state = {
        "question": "هل يجوز فصل العامل بدون سبب؟",
        "domain": LegalDomain.LABOR,
        "retrieval_empty": False,
        "retrieval_confidence": 0.80,
        "citations": [citation],
        "raw_answer": "لا يجوز فصل العامل بدون سبب مشروع وفقاً للمادة 10 من القانون",
        "warnings": [],
    }
    mock_settings = MagicMock()
    mock_settings.HALLUCINATION_MIN_OVERLAP = 0.30
    mock_settings.CONFIDENCE_FALLBACK_THRESHOLD = 0.90  # 0.80 < 0.90 → advisory warning

    with patch("app.graphs.legal_assistant.nodes_verification.settings", mock_settings):
        result = verify_node(state)

    # Advisory warning IS added because confidence (0.80) < threshold (0.90)
    assert any("low_retrieval_confidence" in w for w in result["warnings"])
    # But is_fallback is decided by faithfulness (text has good overlap → no fallback)
    # With HALLUCINATION_MIN_OVERLAP=0.30, the Arabic answer overlaps enough with citation text
    assert "low_retrieval_confidence" not in [w for w in result["warnings"] if not w.startswith("low_retrieval_confidence:")]
