import io, asyncio
from reportlab.pdfgen import canvas
from services.pdf_processor import PDFProcessor

def make_pdf_bytes(text: str) -> bytes:
    buf = io.BytesIO()
    c = canvas.Canvas(buf)
    c.drawString(100, 750, text)
    c.save()
    return buf.getvalue()

async def _extract(text):
    raw = make_pdf_bytes(text)
    proc = PDFProcessor(raw)
    pages = await proc.extract_pages()
    return "\n\n".join(pages)

def test_pdf_extract_simple():
    text = "John Doe lives in New York."
    out = asyncio.run(_extract(text))
    assert "John Doe" in out
