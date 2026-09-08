from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.graphs.legal_assistant.nodes_retrieval import _should_skip_rerank
from app.schemas.chat import Citation


def make_citation(
    article_number: str = '69',
    law_type: str = 'labor',
    law_name: str = 'قانون العمل',
    score: float = 0.03,
) -> Citation:
    return Citation(
        chunk_id='c1', doc_id='d1', law_name=law_name, law_number='12',
        law_year='2003', law_type=law_type, category='labor_law',
        article_number=article_number, text='نص قانوني تجريبي', score=score,
    )


def two_citations(art1='69', art2='76', score1=0.031, score2=0.016, law_type='labor'):
    return [
        make_citation(article_number=art1, score=score1, law_type=law_type),
        make_citation(article_number=art2, score=score2, law_type=law_type),
    ]


class TestShouldSkipRerank:

    def test_article_ref_matched_high_confidence(self):
        citations = two_citations(art1='69', score1=0.031, score2=0.016)
        skip, reason = _should_skip_rerank(citations, 'ماذا تنص المادة 69 من قانون العمل؟', 'labor')
        assert skip is True
        assert reason == 'article_ref_matched_high_confidence'

    def test_no_article_ref_never_skips(self):
        citations = two_citations()
        skip, reason = _should_skip_rerank(citations, 'هل يجوز فصل العامل بدون سبب؟', 'labor')
        assert skip is False
        assert reason == 'no_article_ref'

    def test_article_ref_not_top1(self):
        citations = two_citations(art1='76', art2='69')
        skip, reason = _should_skip_rerank(citations, 'ماذا تنص المادة 69 من قانون العمل؟', 'labor')
        assert skip is False
        assert reason == 'article_ref_not_top1'

    def test_domain_mismatch_prevents_skip(self):
        citations = two_citations(art1='69', law_type='family')
        skip, reason = _should_skip_rerank(citations, 'ماذا تنص المادة 69 من قانون العمل؟', 'labor')
        assert skip is False
        assert reason == 'domain_mismatch'

    def test_zero_margin_always_reranks(self):
        citations = two_citations(art1='69', art2='76', score1=0.016, score2=0.016)
        skip, reason = _should_skip_rerank(citations, 'ماذا تنص المادة 69 من قانون العمل؟', 'labor')
        assert skip is False
        assert reason == 'zero_margin_ambiguous'

    def test_too_few_candidates(self):
        citations = [make_citation()]
        skip, reason = _should_skip_rerank(citations, 'ماذا تنص المادة 69 من قانون العمل؟', 'labor')
        assert skip is False
        assert reason == 'too_few_candidates'

    def test_no_domain_filter_skips_without_domain_check(self):
        citations = two_citations(art1='69', score1=0.031, score2=0.016)
        skip, reason = _should_skip_rerank(citations, 'ماذا تنص المادة 69؟', law_type_filter=None)
        assert skip is True

    def test_empty_citations(self):
        skip, reason = _should_skip_rerank([], 'ماذا تنص المادة 69؟', 'labor')
        assert skip is False
        assert reason == 'too_few_candidates'

    def test_negative_margin_treated_as_zero(self):
        citations = two_citations(art1='69', score1=0.010, score2=0.031)
        skip, reason = _should_skip_rerank(citations, 'ماذا تنص المادة 69؟', 'labor')
        assert skip is False
        assert reason == 'zero_margin_ambiguous'

    def test_arabic_dialect_article_ref(self):
        citations = two_citations(art1='76', score1=0.03, score2=0.01)
        skip, reason = _should_skip_rerank(citations, 'هو المادة 76 بتقول اي في قانون العمل؟', 'labor')
        assert skip is True


