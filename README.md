````markdown
# AI Privacy Assistant — PDF Anonymizer (End‑to‑End)

A production‑style, **AI data privacy assistant** that detects and anonymizes Personally Identifiable Information (PII) in PDFs. It supports:

- **Regex + spaCy NER (primary)** detection with **LLM assist** for context‑dependent PII.
- **Three anonymization modes** on rebuilt PDFs: `mask`, `redact`, and `pseudo` (realistic replacements).
- **Layout‑preserving redaction** (overlay of black boxes) for native and scanned PDFs (OCR).
- A **modern,single‑page UI** (HTML/JS) that runs on the **same port** as the API.
- **One‑command Docker run** with reproducible dependencies.

> **Why this project?** Most “PII anonymizers” are either toy scripts or single‑tech demos. This repo showcases **industry‑grade architecture**: hybrid detection (regex+NER+LLM), OCR fallback, visual overlays on original PDFs, reporting bundles, clean services, tests, and Dockerized reproducibility.

---

## Features
- **Detectors**
  - **Regex** for emails/phones/IDs (high precision).
  - **spaCy NER** for PERSON/ORG/GPE, etc.
  - **LLM** to catch context‑dependent PII (disabled by default unless `OPENAI_API_KEY` is set).
- **Anonymization Modes** (rebuilt PDFs)
  - `mask`: replace with angle‑bracket tags (e.g., `<PERSON_1>`)
  - `redact`: black bars in rebuilt document text
  - `pseudo`: realistic replacements via Faker
- **Layout‑Preserving Redaction**
  - Draw **black boxes** on **original PDF** (visual overlay).
  - Works for **native PDFs** and **scanned PDFs** via **Tesseract OCR** boxes mapped to PDF coordinates.
- **OCR Fallback**
  - If a PDF is image‑heavy, the app automatically switches to OCR detection.
- **UI/UX**
  - drag‑and‑drop upload, activity log, toasts.
  - Overlay toggle auto‑locks Mode to `redact` and disables “Include report”.
- **Reports**
  - Download a **ZIP bundle** with: sanitized PDF, `privacy_report.json`, and `privacy_report.pdf`.
- **One‑Port Run**
  - `run_all.py` serves **/ui** (frontend) and the API on **port 8000**.
- **Dockerized**
  - `docker compose up --build` — no local setup headache.

---

## Architecture Overview

```text
┌─────────────────┐                                ┌─────────────────┐
│  Frontend (UI)  │  upload PDF (fetch POST)  ───▶ │   FastAPI API   │
│   /ui HTML/JS   │                                │ /upload-pdf     │
└─────────────────┘                                │ /anonymize-pdf  │
                                                   │ /redact-pdf     │
                                                   │ /anonymize-...  │
                                                   └────────┬────────┘
                                                            │
                                                            │ detection (regex + spaCy + LLM*)
                                                            ▼
                                                   ┌────────────────────┐
                                                   │   Services Layer   │
                                                   │  pdf_processor     │
                                                   │  pii_detector      │
                                                   │  anonymizer        │
                                                   │  redactor (overlay)│
                                                   │  ocr_engine        │
                                                   │  report            │
                                                   └─────────┬──────────┘
                                                             │
                                                         Filesystem
                                                             │
                                                             ▼
                                                     outputs/*.pdf/.zip
````

*Regex + spaCy run locally and are the **primary** detectors. LLM assist is optional.*

---

## File Structure

```text
.
├── config/
│   └── settings.py            # env-driven config (loads .env)
├── services/
│   ├── anonymizer.py          # mask / redact / pseudo (Faker)
│   ├── ocr_engine.py          # pdf2image + Tesseract OCR
│   ├── pii_detector.py        # regex + spaCy + optional LLM
│   ├── pdf_processor.py       # text + word boxes + write PDFs
│   ├── redactor.py            # layout-preserving overlay boxes
│   └── report.py              # JSON + PDF reports
├── utils/
│   └── regex_patterns.py      # compiled regex patterns
├── frontend/
│   └── index.html             # Amazon-style SPA UI
├── outputs/
│   └── .gitkeep               # generated PDFs/ZIPs land here
├── tests/                     # (optional) pytest smoke tests
├── .gitignore
├── docker-compose.yml
├── Dockerfile
├── requirements.txt           # curated deps for Docker
├── run_all.py                 # serves UI + API on same port
├── main.py                    # FastAPI app & endpoints
└── README.md
```

---

## Requirements

* macOS / Linux (Windows WSL works too)
* Python **3.9+** (local dev) — Docker image uses **3.11**
* **Tesseract** & **poppler** (for local OCR & PDF rendering)

  * macOS: `brew install tesseract poppler`
* For Docker: **Docker Desktop** (includes Compose v2)

---

## Setup & Run (Local, no Docker)

### 1) Create venv & install

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python -m spacy download en_core_web_md   # or en_core_web_lg (larger)
```

### 2) Environment

Create `.env` in project root (at minimum):

```env
OPENAI_API_KEY=sk-...        # optional; required only if you want LLM assist
USE_LLM=true                 # set true only if you want LLM to run
SPACY_MODEL=en_core_web_md   # or en_core_web_lg
OCR_DPI=300
IMAGE_DOC_EMPTY_RATIO=0.6
```

> If `OPENAI_API_KEY` is missing or `USE_LLM=false`, you’ll see `llm disabled` in the detection summary — that’s expected.

