from services.redactor import make_overlay_pdf

def test_overlay_bytes():
    rects = [[(50, 50, 150, 80)]]
    sizes = [(612.0, 792.0)]  # US Letter
    buf = make_overlay_pdf(rects, sizes)
    data = buf.getvalue()
    assert isinstance(data, (bytes, bytearray))
    assert len(data) > 100
