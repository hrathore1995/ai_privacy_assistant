from typing import List, Dict, Any
from pdf2image import convert_from_bytes
from pytesseract import image_to_string, image_to_data, Output
from config import settings

class OCREngine:
    def __init__(self, dpi: int = None):
        self.dpi = dpi or settings.OCR_DPI

    def extract_pages(self, pdf_bytes: bytes) -> List[str]:
        imgs = convert_from_bytes(pdf_bytes, dpi=self.dpi)
        return [image_to_string(im) or "" for im in imgs]

    def extract_pages_with_boxes(self, pdf_bytes: bytes) -> List[Dict[str, Any]]:
        imgs = convert_from_bytes(pdf_bytes, dpi=self.dpi)
        out = []
        for im in imgs:
            data = image_to_data(im, output_type=Output.DICT)
            words = []
            for i in range(len(data["text"])):
                t = (data["text"][i] or "").strip()
                if not t: continue
                words.append({"text": t, "x": data["left"][i], "y": data["top"][i],
                              "w": data["width"][i], "h": data["height"][i]})
            out.append({"text": "\n".join(w["text"] for w in words),
                        "width_px": im.width, "height_px": im.height, "words": words})
        return out
