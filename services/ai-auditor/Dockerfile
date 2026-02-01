FROM python:3.11-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1

COPY services/ai-auditor/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy shared code
COPY shared ./shared

# Copy AI auditor code
COPY services/ai-auditor/src/ ./src

ENV GEMINI_API_KEY=${GEMINI_API_KEY}
ENV API_URL=http://api:8000
ENV SUPABASE_URL=${SUPABASE_URL}
ENV SUPABASE_ANON_KEY=${SUPABASE_ANON_KEY}

CMD ["python", "src/auditor.py"]
