# TP2-CloudNative_AI_Sustainability_Proj
# TO RUN:
# 1. Compose the microservice containers
docker-compose up
docker compose up --build

# 2. RUN Frontend
localhost:3000

# 3. Free resources
docker compose down
docker-compose stop (TO STOP)

# TEST BACKEND APIS
http://localhost:8000/docs#/


# semantic search JSON
{
  "query": "what is the renewable energy claim",
  "company": "Opella Sustainability Report",
  "year": 2024,
  "match_threshold": 0.5,
  "match_count": 5
}