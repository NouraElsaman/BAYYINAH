from __future__ import annotations

import re

from app.core.config import get_settings
from app.core.logging import get_logger
from app.graphs.legal_assistant.state import LegalAssistantState

logger = get_logger("bayyinah.graph.verification")
settings = get_settings()

FALLBACK_NO_CONTEXT = (
    "عذرًا، لم أتمكن من العثور على نصوص قانونية كافية للإجابة على سؤالك بدقة. "
    "يُرجى إعادة صياغة السؤال بشكل أكثر تحديدًا، أو التواصل مع محامٍ مرخص للحصول على استشارة دقيقة."
)

FALLBACK_LOW_FAITHFULNESS = (
    "لم نتمكن من التحقق من دقة الإجابة بشكل كافٍ بناءً على النصوص القانونية المتاحة. "
    "ننصح بالتواصل مع محامٍ مرخص لمراجعة حالتك بدقة، أو إعادة صياغة السؤال."
)

FALLBACK_UNSAFE = (
    "لا يمكنني تقديم إجابة على هذا الطلب لأنه قد يتضمن محتوى غير مناسب أو خارج نطاق "
    "المساعدة القانونية العامة. يُرجى التواصل مع محامٍ مرخص."
)

UNSAFE_PATTERNS = [
    r"كيف (أ|اعمل|اصنع)?\s*(أهرب|أزور|أزيف)",
    r"تهرب من (الضريبة|الضرائب|القانون)",
    r"تجنب (المسؤولية|العقاب|الملاحقة)",
    r"كيفية ارتكاب",
]

# Precompile UNSAFE_PATTERNS for fast repeated matching
_UNSAFE_PATTERNS_COMPILED = [re.compile(p) for p in UNSAFE_PATTERNS]

# Precompile Arabic diacritics removal pattern
_RE_DIACRITICS = re.compile(r"[\u064B-\u0652]")

# Precompile Arabic token finder
_RE_ARABIC_TOKENS = re.compile(r"[\u0600-\u06FFA-Za-z0-9]+")

ARABIC_DIGIT_MAP = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")


def _normalize(text: str) -> str:
    text = text.translate(ARABIC_DIGIT_MAP)
    text = _RE_DIACRITICS.sub("", text)  # precompiled
    return text


def _tokenize(text: str) -> set[str]:
    text = _normalize(text)
    tokens = _RE_ARABIC_TOKENS.findall(text)  # precompiled
    return {t for t in tokens if len(t) > 1}


def _check_unsafe(question: str) -> bool:
    normalized = _normalize(question)
    return any(p.search(normalized) for p in _UNSAFE_PATTERNS_COMPILED)


def _compute_faithfulness(answer: str, citations) -> float:
    """Lexical overlap-based faithfulness proxy (token overlap between
    answer and retrieved context). Production deployments should layer
    an additional LLM-as-judge or NLI-based check here."""
    if not answer or not citations:
        return 0.0

    answer_tokens = _tokenize(answer)
    if not answer_tokens:
        return 0.0

    context_tokens: set[str] = set()
    for c in citations:
        context_tokens |= _tokenize(c.text)

    if not context_tokens:
        return 0.0

    overlap = answer_tokens & context_tokens
    return round(len(overlap) / len(answer_tokens), 4)


def _validate_citations(answer: str, citations) -> bool:
    """Checks that article numbers mentioned in the answer correspond
    to article numbers present in the retrieved citations."""
    if not citations:
        return False

    answer_norm = _normalize(answer)
    mentioned_articles = set(re.findall(r"(?:المادة|مادة)\s*(\d+)", answer_norm))

    if not mentioned_articles:
        # Answer made no citation claims - cannot be "invalid", but flag for review
        return True

    available_articles = {
        _normalize(c.article_number) for c in citations if c.article_number
    }
    return mentioned_articles.issubset(available_articles) if available_articles else False


from app.observability import trace_node


@trace_node("verify")
def verify_node(state: LegalAssistantState) -> LegalAssistantState:
    warnings: list[str] = list(state.get("warnings", []))

    # 1. Unsafe request guardrail
    if _check_unsafe(state["question"]):
        logger.warning("guardrail_unsafe_request")
        return {
            **state,
            "is_unsafe": True,
            "final_answer": FALLBACK_UNSAFE,
            "is_fallback": True,
            "faithfulness_score": 0.0,
            "citation_valid": False,
            "warnings": warnings + ["unsafe_request_blocked"],
        }

    # 2. Empty retrieval guardrail (now allows general knowledge fallback)
    if state.get("retrieval_empty"):
        logger.info("guardrail_empty_retrieval_general_knowledge_fallback")
        return {
            **state,
            "is_unsafe": False,
            "final_answer": state.get("raw_answer", ""),
            "is_fallback": True,
            "faithfulness_score": 0.0,
            "citation_valid": False,
            "warnings": warnings + ["empty_retrieval"],
        }

    # 2b. Low retrieval-confidence warning (informational only — does NOT block generation)
    # The graph router already decided to send this request here based on confidence.
    # Re-applying the same gate here would double-kill valid retrievals when confidence
    # is slightly above the threshold but faithfulness is also being checked.
    # We only WARN, never block, at this point.
    confidence: float = float(state.get("retrieval_confidence") or 0.0)
    if confidence < settings.CONFIDENCE_FALLBACK_THRESHOLD:
        logger.warning(
            "verify_low_confidence_warning",
            extra={"extra_fields": {
                "confidence": round(confidence, 4),
                "threshold": settings.CONFIDENCE_FALLBACK_THRESHOLD,
                "note": "proceeding with generation — threshold check is advisory here",
            }},
        )
        warnings.append(f"low_retrieval_confidence:{round(confidence, 4)}")
        # Do NOT return fallback here — let faithfulness check decide below

    answer = state.get("raw_answer", "")
    citations = state.get("citations", [])

    faithfulness = _compute_faithfulness(answer, citations)
    citation_valid = _validate_citations(answer, citations)

    is_unsafe = False

    if faithfulness < settings.HALLUCINATION_MIN_OVERLAP:
        logger.warning(
            "guardrail_low_faithfulness",
            extra={"extra_fields": {"score": faithfulness}},
        )
        return {
            **state,
            "is_unsafe": is_unsafe,
            "faithfulness_score": faithfulness,
            "citation_valid": citation_valid,
            "final_answer": FALLBACK_LOW_FAITHFULNESS,
            "is_fallback": True,
            "warnings": warnings + ["low_faithfulness"],
        }

    if not citation_valid:
        warnings.append("citation_mismatch")
        logger.warning("guardrail_citation_mismatch")

    return {
        **state,
        "is_unsafe": is_unsafe,
        "faithfulness_score": faithfulness,
        "citation_valid": citation_valid,
        "final_answer": answer,
        "is_fallback": False,
        "warnings": warnings,
    }
