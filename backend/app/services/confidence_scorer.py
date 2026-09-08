"""
confidence_scorer.py
====================
Pure utility for computing retrieval confidence.

Architecture specification
--------------------------
confidence = w_dense  * top1_score
           + w_recall * recall_coverage
           + w_domain * domain_bonus
           + w_reranker* reranker_margin

Where:
  - top1_score      : dense retrieval score of the top-ranked document.
                      Expected range [0, 1].  Clamped to [0, 1].
  - recall_coverage : num_docs / recall_cap, clamped to [0, 1].
                      Represents how many candidates were retrieved relative
                      to the configured "full recall" cap.
  - domain_bonus    : CONFIDENCE_DOMAIN_BONUS if domain_match else 0.0.
  - reranker_margin : top1_reranker_score / reranker_scale, clamped to [0, 1].
                      Safely falls back to 0.0 when the reranker score is None.

All four component weights default to the architecture specification
(0.4 / 0.3 / 0.2 / 0.1) but are fully overridable via constructor kwargs
or via Settings (environment variables).

This module has NO side-effects:
  - It does NOT modify any graph state.
  - It does NOT call any external service.
  - It does NOT import LangGraph, Qdrant, or any IO library.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from app.core.config import get_settings


# ---------------------------------------------------------------------------
# Configuration dataclass
# ---------------------------------------------------------------------------

@dataclass
class ScorerWeights:
    """
    Configurable weight and normalisation parameters for
    :func:`compute_confidence`.

    All four weights (``w_dense``, ``w_recall``, ``w_domain``,
    ``w_reranker``) should ideally sum to 1.0, but the scorer
    normalises the output to [0, 1] regardless.

    Attributes
    ----------
    w_dense:
        Weight applied to the top-1 dense retrieval score.
    w_recall:
        Weight applied to recall coverage (num_docs / recall_cap).
    w_domain:
        Weight applied to the binary domain match bonus.
    w_reranker:
        Weight applied to the normalised reranker score.
    recall_cap:
        Number of retrieved documents that represents 100 % recall
        coverage.  Retrieval counts above this are treated as 1.0.
    domain_bonus:
        Scalar applied as the domain component when ``domain_match``
        is True.  Set to 0.0 to disable the domain component.
    reranker_scale:
        Divisor used to normalise raw reranker scores to [0, 1].
        Cross-Encoder scores are typically in [-10, 10] or [0, 1]
        depending on the model; the default (1.0) treats them as
        already normalised.  Override as needed.
    """

    w_dense: float = field(default=0.4)
    w_recall: float = field(default=0.3)
    w_domain: float = field(default=0.2)
    w_reranker: float = field(default=0.1)
    recall_cap: int = field(default=5)
    domain_bonus: float = field(default=1.0)
    reranker_scale: float = field(default=1.0)

    @classmethod
    def from_settings(cls) -> "ScorerWeights":
        """Build a :class:`ScorerWeights` from the active :class:`Settings`."""
        s = get_settings()
        return cls(
            w_dense=s.CONFIDENCE_WEIGHT_DENSE,
            w_recall=s.CONFIDENCE_WEIGHT_RECALL,
            w_domain=s.CONFIDENCE_WEIGHT_DOMAIN,
            w_reranker=s.CONFIDENCE_WEIGHT_RERANKER,
            recall_cap=s.CONFIDENCE_RECALL_CAP,
            domain_bonus=s.CONFIDENCE_DOMAIN_BONUS,
        )


# ---------------------------------------------------------------------------
# Core scoring function
# ---------------------------------------------------------------------------

def compute_confidence(
    *,
    top1_dense_score: float,
    num_docs: int,
    domain_match: bool = False,
    top1_reranker_score: Optional[float] = None,
    weights: Optional[ScorerWeights] = None,
) -> float:
    """Compute a scalar retrieval confidence score in **[0.0, 1.0]**.

    Parameters
    ----------
    top1_dense_score:
        Dense vector similarity score of the top-ranked document.
        Values are clamped to [0, 1] before weighting.
    num_docs:
        Total number of documents returned by the retrieval pipeline
        (after reranking / filtering).
    domain_match:
        ``True`` when the detected legal domain of the query matches the
        domain of the retrieved documents.  Contributes a bonus component
        scaled by ``weights.domain_bonus``.
    top1_reranker_score:
        Reranker score for the top-ranked document, or ``None`` if the
        reranker was not used or produced no output.  When ``None`` the
        reranker component is **zero** (safe fall-back, no penalty).
        Values are divided by ``weights.reranker_scale`` then clamped
        to [0, 1].
    weights:
        :class:`ScorerWeights` instance.  When ``None``, weights are
        loaded from :func:`~app.core.config.get_settings`.

    Returns
    -------
    float
        Confidence score in [0.0, 1.0].  Returns 0.0 for degenerate
        inputs (``num_docs == 0``, negative scores, etc.).

    Examples
    --------
    >>> compute_confidence(top1_dense_score=0.9, num_docs=5, domain_match=True,
    ...                    top1_reranker_score=0.8)
    0.92
    """
    if weights is None:
        weights = ScorerWeights.from_settings()

    # ------------------------------------------------------------------
    # Guard: zero documents → no evidence → zero confidence
    # ------------------------------------------------------------------
    if num_docs <= 0:
        return 0.0

    # ------------------------------------------------------------------
    # Component 1: top-1 dense score (clamped to [0, 1])
    # ------------------------------------------------------------------
    top1 = max(0.0, min(1.0, top1_dense_score))

    # ------------------------------------------------------------------
    # Component 2: recall coverage
    #   = num_docs / recall_cap, clamped to [0, 1]
    # ------------------------------------------------------------------
    cap = max(1, weights.recall_cap)  # avoid division by zero
    recall_coverage = min(1.0, num_docs / cap)

    # ------------------------------------------------------------------
    # Component 3: domain bonus
    # ------------------------------------------------------------------
    domain_component = weights.domain_bonus if domain_match else 0.0
    # Clamp to [0, 1] in case domain_bonus > 1.0 is misconfigured
    domain_component = max(0.0, min(1.0, domain_component))

    # ------------------------------------------------------------------
    # Component 4: reranker margin (falls back to 0 when unavailable)
    # ------------------------------------------------------------------
    if top1_reranker_score is None:
        reranker_component = 0.0
    else:
        scale = weights.reranker_scale if weights.reranker_scale > 0 else 1.0
        reranker_component = max(0.0, min(1.0, top1_reranker_score / scale))

    # ------------------------------------------------------------------
    # Weighted sum
    # ------------------------------------------------------------------
    raw = (
        weights.w_dense    * top1
        + weights.w_recall   * recall_coverage
        + weights.w_domain   * domain_component
        + weights.w_reranker * reranker_component
    )

    # Final clamp — guards against misconfigured weights summing > 1.0
    return max(0.0, min(1.0, raw))


# ---------------------------------------------------------------------------
# Convenience helper: score from a list of Citation objects
# ---------------------------------------------------------------------------

def score_from_citations(
    citations: list,
    domain_match: bool = False,
    weights: Optional[ScorerWeights] = None,
) -> float:
    """Convenience wrapper that extracts scores from a list of
    :class:`~app.schemas.chat.Citation` objects.

    Parameters
    ----------
    citations:
        List of :class:`~app.schemas.chat.Citation` objects (after reranking).
        Must expose a ``.score`` attribute (``float``).
    domain_match:
        Forwarded to :func:`compute_confidence`.
    weights:
        Forwarded to :func:`compute_confidence`.

    Returns
    -------
    float
        Confidence score in [0.0, 1.0].  Returns 0.0 for an empty list.
    """
    if not citations:
        return 0.0

    scores = [c.score for c in citations if hasattr(c, "score")]
    if not scores:
        return 0.0

    top1_dense = scores[0]
    # Assume citations are sorted by score descending (reranker output order)
    top1_reranker = scores[0]  # same score field used for both dense + reranker

    return compute_confidence(
        top1_dense_score=top1_dense,
        num_docs=len(citations),
        domain_match=domain_match,
        top1_reranker_score=top1_reranker,
        weights=weights,
    )
