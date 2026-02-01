FROM python:3.11-slim

WORKDIR /app

# Copy requirements first (cache layer)
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# Copy the AI auditor script
COPY ai_auditor.py .

# Ensure data directories exist (matches your script)
RUN mkdir -p /data/raw_pdfs /data/processed_json

# Set default command
CMD ["python", "ai_auditor.py"]
