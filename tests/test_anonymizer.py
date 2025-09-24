from services.anonymizer import Anonymizer

def test_mask_replacements():
    text = "John Doe lives in New York. Email john@x.com"
    detections = {
        "regex": {"email": ["john@x.com"]},
        "spacy": {"PERSON": ["John Doe"], "GPE": ["New York"]},
    }
    anon = Anonymizer(mode="mask")
    pages, mapping, stats = anon.anonymize_pages([text], detections)
    out = pages[0]
    assert "John Doe" not in out
    assert "john@x.com" not in out
    assert "<PERSON_" in out or "█" in out
