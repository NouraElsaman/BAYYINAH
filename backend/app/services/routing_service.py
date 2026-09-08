import random
import re
from typing import Tuple

from app.core.logging import get_logger
from app.services.llm_service import get_llm_service

logger = get_logger("bayyinah.routing")

# ---------------------------------------------------------------------------
# Module-level precompiled regex (avoids per-call recompilation)
# ---------------------------------------------------------------------------
_RE_DIACRITICS = re.compile(r"[\u064B-\u0652]")

GREETING_RESPONSES = [
    "وعليكم السلام ورحمة الله وبركاته يا فندم! 🤝 أهلاً بحضرتك في بيّنة. أقدر أساعدك إزاي النهاردة في القانون المصري؟",
    "أهلاً بحضرتك يا فندم! 😊 منور بيّنة، إزاي أقدر أفيد حضرتك في الاستشارات القانونية النهاردة؟",
    "أهلاً وسهلاً بك! 👋 أنا بيّنة، مساعدك القانوني الذكي. تحت أمرك في أي استفسار يخص القوانين المصرية.",
    "مساء الفل يا فندم! 🌸 أقدر أساعد حضرتك إزاي النهاردة في المسائل القانونية؟",
    "صباح النور والسرور! ☀️ أهلاً بك في بيّنة. كيف يمكنني مساعدتك اليوم؟"
]

OUT_OF_SCOPE_RESPONSES = [
    "أهلاً بحضرتك يا فندم! 🙏 أنا مساعد قانوني متخصص في قوانين جمهورية مصر العربية فقط (زي قانون العمل، الإيجارات، الأحوال الشخصية، الجنائي، والمدني). للأسف مقدرش أساعدك في موضوع خارج التخصص ده. لو عندك أي سؤال قانوني مصري، أنا تحت أمرك!",
    "للأسف يا فندم، الاستفسار ده خارج نطاق تخصصي القانوني 🔍 أنا هنا عشان أجاوب على الأسئلة المتعلقة بالقوانين والمحاكم المصرية بس. لو تحب تسألني في أي حاجة قانونية، اتفضل!"
]

UNSAFE_RESPONSES = [
    "عذرًا يا فندم، لا يمكنني تقديم إجابة على هذا الطلب لأنه قد يتضمن أعمالاً غير قانونية أو مخالفة للأنظمة العامة في جمهورية مصر العربية. يُرجى الالتزام بالقوانين المنظمة.",
    "للأسف مقدرش أساعد حضرتك في الاستفسار ده لأنه يتعلق بأعمال أو ممارسات غير قانونية يعاقب عليها القانون المصري. تحت أمرك في أي استفسار قانوني مشروع."
]

# Fast path keywords matching
GREETING_KEYWORDS = [
    r"\bالسلام\s+عليكم\b",
    r"\bصباح\s+الخير\b", r"\bصباح\s+النور\b", r"\bصباح\s+الفل\b",
    r"\bمساء\s+الخير\b", r"\bمساء\s+النور\b", r"\bمساء\s+الفل\b",
    r"\bمرحبا\b", r"\bمرحباً\b", r"\bاهلا\b", r"\bأاهلا\b", r"\bأهلاً\b", r"\bهلا\b",
    r"\bهاي\b", r"\bازيك\b", r"\bكيف\s+حالك\b", r"\bكيفك\b", r"\bشلونك\b"
]

OUT_OF_SCOPE_KEYWORDS = [
    # Cooking / Food — no \b: Arabic ال prefix attaches directly
    r"طريقة\s+عمل", r"طبخ", r"وصفة", r"أكلة", r"حلويات", r"محشي",
    # Sports
    r"كورة", r"مباراة", r"الأهلي", r"الزمالك", r"ريال\s+مدريد", r"دوري",
    # Programming / Tech
    r"برمجة", r"كود", r"بايثون", r"جافا", r"سيكوال", r"موقع", r"سيرفر"
]

UNSAFE_KEYWORDS = [
    r"\bتهرب\s+من\s+الضرايب\b", r"\bتزوير\b", r"\bأهرب\s+من\b", r"\bأسرق\b", r"\bتزييف\b",
    r"\bالنصب\s+على\b", r"\bرشوة\b", r"\bقتل\s+شخص\b", r"\bجريمة\s+مثالية\b"
]

