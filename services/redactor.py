import io
from typing import List, Dict, Tuple
from reportlab.pdfgen import canvas
from PyPDF2 import PdfReader, PdfWriter

# ---------- helpers ----------
def _norm(s: str) -> str:
    return " ".join(s.lower().split())

def _find_seq_boxes_pdfplumber(words, target: str) -> List[Tuple[float,float,float,float]]:
    # words from pdfplumber.extract_words: has x0,x1,top,bottom,_page_height
    if not words:
        return []
    target_norm = _norm(target)
    toks = [w["text"] for w in words]
    toks_norm = [_norm(t) for t in toks]

    boxes = []
    n = len(toks_norm)
    for i in range(n):
        buf = ""
        acc = []
        for j in range(i, n):
            buf = f"{buf} {toks_norm[j]}".strip() if buf else toks_norm[j]
            acc.append(words[j])
            if buf == target_norm:
                x0 = min(float(w["x0"]) for w in acc)
                x1 = max(float(w["x1"]) for w in acc)
                top = min(float(w["top"]) for w in acc)
                bottom = max(float(w["bottom"]) for w in acc)
                page_h = float(acc[0]["_page_height"])
                y = page_h - bottom
                h = bottom - top
                boxes.append((x0, y, x1, y + h))
                break
    return boxes

def _find_seq_boxes_ocr(ocr_words, target: str, img_w: int, img_h: int, page_w: float, page_h: float) -> List[Tuple[float,float,float,float]]:
    # ocr_words have x,y,w,h in pixels, origin top-left; pdf is bottom-left
    if not ocr_words:
        return []
    target_norm = _norm(target)
    toks = [w["text"] for w in ocr_words]
    toks_norm = [_norm(t) for t in toks]

    sx = page_w / max(1, img_w)
    sy = page_h / max(1, img_h)

    boxes = []
    n = len(toks_norm)
    for i in range(n):
        buf = ""
        acc = []
        for j in range(i, n):
            buf = f"{buf} {toks_norm[j]}".strip() if buf else toks_norm[j]
            acc.append(ocr_words[j])
            if buf == target_norm:
                x0_px = min(w["x"] for w in acc)
                x1_px = max(w["x"] + w["w"] for w in acc)
                y_top_px = min(w["y"] for w in acc)
                y_bot_px = max(w["y"] + w["h"] for w in acc)
                # map px → points and flip y
                x0 = x0_px * sx
                x1 = x1_px * sx
                y0 = page_h - (y_bot_px * sy)
                y1 = page_h - (y_top_px * sy)
                boxes.append((x0, y0, x1, y1))
                break
    return boxes

# ---------- public api ----------
def rects_for_targets(words_per_page, targets_per_page: List[List[str]]) -> List[List[Tuple[float,float,float,float]]]:
    out = []
    pages = max(len(words_per_page), len(targets_per_page))
    for pi in range(pages):
        page_words = words_per_page[pi] if pi < len(words_per_page) else []
        page_targets = targets_per_page[pi] if pi < len(targets_per_page) else []
        rects = []
        for t in page_targets:
            rects.extend(_find_seq_boxes_pdfplumber(page_words, t))
        out.append(rects)
    return out

def rects_for_targets_ocr(ocr_pages: List[Dict], targets_per_page: List[List[str]], page_sizes_pts: List[Tuple[float,float]]) -> List[List[Tuple[float,float,float,float]]]:
    out = []
    pages = max(len(ocr_pages), len(targets_per_page), len(page_sizes_pts))
    for pi in range(pages):
        ocr_page = ocr_pages[pi] if pi < len(ocr_pages) else None
        targets = targets_per_page[pi] if pi < len(targets_per_page) else []
        if not ocr_page:
            out.append([])
            continue
        img_w = ocr_page["width_px"]
        img_h = ocr_page["height_px"]
        pdf_w, pdf_h = page_sizes_pts[pi]
        rects = []
        for t in targets:
            rects.extend(_find_seq_boxes_ocr(ocr_page["words"], t, img_w, img_h, pdf_w, pdf_h))
        out.append(rects)
    return out

def make_overlay_pdf(rects_per_page, page_sizes_pts) -> io.BytesIO:
    buf = io.BytesIO()
    c = None
    for (rects, size) in zip(rects_per_page, page_sizes_pts):
        w, h = size
        if c is None:
            c = canvas.Canvas(buf, pagesize=(w, h))
        else:
            c.setPageSize((w, h))
        c.setFillColorRGB(0, 0, 0)
        for (x0, y0, x1, y1) in rects:
            c.rect(x0, y0, (x1 - x0), (y1 - y0), fill=1, stroke=0)
        c.showPage()
    if c is None:  # empty doc
        c = canvas.Canvas(buf)
    c.save()
    buf.seek(0)
    return buf

def merge_overlay(original_bytes: bytes, overlay_pdf: io.BytesIO, out_path: str):
    reader = PdfReader(io.BytesIO(original_bytes))
    overlay = PdfReader(overlay_pdf)
    writer = PdfWriter()
    for i, page in enumerate(reader.pages):
        if i < len(overlay.pages):
            page.merge_page(overlay.pages[i])
        writer.add_page(page)
    with open(out_path, "wb") as f:
        writer.write(f)