@patch('app.graphs.legal_assistant.nodes_retrieval.get_embedding_service')
@patch('app.graphs.legal_assistant.nodes_retrieval.get_retrieval_service')
@patch('app.graphs.legal_assistant.nodes_retrieval.get_reranker_service')
def test_article_ref_query_skips_reranker(mock_get_reranker, mock_get_retriever, mock_get_embedder):
    from app.graphs.legal_assistant.nodes_retrieval import retrieve_node
    mock_get_embedder.return_value.embed_query.return_value = [0.1, 0.2, 0.3]
    mock_get_retriever.return_value.search.return_value = [
        make_citation(article_number='69', score=0.031, law_type='labor'),
        make_citation(article_number='76', score=0.016, law_type='labor'),
    ]
    mock_reranker = MagicMock()
    mock_reranker._backend = 'cross_encoder'
    mock_get_reranker.return_value = mock_reranker
    state = {'question': 'ماذا تنص المادة 69 من قانون العمل؟', 'law_type_filter': 'labor', 'category_filter': None, 'warnings': []}
    result = retrieve_node(state)
    mock_reranker.rerank.assert_not_called()
    assert result['citations'][0].article_number == '69'


@patch('app.graphs.legal_assistant.nodes_retrieval.get_embedding_service')
@patch('app.graphs.legal_assistant.nodes_retrieval.get_retrieval_service')
@patch('app.graphs.legal_assistant.nodes_retrieval.get_reranker_service')
def test_general_query_always_uses_reranker(mock_get_reranker, mock_get_retriever, mock_get_embedder):
    from app.graphs.legal_assistant.nodes_retrieval import retrieve_node
    mock_get_embedder.return_value.embed_query.return_value = [0.1, 0.2, 0.3]
    mock_get_retriever.return_value.search.return_value = [
        make_citation(article_number='69', score=0.031),
        make_citation(article_number='76', score=0.016),
    ]
    mock_reranker = MagicMock()
    mock_reranker._backend = 'cross_encoder'
    mock_reranker.rerank.return_value = [make_citation(article_number='69', score=0.99)]
    mock_get_reranker.return_value = mock_reranker
    state = {'question': 'هل يجوز فصل العامل بدون سبب؟', 'law_type_filter': 'labor', 'category_filter': None, 'warnings': []}
    retrieve_node(state)
    mock_reranker.rerank.assert_called_once()


@patch('app.graphs.legal_assistant.nodes_retrieval.get_embedding_service')
@patch('app.graphs.legal_assistant.nodes_retrieval.get_retrieval_service')
@patch('app.graphs.legal_assistant.nodes_retrieval.get_reranker_service')
def test_corpus_miss_uses_reranker(mock_get_reranker, mock_get_retriever, mock_get_embedder):
    from app.graphs.legal_assistant.nodes_retrieval import retrieve_node
    mock_get_embedder.return_value.embed_query.return_value = [0.1, 0.2, 0.3]
    mock_get_retriever.return_value.search.return_value = [
        make_citation(article_number='28', score=0.031, law_type='constitutional'),
        make_citation(article_number='76', score=0.016, law_type='constitutional'),
    ]
    mock_reranker = MagicMock()
    mock_reranker._backend = 'cross_encoder'
    mock_reranker.rerank.return_value = [make_citation(article_number='28', score=0.77)]
    mock_get_reranker.return_value = mock_reranker
    state = {'question': 'ما هي إجراءات الطعن على قرار لجنة الانتخابات الرئاسية؟', 'law_type_filter': None, 'category_filter': None, 'warnings': []}
    retrieve_node(state)
    mock_reranker.rerank.assert_called_once()


@patch('app.graphs.legal_assistant.nodes_retrieval.get_embedding_service')
@patch('app.graphs.legal_assistant.nodes_retrieval.get_retrieval_service')
@patch('app.graphs.legal_assistant.nodes_retrieval.get_reranker_service')
def test_article_ref_wrong_top1_uses_reranker(mock_get_reranker, mock_get_retriever, mock_get_embedder):
    from app.graphs.legal_assistant.nodes_retrieval import retrieve_node
    mock_get_embedder.return_value.embed_query.return_value = [0.1, 0.2, 0.3]
    mock_get_retriever.return_value.search.return_value = [
        make_citation(article_number='76', score=0.031),
        make_citation(article_number='69', score=0.016),
    ]
    mock_reranker = MagicMock()
    mock_reranker._backend = 'cross_encoder'
    mock_reranker.rerank.return_value = [make_citation(article_number='69', score=0.98)]
    mock_get_reranker.return_value = mock_reranker
    state = {'question': 'ماذا تنص المادة 69 من قانون العمل؟', 'law_type_filter': 'labor', 'category_filter': None, 'warnings': []}
    retrieve_node(state)
    mock_reranker.rerank.assert_called_once()
