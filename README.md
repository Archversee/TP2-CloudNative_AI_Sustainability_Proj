# EcoEye: AI-Powered Sustainability Report Analysis Platform

**A cloud-native microservices platform that grants access to corporate ESG data through AI-powered analysis and semantic search.**

EcoEye transforms dense, technical sustainability reportsinto searchable, interpretable insights for non-expert stakeholders including retail investors, consumers, and community members. The system leverages Retrieval-Augmented Generation (RAG) architecture to extract, verify, and semantically index corporate environmental commitments.

### Prerequisites

**Required:**
- Docker Desktop with Kubernetes enabled
- `.env` file in project root:
```env
  GEMINI_API_KEY=your_gemini_api_key
  SUPABASE_URL=your_supabase_url
  SUPABASE_ANON_KEY=your_supabase_anon_key
```

**For Kubernetes Deployment:**
- Enable Kubernetes in Docker Desktop Settings

### Installation
```bash
# 1. Clone repository

# 2. Make deployment script executable
chmod +x deployment.sh

# 3. Create .env file with your credentials
.env
# Edit .env with your API keys

# 4. Deploy to Kubernetes (production-ready)
./deployment.sh start k8s
```
---

##  Key Features

### For End Users
-  **Natural Language Search** - Ask questions like "What are this company's Scope 1 emissions?"
-  **Interactive Dashboards** - Visualize ESG metrics, leaf ratings (1-5 scale), and trends
-  **Automated Analysis** - 57-second average processing time for 50-page reports
-  **Citation Tracking** - Every claim linked to source document pages
-  **Confidence Scoring** - AI-generated confidence levels (high/medium/low)

### For Developers
-  **Cloud-Native Architecture** - Kubernetes orchestration with self-healing
-  **Asynchronous Processing** - Redis-based task queues for parallel workflows
-  **AI-Powered Extraction** - 100+ ESG keyword taxonomy with intelligent prioritization
-  **Vector Embeddings** - 384-dimensional semantic search (all-MiniLM-L6-v2)
-  **Horizontal Scaling** - Independent scaling per microservice
-  **Secrets Management** - Kubernetes-native credential injection

---

##  System Architecture

### Architecture Diagram
```
┌─────────────┐
│   Frontend  │ ◄─── User uploads PDF
│  (Next.js)  │
└──────┬──────┘
       │
       ▼
┌─────────────┐      ┌─────────────┐
│     API     │◄────►│    Redis    │
│  (FastAPI)  │      │    Queue    │
└──────┬──────┘      └──────┬──────┘
       │                    │
       │                    ▼
       │         ┌────────────────────────────────┐
       │         │   Worker Pipeline              │
       │         │  ┌─────┐  ┌─────┐  ┌───────────┐
       │         │  │ PDF │─►│ AI  │─►│ Embedding │
       │         │  └─────┘  └─────┘  └───────────┘
       │         └────────────────────────────────┘
       │                    │
       ▼                    ▼
┌─────────────────────────────┐
│       Supabase              │
│  PostgreSQL + pgvector      │
└─────────────────────────────┘
```
| Service | Technology | Responsibilities | Resources |
|---------|-----------|------------------|-----------|
| **API Gateway** | FastAPI, Python 3.11 | RESTful endpoints, CORS, task orchestration, RAG coordination | 250-500m CPU, 256-512Mi RAM |
| **Frontend** | Next.js 14, TypeScript, Tailwind | PDF upload, search interface, dashboards, visualization | 250-500m CPU, 256-512Mi RAM |
| **PDF Worker** | pdfplumber, PyPDF2, Poppler | Text extraction, Scope 1/2/3 detection, 100+ keyword matching | 250-500m CPU, 256-512Mi RAM |
| **AI Worker** | Gemini 2.0 Flash | Claim prioritization (top 30), LLM auditing (temp=0.1), leaf rating | 250-500m CPU, 256-512Mi RAM |
| **Embeddings Worker** | all-MiniLM-L6-v2 | 384-dim vector generation, pgvector indexing | 500-1000m CPU, 512Mi-1Gi RAM |
| **Redis Queue** | Redis 7 Alpine | Asynchronous task queues, worker coordination | 100-250m CPU, 128-256Mi RAM |

