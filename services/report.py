import os, io, json, datetime
from typing import Dict, Any
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import LETTER

def build_report_json(filename: str, pii: Dict[str, Any], stats: Dict[str, int]) -> Dict[str, Any]:
    return {
        "file": filename,
        "generated_at": datetime.datetime.utcnow().isoformat() + "Z",
        "summary": {
            "total_categories": len((pii or {}).get("regex", {})) + len((pii or {}).get("spacy", {})),
            "counts": stats or {},
        },
        "details": pii or {},
    }

def write_report_pdf(report: Dict[str, Any], out_path: str):
    c = canvas.Canvas(out_path, pagesize=LETTER)
    w, h = LETTER
    x, y = 50, h - 60

    def line(txt: str):
        nonlocal y
        c.drawString(x, y, txt[:1200])
        y -= 16
        if y < 60:
            c.showPage()
            y = h - 60

    line("AI Privacy Assistant — Privacy Report")
    line(f"File: {report.get('file','')}")
    line(f"Generated at: {report.get('generated_at','')}")
    line("")
    line("Summary")
    for k, v in (report.get("summary", {}).get("counts", {}) or {}).items():
        line(f"- {k}: {v}")
    line("")

    # regex section
    regex = (report.get("details", {}) or {}).get("regex", {})
    if regex:
        line("Regex detections:")
        for cat, vals in regex.items():
            line(f"  • {cat}: {', '.join(map(str, vals))[:1000]}")
        line("")

    # spacy section
    spacy_ents = (report.get("details", {}) or {}).get("spacy", {})
    if spacy_ents:
        line("NER detections:")
        for lbl, vals in spacy_ents.items():
            line(f"  • {lbl}: {', '.join(map(str, vals))[:1000]}")
        line("")

    c.showPage()
    c.save()
