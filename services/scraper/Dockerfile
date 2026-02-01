FROM mcr.microsoft.com/playwright/python:v1.46.0-jammy

WORKDIR /app

ENV PYTHONUNBUFFERED=1

# Copy Python dependencies
COPY services/scraper/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Ensure browsers are installed
RUN playwright install

# Copy shared code
COPY shared ./shared

# Copy scraper code
COPY services/scraper/src/ ./src

CMD ["python", "src/scraper.py"]
