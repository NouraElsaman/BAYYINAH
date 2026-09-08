"""
test_citation_node.py
=====================
Unit tests for the Citation Agent node:
  backend/app/graphs/legal_assistant/nodes_citation.py

Coverage
--------
1. Duplicate removal — same chunk_id appears twice, only first kept.
2. Order preservation — ranking order is never altered.
3. Token budget trimming — per-citation text capped at CITATION_MAX_TEXT_TOKENS.
4. Total budget enforcement — citations that would push total over CITATION_MAX_TOKENS dropped.
5. Metadata preservation — score, law_name, article_number, law_number, law_year,
   law_type, category all survive intact after dedup + trimming.
6. Empty citation list — returns citations=[], context_tokens=0.
7. No-op on already-short texts — texts within budget pass through unmodified.
8. context_tokens stored in state.
9. Ellipsis appended when text is trimmed.
"""
from __future__ import annotations

from unittest.mock import patch, MagicMock

import pytest

from app.schemas.chat import Citation
from app.graphs.legal_assistant.nodes_citation import (
    citation_node,
    _dedup_citations,
    _trim_text,
    _token_count,
    _apply_token_budget,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_citation(
    chunk_id: str = "c1",
    text: str = "نص قانوني",
    score: float = 0.8,
    article_number: str | None = "10",
    law_name: str = "قانون العمل",
    law_number: str | None = "12",
    law_year: str | None = "2003",
    law_type: str | None = "labor",
    category: str | None = "labor_law",
) -> Citation:
    return Citation(
        chunk_id=chunk_id,
        doc_id=f"doc_{chunk_id}",
        law_name=law_name,
        law_number=law_number,
        law_year=law_year,
        law_type=law_type,
        category=category,
        article_number=article_number,
        text=text,
        score=score,
    )


def _mock_settings(max_tokens: int = 3000, max_text_tokens: int = 400):
    s = MagicMock()
    s.CITATION_MAX_TOKENS = max_tokens
    s.CITATION_MAX_TEXT_TOKENS = max_text_tokens
    return s


# ---------------------------------------------------------------------------
# Unit tests for internal helpers
# ---------------------------------------------------------------------------

class TestTokenCount:
    def test_empty_string(self):
        assert _token_count("") == 0

    def test_single_word(self):
        assert _token_count("كلمة") == 1

    def test_multiple_words(self):
        assert _token_count("كلمة واحدة اثنتان ثلاث") == 4


class TestTrimText:
    def test_no_trim_needed(self):
        text = "كلمة واحدة اثنتان"
        assert _trim_text(text, max_tokens=10) == text

    def test_exact_limit(self):
        text = "a b c d e"
        assert _trim_text(text, max_tokens=5) == text

    def test_trim_adds_ellipsis(self):
        text = "a b c d e f g"
        result = _trim_text(text, max_tokens=3)
        assert result == "a b c …"
        assert _token_count(result.replace(" …", "")) == 3

    def test_max_tokens_zero_returns_empty(self):
        assert _trim_text("some text here", max_tokens=0) == ""

    def test_already_within_budget(self):
        text = "short"
        assert _trim_text(text, max_tokens=400) == "short"


class TestDedupCitations:
    def test_no_duplicates(self):
        citations = [_make_citation("c1"), _make_citation("c2")]
        result = _dedup_citations(citations)
        assert [c.chunk_id for c in result] == ["c1", "c2"]

    def test_exact_duplicate_removed(self):
        citations = [
            _make_citation("c1", score=0.9),
            _make_citation("c1", score=0.5),  # duplicate
        ]
        result = _dedup_citations(citations)
        assert len(result) == 1
        assert result[0].score == 0.9  # first occurrence kept

    def test_multiple_duplicates(self):
        citations = [
            _make_citation("c1"),
            _make_citation("c2"),
            _make_citation("c1"),  # dup
            _make_citation("c3"),
            _make_citation("c2"),  # dup
        ]
        result = _dedup_citations(citations)
        assert [c.chunk_id for c in result] == ["c1", "c2", "c3"]

    def test_empty_list(self):
        assert _dedup_citations([]) == []


class TestApplyTokenBudget:
    def test_all_fit_within_budget(self):
        citations = [_make_citation(f"c{i}", text="a b c") for i in range(3)]
        selected, total = _apply_token_budget(citations, max_text_tokens=10, max_total_tokens=100)
        assert len(selected) == 3
        assert total == 9  # 3 words * 3 citations

    def test_drops_citation_over_total_budget(self):
        c1 = _make_citation("c1", text=" ".join(["كلمة"] * 10))
        c2 = _make_citation("c2", text=" ".join(["كلمة"] * 10))
        # Budget only allows 15 tokens total; c2 (10) would push to 20
        selected, total = _apply_token_budget([c1, c2], max_text_tokens=400, max_total_tokens=15)
        assert len(selected) == 1
        assert selected[0].chunk_id == "c1"
        assert total == 10

    def test_per_citation_text_trimmed(self):
        long_text = " ".join(["word"] * 20)
        c = _make_citation("c1", text=long_text)
        selected, total = _apply_token_budget([c], max_text_tokens=5, max_total_tokens=3000)
        assert len(selected) == 1
        assert _token_count(selected[0].text.replace(" …", "")) == 5
        assert "…" in selected[0].text

    def test_empty_input(self):
        selected, total = _apply_token_budget([], max_text_tokens=400, max_total_tokens=3000)
        assert selected == []
        assert total == 0


# ---------------------------------------------------------------------------
# citation_node integration tests
# ---------------------------------------------------------------------------

class TestCitationNode:

    # -----------------------------------------------------------------------
    # 6. Empty citation list
    # -----------------------------------------------------------------------
    def test_empty_citations_returns_zero(self):
        state = {"question": "سؤال؟", "citations": []}
        result = citation_node(state)
        assert result["citations"] == []
        assert result["context_tokens"] == 0

    def test_missing_citations_key_handled(self):
        """state without 'citations' key should behave like empty list."""
        state = {"question": "سؤال؟"}
        result = citation_node(state)
        assert result["citations"] == []
        assert result["context_tokens"] == 0

    # -----------------------------------------------------------------------
    # 1. Duplicate removal
    # -----------------------------------------------------------------------
    def test_duplicates_removed(self):
        citations = [
            _make_citation("c1", text="نص أول", score=0.9),
            _make_citation("c2", text="نص ثاني", score=0.8),
            _make_citation("c1", text="نص مكرر", score=0.5),  # dup
        ]
        state = {"question": "سؤال؟", "citations": citations}
        with patch("app.graphs.legal_assistant.nodes_citation.get_settings",
                   return_value=_mock_settings()):
            result = citation_node(state)
        ids = [c.chunk_id for c in result["citations"]]
        assert ids.count("c1") == 1
        assert len(result["citations"]) == 2

    # -----------------------------------------------------------------------
    # 2. Order preservation
    # -----------------------------------------------------------------------
    def test_ranking_order_preserved(self):
        citations = [
            _make_citation("c1", score=0.9),
            _make_citation("c2", score=0.7),
            _make_citation("c3", score=0.5),
        ]
        state = {"question": "سؤال؟", "citations": citations}
        with patch("app.graphs.legal_assistant.nodes_citation.get_settings",
                   return_value=_mock_settings()):
            result = citation_node(state)
        assert [c.chunk_id for c in result["citations"]] == ["c1", "c2", "c3"]
        assert [c.score for c in result["citations"]] == [0.9, 0.7, 0.5]

    # -----------------------------------------------------------------------
    # 3. Token budget trimming (per-citation)
    # -----------------------------------------------------------------------
    def test_text_trimmed_to_max_text_tokens(self):
        long_text = " ".join(["كلمة"] * 50)
        c = _make_citation("c1", text=long_text)
        state = {"question": "سؤال؟", "citations": [c]}
        with patch("app.graphs.legal_assistant.nodes_citation.get_settings",
                   return_value=_mock_settings(max_text_tokens=10, max_tokens=3000)):
            result = citation_node(state)
        output_text = result["citations"][0].text
        # Strip ellipsis before counting
        stripped = output_text.replace(" …", "")
        assert _token_count(stripped) <= 10
        assert "…" in output_text

    def test_short_text_not_trimmed(self):
        short_text = "نص قصير"
        c = _make_citation("c1", text=short_text)
        state = {"question": "سؤال؟", "citations": [c]}
        with patch("app.graphs.legal_assistant.nodes_citation.get_settings",
                   return_value=_mock_settings(max_text_tokens=400, max_tokens=3000)):
            result = citation_node(state)
        assert result["citations"][0].text == short_text
        assert "…" not in result["citations"][0].text

    # -----------------------------------------------------------------------
    # 4. Total token budget enforcement
    # -----------------------------------------------------------------------
    def test_total_budget_drops_excess_citations(self):
        # Each citation text is 10 tokens; budget = 15 → only 1 fits
        citations = [
            _make_citation(f"c{i}", text=" ".join(["كلمة"] * 10))
            for i in range(4)
        ]
        state = {"question": "سؤال؟", "citations": citations}
        with patch("app.graphs.legal_assistant.nodes_citation.get_settings",
                   return_value=_mock_settings(max_tokens=15, max_text_tokens=400)):
            result = citation_node(state)
        assert len(result["citations"]) == 1
        assert result["citations"][0].chunk_id == "c0"  # first kept

    # -----------------------------------------------------------------------
    # 5. Metadata preservation
    # -----------------------------------------------------------------------
    def test_metadata_preserved_after_trimming(self):
        long_text = " ".join(["كلمة"] * 50)
        c = _make_citation(
            chunk_id="chunk-99",
            text=long_text,
            score=0.77,
            article_number="42",
            law_name="قانون الإيجار",
            law_number="136",
            law_year="1981",
            law_type="tenancy",
            category="tenancy_law",
        )
        state = {"question": "سؤال؟", "citations": [c]}
        with patch("app.graphs.legal_assistant.nodes_citation.get_settings",
                   return_value=_mock_settings(max_text_tokens=5, max_tokens=3000)):
            result = citation_node(state)
        out = result["citations"][0]
        assert out.chunk_id == "chunk-99"
        assert out.score == 0.77
        assert out.article_number == "42"
        assert out.law_name == "قانون الإيجار"
        assert out.law_number == "136"
        assert out.law_year == "1981"
        assert out.law_type == "tenancy"
        assert out.category == "tenancy_law"

    # -----------------------------------------------------------------------
    # 8. context_tokens stored in state
    # -----------------------------------------------------------------------
    def test_context_tokens_stored(self):
        citations = [
            _make_citation("c1", text="كلمة كلمة كلمة"),   # 3 tokens
            _make_citation("c2", text="كلمة كلمة"),         # 2 tokens
        ]
        state = {"question": "سؤال؟", "citations": citations}
        with patch("app.graphs.legal_assistant.nodes_citation.get_settings",
                   return_value=_mock_settings()):
            result = citation_node(state)
        assert "context_tokens" in result
        assert result["context_tokens"] == 5

    def test_context_tokens_respects_trim(self):
        """context_tokens must reflect trimmed lengths, not originals."""
        long_text = " ".join(["w"] * 50)
        c = _make_citation("c1", text=long_text)
        state = {"question": "سؤال؟", "citations": [c]}
        with patch("app.graphs.legal_assistant.nodes_citation.get_settings",
                   return_value=_mock_settings(max_text_tokens=10, max_tokens=3000)):
            result = citation_node(state)
        # Trimmed text = 10 words + " …"; token count of "w w … w …" = 10 + "…" = 11
        # We stored total_tokens = _token_count(trimmed_text) which counts "…" as a token
        assert result["context_tokens"] <= 12  # 10 words + possible ellipsis token

    # -----------------------------------------------------------------------
    # 9. Ellipsis appended when text is trimmed
    # -----------------------------------------------------------------------
    def test_ellipsis_appended_when_trimmed(self):
        long_text = " ".join(["a"] * 20)
        c = _make_citation("c1", text=long_text)
        state = {"question": "سؤال؟", "citations": [c]}
        with patch("app.graphs.legal_assistant.nodes_citation.get_settings",
                   return_value=_mock_settings(max_text_tokens=5, max_tokens=3000)):
            result = citation_node(state)
        assert result["citations"][0].text.endswith("…")

    # -----------------------------------------------------------------------
    # State passthrough — other keys unchanged
    # -----------------------------------------------------------------------
    def test_other_state_keys_unchanged(self):
        citations = [_make_citation("c1")]
        state = {
            "question": "سؤال؟",
            "citations": citations,
            "retrieval_confidence": 0.85,
            "retrieval_empty": False,
        }
        with patch("app.graphs.legal_assistant.nodes_citation.get_settings",
                   return_value=_mock_settings()):
            result = citation_node(state)
        assert result["retrieval_confidence"] == 0.85
        assert result["retrieval_empty"] is False
        assert result["question"] == "سؤال؟"
