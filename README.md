# TP2-CloudNative_AI_Sustainability_Proj

# DEPENDENCIES:
pip install playwright
python -m playwright install
pip install pdfplumber
pip install redis
pip install fastapi uvicorn redis

RUN:
# Run scraper manually
docker-compose run --rm scraper

# Just start PDF worker
docker-compose up pdf-worker

# Upload via API triggers the worker

# Run 3 PDF workers
docker-compose up --scale pdf-worker=3


docker-compose up
docker compose up --build

docker compose down

docker-compose stop (TO STOP)