### Cloud-Native Features

 **Containerization** - Docker multi-stage builds with minimal base images  
 **Health Monitoring** - Liveness/readiness probes with automatic restart  
 **Secrets Management** - Kubernetes Secrets with environment variable injection  
 **Service Discovery** - DNS-based internal communication  
 **Declarative Infrastructure** - YAML-based configuration (GitOps-ready)  
 **Fault Isolation** - Independent service failures don't cascade  
 **Horizontal Scaling** - `kubectl scale` for manual scaling, HPA-ready

##  Processing Pipeline

The system transforms unstructured PDFs into searchable knowledge through three stages:

### Stage 1: PDF Extraction & Keyword Detection

**PDF Worker responsibilities:**
- Filename parsing extracts company name and year
- Page-by-page text extraction using pdfplumber
- **100+ keyword taxonomy** organized into 7 categories:
  - **Emissions** (41): scope 1/2/3, GHG, carbon footprint, methane
  - **Targets** (29): net-zero, carbon neutral, SBTi, Paris Agreement
  - **Energy** (16): renewable energy, solar, wind, energy efficiency
  - **Resources** (12): water consumption, waste, circular economy
  - **Nature** (9): biodiversity, deforestation, ecosystem
  - **Social** (8): employee safety, diversity, human rights
  - **Standards** (10): GRI, TCFD, CDP, SASB, ISO 14001
- Pattern matching for Scope 1/2/3 emissions with 50+ regex patterns
- Context extraction (300-character windows around keywords)
- Output: Intermediate JSON with page-level metrics

### Stage 2: AI Auditing & Claim Prioritization

**AI Worker responsibilities:**
- **Intelligent claim filtering** - Reduces 87 claims → 30 high-priority claims
  - Scoring algorithm (0-100 points):
    - Keyword priority (0-40): High (net-zero, scope emissions), Medium (renewable energy), Low (general terms)
    - Evidence quality (0-30): Numeric data, commitment language, target years
    - Context richness (0-20): Text length and completeness
    - Metric availability (0-10): Associated emissions data
- **LLM auditing** via Gemini 2.0 Flash (temperature=0.1, maxTokens=4000)
- **Structured output** - JSON with leaf rating (1-5), claim reviews, confidence scores
- **Retry logic** - Exponential backoff (2s, 4s, 8s) for API rate limits (15 req/min free tier)
- Output: Processed JSON stored in Supabase `company_reports` table

**Prompt Engineering Structure:**
1. **Role Assignment** - "Audit sustainability claims for {company} ({year})"
2. **Structured Input** - JSON with deduplicated metrics (Scope 1/2/3, sampled to 50 entries) and claims with context
3. **Scoring Rubric** - Explicit 5-point scale (1=No evidence → 5=Fully supported)
4. **Output Format** - Strict JSON schema without markdown

### Stage 3: Vector Embedding & Indexing

**Embeddings Worker responsibilities:**
- **Model**: all-MiniLM-L6-v2 (22.7M parameters, 384 dimensions)
- Generates embeddings for each claim context (~50ms per embedding)
- Stores vectors in Supabase with pgvector extension
- Creates IVF-Flat index (100 clusters) for O(√n) similarity search

**Storage schema:**
```sql
CREATE TABLE document_chunks (
  id UUID PRIMARY KEY,
  document_id UUID,
  company TEXT,
  year INTEGER,
  page INTEGER,
  content TEXT,
  embedding vector(384),  -- pgvector type
  created_at TIMESTAMP
);

CREATE INDEX ON document_chunks 
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);
```

---

## RAG Architecture

### Semantic Search Pipeline

**1. Query Processing**
```python
# Convert natural language to 384-dim vector
model = SentenceTransformer('all-MiniLM-L6-v2')
query_embedding = model.encode(query, convert_to_numpy=True)
```

**2. Vector Similarity Search**
```sql
-- Cosine similarity via pgvector
SELECT *, 1 - (embedding <=> query_embedding) AS similarity
FROM document_chunks
WHERE similarity > 0.4  -- Threshold τ
ORDER BY similarity DESC
LIMIT 5;
```

**3. Context Assembly**
```python
# Format retrieved chunks with citations
context = [
  f"[Source: {company} {year} Report, Page {page}]\n{content}"
  for chunk in top_5_chunks
]
```