# ---------------------------------------------------------------------------
# Precompile all keyword patterns at import time
# ---------------------------------------------------------------------------
_GREETING_PATTERNS_COMPILED = [re.compile(p) for p in GREETING_KEYWORDS]
_OUT_OF_SCOPE_PATTERNS_COMPILED = [re.compile(p) for p in OUT_OF_SCOPE_KEYWORDS]
_UNSAFE_KEYWORD_PATTERNS_COMPILED = [re.compile(p) for p in UNSAFE_KEYWORDS]


def _normalize_arabic(text: str) -> str:
    text = _RE_DIACRITICS.sub("", text)  # precompiled
    text = text.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا")
    text = text.replace("ى", "ي").replace("ة", "ه")
    return text.strip().lower()


async def route_query(text: str) -> Tuple[str | None, str | None]:
    """Routes the query using a hybrid approach:
    1. Fast-path regex checks for greetings, unsafe actions, and out-of-scope items.
    2. Deep LLM zero-shot classification if regex checks are inconclusive.

    Returns:
        (response_text, intent) if non-legal (routed statically), or (None, "LEGAL") if legal.
    """
    normalized = _normalize_arabic(text)

    # 1. Fast Path Regex Checks (precompiled patterns)
    for pattern in _GREETING_PATTERNS_COMPILED:
        if pattern.search(normalized):
            return random.choice(GREETING_RESPONSES), "GREETING"

    for pattern in _UNSAFE_KEYWORD_PATTERNS_COMPILED:
        if pattern.search(normalized):
            return random.choice(UNSAFE_RESPONSES), "UNSAFE"

    for pattern in _OUT_OF_SCOPE_PATTERNS_COMPILED:
        if pattern.search(normalized):
            return random.choice(OUT_OF_SCOPE_RESPONSES), "OUT_OF_SCOPE"

    # Single word fast path (to reject short garbage or greetings)
    words = normalized.split()
    if len(words) <= 1 and len(normalized) > 0:
        legal_terms = ["قانون", "عقد", "حق", "مادة", "طلاق", "إيجار", "سرقة", "قتل", "ضرب", "شركة", "استقالة", "عمل"]
        if not any(term in normalized for term in legal_terms):
            return random.choice(OUT_OF_SCOPE_RESPONSES), "OUT_OF_SCOPE"

    # 2. Deep LLM Classification Fallback
    try:
        classifier_system_prompt = (
            "You are a strict Egyptian Legal RAG intent classifier. Your task is to analyze user questions "
            "and classify them into exactly one of these categories: LEGAL, GREETING, OUT_OF_SCOPE, UNSAFE. "
            "Respond with only the category name in capital letters."
        )
        
        classifier_user_prompt = f"""Classify this query according to these rules:
- GREETING: Conversational hello, welcome, how are you.
- UNSAFE: Assistance in committing crimes, evasion of laws, tax evasion, fraud, forgery.
- OUT_OF_SCOPE: Topics completely unrelated to Egyptian law (cooking, programming, sports, science, weather, etc.).
- LEGAL: Genuine legal questions about the Egyptian constitution, civil law, labor, tenancy, family status, criminal offenses, etc.

User query: "{text}"
Category:"""

        llm = get_llm_service()
        # max_tokens=5: classifier only needs one word (LEGAL/GREETING/OUT_OF_SCOPE/UNSAFE)
        response = await llm.generate(classifier_system_prompt, classifier_user_prompt, max_tokens=5)
        intent = response.strip().upper()

        logger.info("llm_classifier_routing", extra={"extra_fields": {"query": text, "intent": intent}})

        if "UNSAFE" in intent:
            return random.choice(UNSAFE_RESPONSES), "UNSAFE"
        elif "GREETING" in intent:
            return random.choice(GREETING_RESPONSES), "GREETING"
        elif "OUT_OF_SCOPE" in intent:
            return random.choice(OUT_OF_SCOPE_RESPONSES), "OUT_OF_SCOPE"
        elif "LEGAL" in intent:
            return None, "LEGAL"
            
    except Exception as e:
        logger.error(f"llm_classifier_routing_failed: {e}")

    # Fallback to LEGAL if LLM classification fails
    return None, "LEGAL"
