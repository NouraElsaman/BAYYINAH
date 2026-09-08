from __future__ import annotations

import re

from app.core.logging import get_logger
from app.graphs.legal_assistant.state import LegalAssistantState
from app.schemas.chat import LegalDomain

logger = get_logger("bayyinah.graph.domain")

# ---------------------------------------------------------------------------
# Module-level compiled patterns (avoids re-compilation on every call)
# ---------------------------------------------------------------------------
_RE_DIACRITICS = re.compile(r"[\u064B-\u0652]")

# Keyword lexicon for Egyptian Arabic legal domains.
# category_filter values must match the 'category' field stored in Qdrant payloads.
DOMAIN_KEYWORDS: dict[LegalDomain, list[str]] = {
    LegalDomain.LABOR: [
        "عامل", "عمال", "فصل", "أجر", "مرتب", "شركة", "صاحب العمل", "إجازة",
        "استقالة", "إنهاء الخدمة", "تعويض", "نقابة", "ساعات العمل", "عقد عمل",
        "تأمينات", "معاش", "إضراب", "موظف",
    ],
    LegalDomain.TENANCY: [
        "إيجار", "مؤجر", "مستأجر", "شقة", "عقد إيجار", "طرد", "إخلاء",
        "فسخ العقد", "عين مؤجرة", "إيجار قديم", "إيجار جديد", "العقار",
        "زيادة الإيجار", "الوحدة السكنية",
    ],
    LegalDomain.FAMILY: [
        "زواج", "طلاق", "حضانة", "نفقة", "خلع", "رؤية الأبناء", "ميراث",
        "وصية", "نسب", "زوجة", "زوج", "أولاد", "ولاية", "مهر", "عدة",
    ],
    LegalDomain.CRIMINAL: [
        "جريمة", "سرقة", "قتل", "ضرب", "نصب", "احتيال", "عقوبة", "سجن",
        "غرامة", "جنحة", "جناية", "بلاغ", "نيابة", "محبوس", "قضية جنائية",
    ],
    LegalDomain.COMMERCIAL: [
        "شركة", "تجاري", "شيك", "كمبيالة", "إفلاس", "تجارة", "تاجر",
        "سجل تجاري", "شراكة", "عقد تجاري", "علامة تجارية",
    ],
    LegalDomain.ADMINISTRATIVE: [
        "حكومي", "إداري", "قرار إداري", "موظف عام", "ديوان", "مجلس الدولة",
        "ترخيص", "وزارة", "هيئة",
    ],
    LegalDomain.CIVIL: [
        "عقد", "تعويض", "ملكية", "بيع", "شراء", "ضرر", "مسؤولية", "دين",
        "التزام", "عقد بيع",
    ],
}

# Maps detected domain -> (category_filter, law_type_filter) used in Qdrant retrieval.
#
# IMPORTANT — Payload audit (2026-06-20) findings:
#   • law_type is stored as a plain string: 'civil', 'family', 'labor', 'criminal',
#     'constitutional', 'procedural', 'encyclopedia', 'other'
#   • category is stored as a *stringified Python list* e.g. "['الاحوال الشخصية']"
#     which CANNOT be matched by a MatchValue filter — so we ONLY filter on law_type.
#
# law_type corpus distribution (5k sample):
#   civil: 1129 | family: 953 | constitutional: 693 | procedural: 431
#   encyclopedia: 415 | labor: 68 | criminal: 22 | other: 1289
DOMAIN_TO_FILTERS: dict[LegalDomain, tuple[str | None, str | None]] = {
    LegalDomain.LABOR: (None, "labor"),
    LegalDomain.TENANCY: (None, "civil"),      # tenancy falls under civil code
    LegalDomain.FAMILY: (None, "family"),
    LegalDomain.CRIMINAL: (None, "criminal"),
    LegalDomain.COMMERCIAL: (None, "civil"),   # commercial contracts → civil
    LegalDomain.ADMINISTRATIVE: (None, "other"),
    LegalDomain.CIVIL: (None, "civil"),
    LegalDomain.UNKNOWN: (None, None),         # no filter → full corpus search
}


def _normalize_arabic(text: str) -> str:
    text = _RE_DIACRITICS.sub("", text)  # remove diacritics (precompiled)
    text = text.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا")
    text = text.replace("ى", "ي").replace("ة", "ه")
    return text


# ---------------------------------------------------------------------------
# Precompute normalized domain keywords once at import time.
# Previously _normalize_arabic(kw) was called per-keyword per-query.
# ---------------------------------------------------------------------------
_NORMALIZED_DOMAIN_KEYWORDS: dict[LegalDomain, list[str]] = {
    domain: [_normalize_arabic(kw) for kw in keywords]
    for domain, keywords in DOMAIN_KEYWORDS.items()
}


from app.observability import trace_node


@trace_node("detect_domain")
def detect_domain_node(state: LegalAssistantState) -> LegalAssistantState:
    question = state["question"]
    normalized = _normalize_arabic(question)

    scores: dict[LegalDomain, int] = {d: 0 for d in _NORMALIZED_DOMAIN_KEYWORDS}
    for domain, keywords in _NORMALIZED_DOMAIN_KEYWORDS.items():
        for kw in keywords:
            if kw in normalized:
                scores[domain] += 1

    best_domain = max(scores, key=lambda d: scores[d])
    if scores[best_domain] == 0:
        best_domain = LegalDomain.UNKNOWN

    category, law_type = DOMAIN_TO_FILTERS[best_domain]

    logger.info(
        "domain_detected",
        extra={"extra_fields": {"domain": best_domain.value, "scores": {k.value: v for k, v in scores.items()}}},
    )

    return {
        **state,
        "domain": best_domain,
        "category_filter": category,
        "law_type_filter": law_type,
    }