**4. LLM Generation**
```python
# Gemini 2.0 Flash generates grounded response
prompt = f"""
USER QUESTION: {query}

RELEVANT CONTEXT: {assembled_context}

Return JSON:
{{
  "answer": "factual response",
  "citations": [{{"company": "...", "year": 2024, "page": 5}}],
  "confidence": "high|medium|low"
}}
"""

response = gemini.generate(prompt, temperature=0.2)
```

---

##  Deployment

### Kubernetes (Production)
```bash
# Deploy with image rebuild (30 minutes first time)
./deployment.sh start k8s

# Deploy without rebuild (2 minutes)
./deployment.sh start k8s --skip-build

# Check status
./deployment.sh status k8s

# View logs
./deployment.sh logs k8s

# Stop (keeps namespace & secrets)
./deployment.sh stop k8s

# Complete cleanup
./deployment.sh stop k8s --cleanup
```

**Kubernetes Configuration:**
```yaml
# Namespace isolation
namespace: ecoeye

# Resource limits per pod
resources:
  requests:
    cpu: 250m
    memory: 256Mi
  limits:
    cpu: 500m
    memory: 512Mi

# High availability
replicas:
  api: 2        # Load balanced with NodePort
  frontend: 1
  workers: 1    # Each worker type

# Health checks
livenessProbe:
  httpGet:
    path: /health
    port: 8000
  initialDelaySeconds: 30
  periodSeconds: 10

readinessProbe:
  httpGet:
    path: /health
    port: 8000
  initialDelaySeconds: 10
  periodSeconds: 5
```

**Access URLs:**
- Frontend: http://localhost:30300
- API: http://localhost:30800
- API Docs: http://localhost:30800/docs

### Docker Compose (Development)
```bash
# Start all services
./deployment.sh start compose

# Stop (keeps volumes)
./deployment.sh stop compose

# Complete cleanup
./deployment.sh stop compose --cleanup
```

**Access URLs:**
- Frontend: http://localhost:3000
- API: http://localhost:8000
- API Docs: http://localhost:8000/docs

### Rebuild Commands
```bash
# Rebuild all images
./deployment.sh rebuild all

# Rebuild frontend only (updates API URL for deployment mode)
./deployment.sh rebuild frontend
```

##  Technical Stack

### Backend
- **Python 3.11** - Primary language
- **FastAPI 0.115.5** - High-performance API framework
- **Uvicorn 0.32.1** - ASGI server
- **Redis 7.2** - Task queue and caching
- **Supabase** - PostgreSQL 15 + pgvector 0.5.1
- **pdfplumber 0.11.4** - PDF text extraction
- **PyPDF2** - PDF utilities

### AI/ML
- **Google Gemini 2.0 Flash** - LLM for auditing and RAG generation
- **Sentence Transformers 3.3.1** - Embedding framework
- **all-MiniLM-L6-v2** - 384-dim semantic vectors (22.7M params)
- **pgvector 0.5.1** - Vector similarity extension for PostgreSQL

### Frontend
- **Next.js 14** - React framework (App Router)
- **React 18** - UI library
- **TypeScript 5.0** - Type safety
- **Tailwind CSS 3.4** - Utility-first styling
- **Axios** - HTTP client
- **Recharts** - Data visualization

### Infrastructure
- **Docker 24.0** - Containerization
- **Kubernetes 1.28** - Container orchestration
- **kubectl 1.28** - Cluster management
- **Bash** - Deployment automation

##  Development

### Environment Variables
```env
# API Keys
GEMINI_API_KEY=your_gemini_api_key_here
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your_supabase_anon_key

# Internal (auto-configured)
REDIS_URL=redis://redis:6379
NEXT_PUBLIC_API_URL=http://localhost:30800  # K8s
# NEXT_PUBLIC_API_URL=http://localhost:8000  # Compose
```

## 👥 Authors

**Group W Team 2**  
Singapore Institute of Technology / University of Glasgow

- Neo Sun Wei - 2400979@sit.singaporetech.edu.sg
- Jabier Ho Wei Le - 2402063@sit.singaporetech.edu.sg
- Haley Tan Hui Xin - 2402023@sit.singaporetech.edu.sg
- Gerald Tan Hau Qing - 2403349@sit.singaporetech.edu.sg

Built for Dell Cloud Native Award Competition 2026
