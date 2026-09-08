"""
test_answer_synthesis.py
========================
Unit tests for the Answer Synthesis node (nodes_answer_synthesis.py).
"""
from __future__ import annotations

import pytest

from app.schemas.chat import Citation
from app.graphs.legal_assistant.nodes_answer_synthesis import answer_synthesis_node


def _make_citation(chunk_id: str, law_name: str, law_type: str = "labor", score: float = 0.8) -> Citation:
    return Citation(
        chunk_id=chunk_id,
        doc_id=f"doc_{chunk_id}",
        law_name=law_name,
        law_number="12",
        law_year="2003",
        law_type=law_type,
        category="labor_law",
        article_number="10",
        text="نص سياق تجريبي للمطابقة",
        score=score,
    )


# ===========================================================================
# 1. Local citations only (no web results)
# ===========================================================================

def test_local_citations_only():
    local_c = [_make_citation("local_1", "قانون العمل"), _make_citation("local_2", "قانون العمل")]
    state = {
        "citations": local_c,
        "web_results": [],
    }

    res = answer_synthesis_node(state)
    
    # State should remain unchanged
    assert len(res["citations"]) == 2
    assert res["citations"][0].chunk_id == "local_1"
    assert res["citations"][1].chunk_id == "local_2"


# ===========================================================================
# 2. Web citations only (no local citations)
# ===========================================================================

def test_web_citations_only():
    state = {
        "citations": [],
        "web_results": [
            {"title": "موقع إخباري", "url": "https://news.eg/1", "content": "أخبار قانونية", "score": 0.9},
            {"title": "منتدى قانوني", "url": "https://forum.eg/2", "content": "نقاشات قانون العمل", "score": 0.7},
        ],
    }

    res = answer_synthesis_node(state)

    assert len(res["citations"]) == 2
    assert res["citations"][0].law_name == "موقع إخباري"
    assert res["citations"][0].law_type == "web"
    assert res["citations"][1].law_name == "منتدى قانوني"
    assert res["citations"][1].law_type == "web"
    assert res["retrieval_empty"] is False


# ===========================================================================
# 3. Local + Web merge & Ranking Preserved
# ===========================================================================

def test_local_and_web_merge_preserves_ranking():
    local_c = [_make_citation("local_1", "قانون العمل", score=0.95)]
    state = {
        "citations": local_c,
        "web_results": [
            {"title": "موقع إخباري", "url": "https://news.eg/1", "content": "أخبار قانونية", "score": 0.9},
        ],
    }

    res = answer_synthesis_node(state)

    assert len(res["citations"]) == 2
    # Local citation must remain at index 0 (preserving ranking order)
    assert res["citations"][0].chunk_id == "local_1"
    assert res["citations"][0].score == 0.95
    # Web citation appended at index 1
    assert res["citations"][1].chunk_id == "web_0"
    assert res["citations"][1].score == 0.9


# ===========================================================================
# 4. Duplicate chunk_id
# ===========================================================================

def test_duplicate_chunk_id_filtered():
    local_c = [_make_citation("local_1", "قانون العمل")]
    # Preserved in local_citations by wrapped node
    state = {
        "local_citations": local_c,
        # state["citations"] holds the web search result (which has a duplicate chunk_id)
        "citations": [_make_citation("local_1", "قانون العمل مكرر")],
        "web_results": [
            # web result translates to chunk_id: web_0, which is unique
            {"title": "فريد", "url": "https://unique.eg", "content": "محتوى فريد"},
        ],
    }

    res = answer_synthesis_node(state)

    # local_1 and unique web result should be kept, the duplicate discarded
    assert len(res["citations"]) == 2
    assert res["citations"][0].chunk_id == "local_1"
    assert res["citations"][1].chunk_id == "web_0"


# ===========================================================================
# 5. Duplicate URL
# ===========================================================================

def test_duplicate_url_filtered():
    state = {
        "citations": [],
        "web_results": [
            {"title": "الأصل", "url": "https://egy.gov/1", "content": "محتوى اصلي"},
            {"title": "مكرر", "url": "https://egy.gov/1", "content": "محتوى مكرر نفس الرابط"},  # Duplicate URL
        ],
    }

    res = answer_synthesis_node(state)

    # Only original should remain
    assert len(res["citations"]) == 1
    assert res["citations"][0].law_name == "الأصل"


# ===========================================================================
# 6. Empty inputs
# ===========================================================================

def test_empty_inputs():
    state = {
        "citations": [],
        "web_results": [],
    }

    res = answer_synthesis_node(state)
    assert res["citations"] == []
    assert res["retrieval_empty"] is True


# ===========================================================================
# 7. Metadata preserved
# ===========================================================================

def test_metadata_preserved():
    local_c = [
        Citation(
            chunk_id="local_custom",
            doc_id="doc_custom",
            law_name="قانون مخصص",
            law_number="99",
            law_year="1999",
            law_type="custom",
            category="custom_law",
            article_number="7",
            text="نص مخصص",
            score=0.88,
        )
    ]
    state = {
        "citations": local_c,
        "web_results": [],
    }

    res = answer_synthesis_node(state)
    c = res["citations"][0]
    
    assert c.chunk_id == "local_custom"
    assert c.law_name == "قانون مخصص"
    assert c.law_number == "99"
    assert c.law_year == "1999"
    assert c.law_type == "custom"
    assert c.category == "custom_law"
    assert c.article_number == "7"
    assert c.score == 0.88
