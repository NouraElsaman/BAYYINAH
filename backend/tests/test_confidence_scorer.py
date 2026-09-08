"""
test_confidence_scorer.py
=========================
Comprehensive unit tests for :mod:`app.services.confidence_scorer`.

Coverage:
  - Boundary values (0, 1, edge inputs)
  - Missing / None reranker score → zero reranker component
  - Recall normalisation (under / at / over the cap)
  - Domain match bonus (on / off)
  - Custom weights (non-default ScorerWeights)
  - Weight sum != 1.0 → output still clamped to [0, 1]
  - score_from_citations() helper
  - Degenerate inputs (num_docs=0, negative scores, empty citations)
"""
from __future__ import annotations

import pytest
from unittest.mock import patch, MagicMock

from app.services.confidence_scorer import (
    ScorerWeights,
    compute_confidence,
    score_from_citations,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _weights(**kw) -> ScorerWeights:
    """Create a ScorerWeights with defaults overridden by kwargs."""
    defaults = dict(
        w_dense=0.4,
        w_recall=0.3,
        w_domain=0.2,
        w_reranker=0.1,
        recall_cap=5,
        domain_bonus=1.0,
        reranker_scale=1.0,
    )
    defaults.update(kw)
    return ScorerWeights(**defaults)


def _citation(score: float):
    """Minimal Citation-like object with a score attribute."""
    c = MagicMock()
    c.score = score
    return c


# ===========================================================================
# compute_confidence — boundary values
# ===========================================================================

class TestBoundaryValues:
    def test_all_perfect_scores(self):
        """All components at maximum → confidence == 1.0."""
        w = _weights()
        score = compute_confidence(
            top1_dense_score=1.0,
            num_docs=5,
            domain_match=True,
            top1_reranker_score=1.0,
            weights=w,
        )
        assert score == pytest.approx(1.0)

    def test_all_zero_scores(self):
        """All scoring inputs zero (but num_docs > 0) → very low score."""
        w = _weights()
        score = compute_confidence(
            top1_dense_score=0.0,
            num_docs=1,
            domain_match=False,
            top1_reranker_score=0.0,
            weights=w,
        )
        # recall_coverage = 1/5 = 0.2, weighted 0.3 → 0.06
        assert score == pytest.approx(0.3 * (1 / 5), rel=1e-3)

    def test_num_docs_zero_returns_zero(self):
        """Zero retrieved documents → always 0.0 regardless of other inputs."""
        score = compute_confidence(
            top1_dense_score=0.99,
            num_docs=0,
            domain_match=True,
            top1_reranker_score=0.99,
        )
        assert score == 0.0

    def test_negative_dense_score_clamped(self):
        """Negative dense score is clamped to 0.0 before weighting."""
        w = _weights()
        score = compute_confidence(
            top1_dense_score=-5.0,
            num_docs=3,
            domain_match=False,
            top1_reranker_score=None,
            weights=w,
        )
        # dense = 0 (clamped), recall = 3/5=0.6, domain=0, reranker=0
        expected = 0.3 * 0.6
        assert score == pytest.approx(expected, rel=1e-3)

    def test_dense_score_above_one_clamped(self):
        """Dense score > 1.0 is clamped to 1.0."""
        w = _weights()
        score_clamped = compute_confidence(
            top1_dense_score=2.5, num_docs=5, domain_match=True,
            top1_reranker_score=1.0, weights=w,
        )
        score_exact = compute_confidence(
            top1_dense_score=1.0, num_docs=5, domain_match=True,
            top1_reranker_score=1.0, weights=w,
        )
        assert score_clamped == pytest.approx(score_exact, rel=1e-6)

    def test_confidence_never_exceeds_one(self):
        """Even with mismatched weights summing > 1, output is clamped ≤ 1."""
        w = _weights(w_dense=0.9, w_recall=0.9, w_domain=0.9, w_reranker=0.9)
        score = compute_confidence(
            top1_dense_score=1.0, num_docs=5, domain_match=True,
            top1_reranker_score=1.0, weights=w,
        )
        assert score <= 1.0

    def test_confidence_never_below_zero(self):
        """Output is never negative."""
        w = _weights(w_dense=-0.5, w_recall=-0.5)
        score = compute_confidence(
            top1_dense_score=0.5, num_docs=2, domain_match=False,
            top1_reranker_score=None, weights=w,
        )
        assert score >= 0.0


# ===========================================================================
# compute_confidence — reranker handling
# ===========================================================================

class TestRerankerHandling:
    def test_none_reranker_contributes_zero(self):
        """When reranker score is None the reranker component must be 0."""
        w = _weights()
        with_reranker = compute_confidence(
            top1_dense_score=0.7, num_docs=3, domain_match=False,
            top1_reranker_score=1.0, weights=w,
        )
        without_reranker = compute_confidence(
            top1_dense_score=0.7, num_docs=3, domain_match=False,
            top1_reranker_score=None, weights=w,
        )
        # Difference should equal w_reranker * 1.0 (reranker at max)
        assert with_reranker - without_reranker == pytest.approx(w.w_reranker, rel=1e-3)

    def test_negative_reranker_score_clamped(self):
        """Negative reranker scores are clamped to 0."""
        w = _weights()
        score_neg = compute_confidence(
            top1_dense_score=0.5, num_docs=2, domain_match=False,
            top1_reranker_score=-3.0, weights=w,
        )
        score_none = compute_confidence(
            top1_dense_score=0.5, num_docs=2, domain_match=False,
            top1_reranker_score=None, weights=w,
        )
        assert score_neg == pytest.approx(score_none, rel=1e-6)

    def test_reranker_scale_normalises_large_scores(self):
        """A reranker_scale > 1 normalises raw scores above 1.0."""
        w = _weights(reranker_scale=10.0)
        score = compute_confidence(
            top1_dense_score=0.0, num_docs=1, domain_match=False,
            top1_reranker_score=5.0,  # raw score in [-10, 10]
            weights=w,
        )
        # reranker component = 0.1 * (5/10) = 0.05
        # recall_coverage = 1/5 = 0.2, component = 0.3 * 0.2 = 0.06
        expected = 0.1 * (5.0 / 10.0) + 0.3 * (1 / 5)
        assert score == pytest.approx(expected, rel=1e-3)

    def test_reranker_above_scale_clamped(self):
        """Reranker / scale > 1 is clamped to 1.0."""
        w = _weights(reranker_scale=1.0)
        score_high = compute_confidence(
            top1_dense_score=0.0, num_docs=5, domain_match=False,
            top1_reranker_score=100.0, weights=w,
        )
        score_one = compute_confidence(
            top1_dense_score=0.0, num_docs=5, domain_match=False,
            top1_reranker_score=1.0, weights=w,
        )
        assert score_high == pytest.approx(score_one, rel=1e-6)


# ===========================================================================
# compute_confidence — recall normalisation
# ===========================================================================

class TestRecallNormalisation:
    def test_recall_at_cap_is_one(self):
        """num_docs == recall_cap → recall_coverage == 1.0."""
        w = _weights(recall_cap=5)
        score = compute_confidence(
            top1_dense_score=0.0, num_docs=5, domain_match=False,
            top1_reranker_score=None, weights=w,
        )
        expected = 0.3 * 1.0  # only recall component contributes
        assert score == pytest.approx(expected, rel=1e-3)

    def test_recall_under_cap_is_fractional(self):
        """num_docs < recall_cap → partial recall coverage."""
        w = _weights(recall_cap=10)
        score = compute_confidence(
            top1_dense_score=0.0, num_docs=3, domain_match=False,
            top1_reranker_score=None, weights=w,
        )
        expected = 0.3 * (3 / 10)
        assert score == pytest.approx(expected, rel=1e-3)

    def test_recall_over_cap_clamped_to_one(self):
        """num_docs > recall_cap → recall_coverage clamped to 1.0."""
        w = _weights(recall_cap=3)
        score_over = compute_confidence(
            top1_dense_score=0.0, num_docs=10, domain_match=False,
            top1_reranker_score=None, weights=w,
        )
        score_at_cap = compute_confidence(
            top1_dense_score=0.0, num_docs=3, domain_match=False,
            top1_reranker_score=None, weights=w,
        )
        assert score_over == pytest.approx(score_at_cap, rel=1e-6)

    def test_recall_cap_one(self):
        """recall_cap=1 → even a single document gives full recall."""
        w = _weights(recall_cap=1)
        score = compute_confidence(
            top1_dense_score=0.0, num_docs=1, domain_match=False,
            top1_reranker_score=None, weights=w,
        )
        expected = 0.3 * 1.0
        assert score == pytest.approx(expected, rel=1e-3)


# ===========================================================================
# compute_confidence — domain bonus
# ===========================================================================

class TestDomainBonus:
    def test_domain_match_true_adds_component(self):
        """domain_match=True increases score by w_domain * domain_bonus."""
        w = _weights()
        without = compute_confidence(
            top1_dense_score=0.5, num_docs=3, domain_match=False,
            top1_reranker_score=None, weights=w,
        )
        with_ = compute_confidence(
            top1_dense_score=0.5, num_docs=3, domain_match=True,
            top1_reranker_score=None, weights=w,
        )
        assert with_ - without == pytest.approx(w.w_domain * w.domain_bonus, rel=1e-3)

    def test_domain_match_false_zero_component(self):
        """domain_match=False → zero domain contribution."""
        w = _weights(domain_bonus=1.0)
        score = compute_confidence(
            top1_dense_score=0.0, num_docs=5, domain_match=False,
            top1_reranker_score=None, weights=w,
        )
        # Only recall contributes: 0.3 * 1.0
        expected = 0.3 * 1.0
        assert score == pytest.approx(expected, rel=1e-3)

    def test_domain_bonus_zero_disables_component(self):
        """Setting domain_bonus=0 makes domain_match irrelevant."""
        w = _weights(domain_bonus=0.0)
        score_match = compute_confidence(
            top1_dense_score=0.5, num_docs=3, domain_match=True,
            top1_reranker_score=None, weights=w,
        )
        score_no_match = compute_confidence(
            top1_dense_score=0.5, num_docs=3, domain_match=False,
            top1_reranker_score=None, weights=w,
        )
        assert score_match == pytest.approx(score_no_match, rel=1e-6)

    def test_domain_bonus_above_one_clamped(self):
        """domain_bonus > 1 is clamped to 1.0 for the component."""
        w_clamped = _weights(domain_bonus=999.0)
        w_one = _weights(domain_bonus=1.0)
        score_clamped = compute_confidence(
            top1_dense_score=0.0, num_docs=1, domain_match=True,
            top1_reranker_score=None, weights=w_clamped,
        )
        score_one = compute_confidence(
            top1_dense_score=0.0, num_docs=1, domain_match=True,
            top1_reranker_score=None, weights=w_one,
        )
        assert score_clamped == pytest.approx(score_one, rel=1e-6)


# ===========================================================================
# compute_confidence — configurable weights
# ===========================================================================

class TestConfigurableWeights:
    def test_custom_weights_sum_to_one(self):
        """Custom equal weights (0.25 each) produce the correct result."""
        w = _weights(w_dense=0.25, w_recall=0.25, w_domain=0.25, w_reranker=0.25)
        score = compute_confidence(
            top1_dense_score=1.0, num_docs=5, domain_match=True,
            top1_reranker_score=1.0, weights=w,
        )
        assert score == pytest.approx(1.0)

    def test_all_weight_on_dense(self):
        """Weight entirely on dense → score equals top1_dense_score."""
        w = _weights(w_dense=1.0, w_recall=0.0, w_domain=0.0, w_reranker=0.0)
        for dense_val in [0.0, 0.3, 0.7, 1.0]:
            score = compute_confidence(
                top1_dense_score=dense_val, num_docs=5, domain_match=True,
                top1_reranker_score=1.0, weights=w,
            )
            assert score == pytest.approx(dense_val, rel=1e-6)

    def test_all_weight_on_recall(self):
        """Weight entirely on recall → score equals recall_coverage."""
        w = _weights(w_dense=0.0, w_recall=1.0, w_domain=0.0, w_reranker=0.0,
                     recall_cap=10)
        score = compute_confidence(
            top1_dense_score=0.9, num_docs=4, domain_match=True,
            top1_reranker_score=0.9, weights=w,
        )
        assert score == pytest.approx(4 / 10, rel=1e-3)

    def test_architecture_spec_example(self):
        """Verify the exact values from the architecture specification docstring."""
        # From compute_confidence docstring example
        w = _weights(w_dense=0.4, w_recall=0.3, w_domain=0.2, w_reranker=0.1,
                     recall_cap=5, domain_bonus=1.0)
        score = compute_confidence(
            top1_dense_score=0.9, num_docs=5, domain_match=True,
            top1_reranker_score=0.8, weights=w,
        )
        expected = 0.4 * 0.9 + 0.3 * 1.0 + 0.2 * 1.0 + 0.1 * 0.8
        assert score == pytest.approx(expected, rel=1e-6)


# ===========================================================================
# ScorerWeights.from_settings()
# ===========================================================================

class TestFromSettings:
    def test_from_settings_reads_config(self):
        """from_settings() honours environment-driven config values."""
        mock_settings = MagicMock()
        mock_settings.CONFIDENCE_WEIGHT_DENSE = 0.5
        mock_settings.CONFIDENCE_WEIGHT_RECALL = 0.2
        mock_settings.CONFIDENCE_WEIGHT_DOMAIN = 0.2
        mock_settings.CONFIDENCE_WEIGHT_RERANKER = 0.1
        mock_settings.CONFIDENCE_RECALL_CAP = 8
        mock_settings.CONFIDENCE_DOMAIN_BONUS = 0.8

        with patch("app.services.confidence_scorer.get_settings", return_value=mock_settings):
            w = ScorerWeights.from_settings()

        assert w.w_dense == 0.5
        assert w.recall_cap == 8
        assert w.domain_bonus == 0.8

    def test_none_weights_uses_settings(self):
        """Passing weights=None to compute_confidence triggers from_settings()."""
        mock_settings = MagicMock()
        mock_settings.CONFIDENCE_WEIGHT_DENSE = 1.0
        mock_settings.CONFIDENCE_WEIGHT_RECALL = 0.0
        mock_settings.CONFIDENCE_WEIGHT_DOMAIN = 0.0
        mock_settings.CONFIDENCE_WEIGHT_RERANKER = 0.0
        mock_settings.CONFIDENCE_RECALL_CAP = 5
        mock_settings.CONFIDENCE_DOMAIN_BONUS = 1.0

        with patch("app.services.confidence_scorer.get_settings", return_value=mock_settings):
            score = compute_confidence(
                top1_dense_score=0.6, num_docs=3, domain_match=False,
                top1_reranker_score=None, weights=None,
            )
        # With w_dense=1.0 and all others 0, score == top1_dense
        assert score == pytest.approx(0.6, rel=1e-6)


# ===========================================================================
# score_from_citations() helper
# ===========================================================================

class TestScoreFromCitations:
    def test_empty_citations_returns_zero(self):
        assert score_from_citations([]) == 0.0

    def test_single_citation(self):
        w = _weights(recall_cap=5)
        c = _citation(0.8)
        score = score_from_citations([c], domain_match=False, weights=w)
        # dense=0.8, recall=1/5=0.2, domain=0, reranker=0.8 (same score)
        expected = 0.4 * 0.8 + 0.3 * 0.2 + 0.0 + 0.1 * 0.8
        assert score == pytest.approx(expected, rel=1e-3)

    def test_multiple_citations_recall_coverage(self):
        """3 citations → recall_coverage = 3/5 with default cap."""
        w = _weights(recall_cap=5)
        citations = [_citation(0.9), _citation(0.7), _citation(0.5)]
        score = score_from_citations(citations, domain_match=True, weights=w)
        # dense=0.9, recall=3/5=0.6, domain=1.0, reranker=0.9
        expected = 0.4 * 0.9 + 0.3 * 0.6 + 0.2 * 1.0 + 0.1 * 0.9
        assert score == pytest.approx(expected, rel=1e-3)

    def test_citations_without_score_attr_handled(self):
        """Objects with no .score attribute are skipped gracefully."""
        bad = MagicMock(spec=[])  # no .score
        assert score_from_citations([bad]) == 0.0

    def test_citations_at_recall_cap(self):
        """When citation count == recall_cap, recall_coverage is exactly 1."""
        w = _weights(recall_cap=3)
        citations = [_citation(0.5), _citation(0.4), _citation(0.3)]
        score = score_from_citations(citations, domain_match=False, weights=w)
        expected = 0.4 * 0.5 + 0.3 * 1.0 + 0.0 + 0.1 * 0.5
        assert score == pytest.approx(expected, rel=1e-3)
