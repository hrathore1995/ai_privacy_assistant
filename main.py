import os
import uuid
import json
import zipfile
from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import FileResponse
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from services.pdf_processor import PDFProcessor
from services.pii_detector import PIIDetector
from services.anonymizer import Anonymizer
from services.redactor import (
    rects_for_targets,
    rects_for_targets_ocr,
    make_overlay_pdf,
    merge_overlay,
)
from services.ocr_engine import OCREngine
from services.report import build_report_json, write_report_pdf

load_dotenv()

app = FastAPI()

# allow local ui to call the api
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

OUT_DIR = "outputs"
os.makedirs(OUT_DIR, exist_ok=True)


@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse(url="/ui/")

@app.get("/health")
def health():
    return {"message": "backend is running"}


# analysis only (JSON)
@app.post("/upload-pdf/")
async def upload_pdf(file: UploadFile = File(...)):
    try:
        if not file.filename.lower().endswith(".pdf"):
            return {"error": "only pdf files supported"}

        raw = await file.read()  # <- read bytes up-front
        pages = await PDFProcessor(raw).extract_pages()  # pass bytes, not UploadFile
        full_text = "\n\n".join(pages)

        pii = PIIDetector(full_text).detect_all()
        return {
            "filename": file.filename,
            "extracted_text": full_text,
            "pii_detection": pii,
        }
    except Exception as e:
        return {"error": str(e)}



# anonymize and return a rebuilt PDF (mask/redact/pseudo)
@app.post("/anonymize-pdf/")
async def anonymize_pdf(
    mode: str = Form("mask"),  # mask | redact | pseudo
    file: UploadFile = File(...),
):
    try:
        if not file.filename.lower().endswith(".pdf"):
            return {"error": "only pdf files supported"}

        raw = await file.read()
        pages = await PDFProcessor(raw).extract_pages()
        full_text = "\n\n".join(pages)

        pii = PIIDetector(full_text).detect_all()

        anonymizer = Anonymizer(mode=mode)
        sanitized_pages, mapping, stats = anonymizer.anonymize_pages(pages, pii)

        out_path = os.path.join(OUT_DIR, f"sanitized_{uuid.uuid4().hex}.pdf")
        PDFProcessor(raw).write_pdf(sanitized_pages, out_path)

        return FileResponse(
            path=out_path,
            media_type="application/pdf",
            filename=f"sanitized_{file.filename}",
        )
    except Exception as e:
        return {"error": str(e)}


# layout-preserving redaction overlay (black boxes on original)
@app.post("/redact-pdf/")
async def redact_pdf(file: UploadFile = File(...)):
    try:
        if not file.filename.lower().endswith(".pdf"):
            return {"error": "only pdf files supported"}

        raw = await file.read()
        pdf_proc = PDFProcessor(raw)

        # extract text and word boxes
        words_per_page = await pdf_proc.extract_words_per_page()
        sizes_pts = await pdf_proc.page_sizes_pts()
        pages_text = await pdf_proc.extract_pages()
        full_text = "\n\n".join(pages_text)

        # decide if OCR path
        empty_ratio = sum(1 for t in pages_text if not t.strip()) / max(1, len(pages_text))
        use_ocr = empty_ratio > settings.IMAGE_DOC_EMPTY_RATIO

        if use_ocr:
            ocr = OCREngine(dpi=settings.OCR_DPI)
            ocr_pages = ocr.extract_pages_with_boxes(raw)
            ocr_text = "\n\n".join([p["text"] for p in ocr_pages])
            pii = PIIDetector(ocr_text).detect_all()

            targets = []
            for vals in (pii.get("regex") or {}).values():
                targets.extend(vals)
            for _, vals in (pii.get("spacy") or {}).items():
                targets.extend(vals)

            targets_per_page = [targets for _ in ocr_pages]
            rects = rects_for_targets_ocr(ocr_pages, targets_per_page, sizes_pts)
            overlay_buf = make_overlay_pdf(rects, sizes_pts)
        else:
            pii = PIIDetector(full_text).detect_all()

            targets = []
            for vals in (pii.get("regex") or {}).values():
                targets.extend(vals)
            for _, vals in (pii.get("spacy") or {}).items():
                targets.extend(vals)

            targets_per_page = [targets for _ in words_per_page]
            rects = rects_for_targets(words_per_page, targets_per_page)
            overlay_buf = make_overlay_pdf(rects, sizes_pts)

        out_path = os.path.join(OUT_DIR, f"redacted_{uuid.uuid4().hex}.pdf")
        merge_overlay(raw, overlay_buf, out_path)

        return FileResponse(
            path=out_path,
            media_type="application/pdf",
            filename=f"redacted_{file.filename}",
        )
    except Exception as e:
        return {"error": str(e)}


# anonymize and return a ZIP bundle (PDF + JSON + PDF report)
@app.post("/anonymize-bundle/")
async def anonymize_bundle(
    mode: str = Form("mask"),  # mask | redact | pseudo
    file: UploadFile = File(...),
):
    try:
        if not file.filename.lower().endswith(".pdf"):
            return {"error": "only pdf files supported"}

        raw = await file.read()
        pages = await PDFProcessor(raw).extract_pages()
        full_text = "\n\n".join(pages)

        pii = PIIDetector(full_text).detect_all()

        # anonymize
        anon = Anonymizer(mode=mode)
        sanitized_pages, mapping, stats = anon.anonymize_pages(pages, pii)

        base = uuid.uuid4().hex
        pdf_path = os.path.join(OUT_DIR, f"sanitized_{base}.pdf")
        PDFProcessor(raw).write_pdf(sanitized_pages, pdf_path)

        # report
        rep_json = build_report_json(file.filename, pii, stats)
        rep_json_path = os.path.join(OUT_DIR, f"report_{base}.json")
        with open(rep_json_path, "w") as f:
            json.dump(rep_json, f, indent=2)
        rep_pdf_path = os.path.join(OUT_DIR, f"report_{base}.pdf")
        write_report_pdf(rep_json, rep_pdf_path)

        # zip
        bundle_path = os.path.join(OUT_DIR, f"bundle_{base}.zip")
        with zipfile.ZipFile(bundle_path, "w", zipfile.ZIP_DEFLATED) as z:
            z.write(pdf_path, arcname=f"sanitized_{file.filename}")
            z.write(rep_json_path, arcname="privacy_report.json")
            z.write(rep_pdf_path, arcname="privacy_report.pdf")

        return FileResponse(
            path=bundle_path,
            media_type="application/zip",
            filename=f"privacy_bundle_{file.filename.replace('.pdf','')}.zip",
        )
    except Exception as e:
        return {"error": str(e)}