### 3) Run UI + API on one port

```bash
python run_all.py
# UI: http://127.0.0.1:8000/ui/
# API docs: http://127.0.0.1:8000/docs
```

> The root path `/` redirects to `/ui/`. Health check is at `/health`.

---

## Setup & Run (Docker)

### 1) Prepare

* Ensure Docker Desktop is installed and running
* Remove `version:` line from `docker-compose.yml` if you see a warning

### 2) Build & run

```bash
export OPENAI_API_KEY=sk-...   # optional (for LLM)
docker compose up --build
# Open http://localhost:8000/ui/
```

**Notes**

* The Dockerfile installs \`\` for faster builds. Ensure `SPACY_MODEL=en_core_web_md` (default) or switch both Dockerfile and env to `lg` if you need extra accuracy.
* Volumes mount `frontend/` and `outputs/` so you can iterate and keep artifacts on host.

---

## Using the App

1. **Upload PDF** (drag & drop or choose file)
2. Click **Analyze PII** to see findings:

   * **Regex** section: exact matches (emails, phones, etc.)
   * **NER (spaCy)**: detected entities (PERSON/ORG/GPE…)
   * **LLM note**: shows `llm disabled` or a short contextual summary if enabled
3. Choose **Mode** (`mask` | `redact` | `pseudo`) and options:

   * **Preserve layout (overlay)** → forces **Redact** and disables **Include report**
   * **Include report (ZIP)** → sanitized PDF + JSON/PDF report
4. Click **Anonymize PDF** → file downloads automatically

---

## API Endpoints (FastAPI)

* `POST /upload-pdf/` → JSON detection summary (no file saved)
* `POST /anonymize-pdf/` → Rebuilt sanitized PDF (mode via `Form('mode')`)
* `POST /redact-pdf/` → Visual overlay of black boxes on **original PDF**
* `POST /anonymize-bundle/` → ZIP with sanitized PDF + JSON/PDF reports
* `GET /ui/` → Frontend
* `GET /health` → `{ "message": "backend is running" }`

**Request example**

```bash
curl -F "file=@/path/to/file.pdf" -F "mode=mask" http://127.0.0.1:8000/anonymize-pdf/
```

---

## Configuration

All env is read via `config/settings.py` (loads `.env` first):

* `OPENAI_API_KEY` — enables LLM assist (optional)
* `OPENAI_MODEL` — default `gpt-4o-mini`
* `USE_LLM` — `true|false` (default `true`)
* `SPACY_MODEL` — `en_core_web_md` (default) or `en_core_web_lg`
* `OCR_DPI` — DPI for pdf2image (default 300)
* `IMAGE_DOC_EMPTY_RATIO` — threshold (0–1) to consider a PDF “image‑heavy” and switch to OCR (default 0.6)

> **Policy**: Regex + spaCy are **primary**; LLM is an **assist/booster**. You can switch to other policies if desired.

---

## Detection Policies (optional extension)

You can add a `DETECTION_POLICY` flag to route detection:

* `assist` (default): regex+NER, LLM adds context
* `primary`: LLM first, regex/spaCy validate
* `audit`: regex+NER only; LLM double‑checks before final action
* `off`: no LLM at all

---

## Security & Privacy Notes

* **Local‑first**: Regex and spaCy run locally; OCR runs locally; no data leaves the machine unless `USE_LLM=true`.
* **LLM**: If enabled, text chunks are sent to the LLM provider (OpenAI). Ensure this aligns with your data policy.
* **Files**: Outputs are saved under `outputs/`. You can disable saving or pipe to S3/GCS in production.
* **Overlay redaction**: Draws boxes on top; underlying text persists in the PDF layer. For compliance that requires text removal, implement **hard redaction** (PyMuPDF) — see Roadmap.

---

## Troubleshooting

* **“bytes‑like object required” on Analyze**: Ensure `/upload-pdf/` reads `raw = await file.read()` and passes **bytes** to `PDFProcessor(raw)`.
* **Model not found: en\_core\_web\_lg**: Either install `lg` or set `SPACY_MODEL=en_core_web_md` (Docker uses `md`).
* **Tesseract not found** (local): `brew install tesseract` (macOS). Ensure `which tesseract` shows a valid path.
* **Compose warning**: Remove `version:` from `docker-compose.yml`.
* **LibreSSL warning** (macOS system Python): harmless; use venv or Docker.

---

## Roadmap / Ideas

* **Hard redaction** (PyMuPDF) that truly removes underlying text
* **Policy YAML** to enable/disable specific entity categories
* **Per‑page targeting** (page‑aware detection and redaction)
* **Streaming progress** and large PDF chunking
* **Batch uploads** + job queue (Redis/Celery)
* **Enterprise connectors** (S3, GCS, SharePoint)

---

## Contributing

PRs welcome. Please run lint/tests and include before/after screenshots or sample PDFs when changing detection/redaction logic.

---

## License

MIT — do what you want, but **no warranty**. Verify anonymization for your data and compliance context.

---

## Quick Start Cheat‑Sheet

```bash
# Local
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python -m spacy download en_core_web_md
# .env: set OPENAI_API_KEY if you want LLM
python run_all.py   # http://127.0.0.1:8000/ui/

# Docker
export OPENAI_API_KEY=sk-...   # optional
docker compose up --build      # http://localhost:8000/ui/
```

```
```
