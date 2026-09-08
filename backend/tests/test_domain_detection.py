from app.graphs.legal_assistant.nodes_domain import detect_domain_node
from app.schemas.chat import LegalDomain


def test_labor_domain_detection():
    state = {"question": "هل يجوز فصل العامل بدون سبب؟", "warnings": []}
    result = detect_domain_node(state)
    assert result["domain"] == LegalDomain.LABOR
    assert result["category_filter"] is None


def test_tenancy_domain_detection():
    state = {"question": "لو طردوني من الشقة أعمل إيه؟", "warnings": []}
    result = detect_domain_node(state)
    assert result["domain"] == LegalDomain.TENANCY


def test_family_domain_detection():
    state = {"question": "إمتى تسقط الحضانة؟", "warnings": []}
    result = detect_domain_node(state)
    assert result["domain"] == LegalDomain.FAMILY


def test_unknown_domain_fallback():
    state = {"question": "ما هو الطقس اليوم؟", "warnings": []}
    result = detect_domain_node(state)
    assert result["domain"] == LegalDomain.UNKNOWN
    assert result["category_filter"] is None
