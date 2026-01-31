# TP2-CloudNative_AI_Sustainability_Proj

DEPENDENCIES:

pip install playwright
python -m playwright install
pip install pdfplumber

RUN:
# Step 1: scrape
docker compose up --build scraper

# Step 2: process
docker compose up --build pdf_processor


docker-compose stop (TO STOP)



