FROM python:3.11-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    poppler-utils fonts-liberation fonts-dejavu \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY services/pdf-processor/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy shared code
COPY shared ./shared

# Copy PDF processor code
COPY services/pdf-processor/src/ ./src

CMD ["python", "src/processor.py"]
