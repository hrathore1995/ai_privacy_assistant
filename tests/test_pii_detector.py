from services.pii_detector import PIIDetector

def test_regex_email_phone():
    txt = "Email: a@b.com, Phone: +1 202-555-0199"
    det = PIIDetector(txt)
    res = det.detect_all()
    assert "a@b.com" in res["regex"].get("email", [])
    assert any("202" in p for p in res["regex"].get("phone", []))

def test_spacy_person_place():
    txt = "John Doe moved to New York."
    det = PIIDetector(txt)
    res = det.detect_all()
    assert "PERSON" in res["spacy"]
    assert "GPE" in res["spacy"]
    # llm may be disabled in tests; just check key exists
    assert "llm" in res
