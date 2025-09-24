# Use slim Python base
FROM python:3.11-slim

# System deps for PDFs & OCR
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    poppler-utils \
    tesseract-ocr \
    libtesseract-dev \
    libleptonica-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Workdir
WORKDIR /app

# Copy only requirement files first (better layer caching)
COPY requirements.txt ./requirements.txt

# Install Python deps
RUN pip install --no-cache-dir -r requirements.txt

# Download spaCy model inside image (change to md if you want a smaller image)
RUN python -m spacy download en_core_web_md


# Copy app code
COPY . .

# Expose port
EXPOSE 8000

# Default envs (override in compose or at runtime)
ENV USE_LLM=true \
    OCR_DPI=300 \
    IMAGE_DOC_EMPTY_RATIO=0.6

# Run both API and UI via run_all.py (serves /ui and /docs on same port)
CMD ["python", "run_all.py"]
