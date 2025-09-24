import io
import pdfplumber
from fastapi import UploadFile
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import LETTER

class PDFProcessor:
    def __init__(self, file_or_bytes):
        self._bytes = None
        if isinstance(file_or_bytes, UploadFile):
            self.file = file_or_bytes
        else:
            self.file = None
            self._bytes = file_or_bytes

    async def _bytes_async(self) -> bytes:
        if self._bytes is None:
            return await self.file.read()
        return self._bytes

    async def extract_pages(self) -> list[str]:
        pdf_bytes = await self._bytes_async()
        pages = []
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            for p in pdf.pages:
                pages.append(p.extract_text() or "")
        return pages

    async def extract_words_per_page(self):
        """list of pages, each page = list of word dicts from pdfplumber"""
        pdf_bytes = await self._bytes_async()
        pages_words = []
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            for p in pdf.pages:
                words = p.extract_words(x_tolerance=1, y_tolerance=3)
                # attach page height for coord transform
                for w in words:
                    w["_page_height"] = p.height
                pages_words.append(words)
        return pages_words

    async def page_sizes_pts(self):
        pdf_bytes = await self._bytes_async()
        sizes = []
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            for p in pdf.pages:
                sizes.append((p.width, p.height))
        return sizes

    def write_pdf(self, pages_text: list[str], out_path: str):
        c = canvas.Canvas(out_path, pagesize=LETTER)
        width, height = LETTER
        margin = 50
        line_h = 14
        for page_text in pages_text:
            y = height - margin
            for raw_line in page_text.splitlines():
                line = raw_line.strip()
                if not line:
                    y -= line_h
                    continue
                if y < margin:
                    c.showPage()
                    y = height - margin
                c.drawString(margin, y, line[:1200])
                y -= line_h
            c.showPage()
        c.save()
