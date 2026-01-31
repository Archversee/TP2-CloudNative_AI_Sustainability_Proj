FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for pdfplumber and fonts
RUN apt-get update && apt-get install -y \
    build-essential \
    poppler-utils \
    libfreetype6 \
    libjpeg-dev \
    libpng-dev \
    libtiff-dev \
    zlib1g-dev \
    fonts-liberation \
    fonts-dejavu \
    && rm -rf /var/lib/apt/lists/*

# Copy Python requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the processor script
COPY pdf_processor.py .

# Default command
CMD ["python", "pdf_processor.py"]
