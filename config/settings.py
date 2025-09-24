# config/settings.py
from dotenv import load_dotenv
import os

load_dotenv()  # <-- must come BEFORE os.getenv calls

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
USE_LLM = os.getenv("USE_LLM", "true").lower() == "true"
OCR_DPI = int(os.getenv("OCR_DPI", "300"))
IMAGE_DOC_EMPTY_RATIO = float(os.getenv("IMAGE_DOC_EMPTY_RATIO", "0.6"))
