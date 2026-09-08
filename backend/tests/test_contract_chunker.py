from app.services.contract_chunker import chunk_contract


def test_chunk_by_article_markers():
    text = """
    المادة 1: يلتزم الطرف الأول بتسليم الوحدة في الموعد المحدد.

    المادة 2: يلتزم الطرف الثاني بدفع الإيجار شهرياً في حدود خمسة أيام من بداية الشهر.

    المادة 3: مدة هذا العقد سنة واحدة قابلة للتجديد بموافقة الطرفين.
    """
    chunks = chunk_contract(text)
    assert len(chunks) >= 2
    assert all(c.text.strip() for c in chunks)


def test_chunk_empty_text():
    assert chunk_contract("") == []


def test_chunk_paragraph_fallback():
    text = "هذا عقد بسيط بدون ترقيم.\n\nيحتوي على فقرتين منفصلتين بشكل واضح ومحدد لاختبار التقسيم الافتراضي للنص الطويل بما يكفي."
    chunks = chunk_contract(text, min_chunk_chars=10)
    assert len(chunks) >= 1
