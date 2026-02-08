"""
EcoLens API with RAG Search Capabilities
"""
from fastapi import FastAPI, Form, HTTPException, UploadFile, File, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import sys
import uuid
from datetime import datetime
import os
import json
import re

sys.path.append('/app')
from shared.tasks import enqueue_task, get_queue_length
from shared.database import get_supabase_client

app = FastAPI(title="EcoLens API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
        allow_origins=[
        "http://localhost:3000", 
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# Request/Response Models
# ============================================================================

class SearchRequest(BaseModel):
    query: str
    company: Optional[str] = None
    year: Optional[int] = None
    match_threshold: Optional[float] = 0.4
    match_count: Optional[int] = 5

class Citation(BaseModel):
    company: str
    year: int
    page: int
    quote: str

class SearchResponse(BaseModel):
    question: str
    answer: str
    citations: List[Citation]
    confidence: str
    num_sources: int

# ============================================================================
# Health & Status Endpoints
# ============================================================================

@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "ecolens-api"}

@app.get("/api/status")
def get_status():
    """Check processing queue status."""
    return {
        "pdf_queue": get_queue_length("pdf_processing"),
        "audit_queue": get_queue_length("ai_audit"),
        "embeddings_queue": get_queue_length("embeddings")
    }

# ============================================================================
# Document Upload & Processing
# ============================================================================

@app.post("/api/upload")
async def upload_pdf(
    file: UploadFile = File(...),
    company: Optional[str] = Form(None),  
    year: Optional[int] = Form(None)      
):
    """Upload PDF with optional metadata override."""
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")
    
    doc_id = str(uuid.uuid4())
    file_dir = "/data/raw_pdfs"
    os.makedirs(file_dir, exist_ok=True)
    
    file_path = f"{file_dir}/{doc_id}.pdf"
    with open(file_path, "wb") as f:
        content = await file.read()
        f.write(content)
    
    task_company = company.strip() if company else None
    task_year = int(year) if year else None
    metadata_source = "api_provided" if (task_company and task_year) else "filename_parsed"
    
    task = {
        "id": doc_id,
        "filename": file.filename,  
        "path": file_path,
        "uploaded_at": datetime.utcnow().isoformat(),
        "company": task_company,   
        "year": task_year,         
        "metadata_source": metadata_source
    }
    
    enqueue_task("pdf_processing", task)
    
    return {
        "document_id": doc_id,
        "filename": file.filename,
        "company": task_company or "Will be parsed from filename",
        "year": task_year or "Will be parsed from filename",
        "metadata_source": metadata_source,
        "status": "queued",
        "message": f"PDF uploaded and queued for processing (metadata from {metadata_source})"
    }

@app.get("/api/documents/{doc_id}")
def get_document_status(doc_id: str):
    """Get processing status of a document."""
    supabase = get_supabase_client()
    
    # Check company_reports table
    result = supabase.table('company_reports').select('*').eq('document_id', doc_id).execute()
    
    if result.data:
        return {
            "document_id": doc_id,
            "status": "completed",
            "data": result.data[0]
        }
    else:
        return {
            "document_id": doc_id,
            "status": "processing",
            "message": "Document is being processed"
        }

# ============================================================================
# Company Data Endpoints
# ============================================================================

@app.get("/api/companies")
def list_companies():
    """List all processed companies."""
    supabase = get_supabase_client()
    result = supabase.table('company_reports').select('company, year, leaf_rating, scope1_total, scope2_total').execute()
    return {
        "companies": result.data,
        "total": len(result.data)
    }

@app.get("/api/companies/{company}")
def get_company(company: str, year: Optional[int] = None):
    """Get company details and sustainability overview."""
    supabase = get_supabase_client()
    
    query = supabase.table('company_reports').select('*').eq('company', company)
    
    if year:
        query = query.eq('year', year)
    else:
        # Get most recent year
        query = query.order('year', desc=True).limit(1)
    
    result = query.execute()
    
    if not result.data:
        raise HTTPException(status_code=404, detail=f"Company '{company}' not found")
    
    return result.data[0]

@app.get("/api/companies/{company}/history")
def get_company_history(company: str):
    """Get historical data for a company across multiple years."""
    supabase = get_supabase_client()
    
    result = supabase.table('company_reports')\
        .select('year, leaf_rating, scope1_total, scope2_total, ai_summary')\
        .eq('company', company)\
        .order('year', desc=False)\
        .execute()
    
    if not result.data:
        raise HTTPException(status_code=404, detail=f"No history found for '{company}'")
    
    return {
        "company": company,
        "history": result.data,
        "years_covered": len(result.data)
    }

# ============================================================================
# RAG Search Endpoints
# ============================================================================

def generate_query_embedding(query: str) -> List[float]:
    """Generate embedding for search query."""
    try:
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer('all-MiniLM-L6-v2')
        embedding = model.encode(query, convert_to_numpy=True)
        return embedding.tolist()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating embedding: {str(e)}")

def semantic_search(
    query: str,
    company: Optional[str] = None,
    year: Optional[int] = None,
    match_threshold: float = 0.7,
    match_count: int = 5
) -> List[dict]:
    """Perform semantic search on document chunks."""
    
    # Generate query embedding
    query_embedding = generate_query_embedding(query)
    
    supabase = get_supabase_client()
    
    try:
        # Call Supabase RPC function for vector search
        result = supabase.rpc(
            'search_documents',
            {
                'query_embedding': query_embedding,
                'match_threshold': match_threshold,
                'match_count': match_count,
                'filter_company': company,
                'filter_year': year
            }
        ).execute()
        
        return result.data or []
    
    except Exception as e:
        # If RPC doesn't exist, do manual search
        print(f"RPC search failed: {e}, falling back to manual search")
        return manual_vector_search(query_embedding, company, year, match_threshold, match_count)

def manual_vector_search(
    query_embedding: List[float],
    company: Optional[str],
    year: Optional[int],
    threshold: float,
    limit: int
) -> List[dict]:
    """Manual vector search if RPC not available."""
    supabase = get_supabase_client()
    
    # Get all chunks (with optional filters)
    query = supabase.table('document_chunks').select('*')
    
    if company:
        query = query.ilike('company', f'%{company}%')  
    if year:
        query = query.eq('year', year)
    
    result = query.limit(100).execute()  # Limit for performance
    
    # Calculate cosine similarity manually
    import numpy as np
    
    results = []
    for chunk in result.data:
        if not chunk.get('embedding'):
            continue
        
        # Cosine similarity
        emb = np.array(chunk['embedding'])
        query_emb = np.array(query_embedding)
        similarity = np.dot(emb, query_emb) / (np.linalg.norm(emb) * np.linalg.norm(query_emb))
        
        if similarity >= threshold:
            chunk['similarity'] = float(similarity)
            results.append(chunk)
    
    # Sort by similarity and limit
    results.sort(key=lambda x: x['similarity'], reverse=True)
    return results[:limit]

def generate_rag_response(query: str, context_chunks: List[dict]) -> dict:
    """Generate AI response using retrieved context chunks."""
    
    if not context_chunks:
        return {
            "answer": "I couldn't find relevant information to answer your question.",
            "citations": [],
            "confidence": "low"
        }
    
    # Build context from chunks
    context_text = "\n\n".join([
        f"[Source: {chunk['company']} {chunk['year']} Report, Page {chunk['page']}]\n{chunk['content']}"
        for chunk in context_chunks
    ])
    
    # Create prompt for Gemini
    prompt = f"""You are an ESG sustainability expert analyzing corporate sustainability reports.

USER QUESTION:
{query}

RELEVANT CONTEXT FROM REPORTS:
{context_text}

INSTRUCTIONS:
1. Answer the question based ONLY on the provided context
2. Include specific citations with company name, year, and page number
3. If the context doesn't fully answer the question, say so
4. Be precise and factual
5. Return your response in JSON format:

{{
  "answer": "Your detailed answer here",
  "citations": [
    {{"company": "...", "year": 2024, "page": 5, "quote": "relevant quote"}}
  ],
  "confidence": "high|medium|low"
}}

Respond with ONLY the JSON, no markdown or extra text."""

    # Call Gemini API
    import os
    import requests
    
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    if not gemini_api_key:
        raise HTTPException(status_code=500, detail="GEMINI_API_KEY not configured")
    
    url = f"https://generativelanguage.googleapis.com/v1/models/gemini-2.0-flash:generateContent?key={gemini_api_key}"
    
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.2,
            "maxOutputTokens": 2000
        }
    }
    
    try:
        response = requests.post(url, json=payload, timeout=30)
        response.raise_for_status()
        
        raw_text = response.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
        
        # Parse JSON response
        clean_text = re.sub(r'```json\s*|\s*```', '', raw_text)
        result = json.loads(clean_text)
        
        return result
    
    except Exception as e:
        return {
            "answer": f"Sorry, I encountered an error generating the response: {str(e)}",
            "citations": [],
            "confidence": "low"
        }

@app.post("/api/search", response_model=SearchResponse)
def search_documents(request: SearchRequest):
    """
    Semantic search across sustainability reports using RAG.
    
    Example:
    POST /api/search
    {
        "query": "What are CLCT's carbon emissions?",
        "company": "CLCT",
        "year": 2024
    }
    """
    
    # Step 1: Semantic search
    chunks = semantic_search(
        query=request.query,
        company=request.company,
        year=request.year,
        match_threshold=request.match_threshold,
        match_count=request.match_count
    )
    
    if not chunks:
        return SearchResponse(
            question=request.query,
            answer="No relevant information found in the database.",
            citations=[],
            confidence="none",
            num_sources=0
        )
    
    # Step 2: Generate answer with RAG
    rag_result = generate_rag_response(request.query, chunks)
    
    return SearchResponse(
        question=request.query,
        answer=rag_result.get("answer", ""),
        citations=[Citation(**c) for c in rag_result.get("citations", [])],
        confidence=rag_result.get("confidence", "unknown"),
        num_sources=len(chunks)
    )

@app.get("/api/search")
def search_documents_get(
    q: str = Query(..., description="Search query"),
    company: Optional[str] = Query(None, description="Filter by company name"),
    year: Optional[int] = Query(None, description="Filter by year"),
    threshold: float = Query(0.7, description="Similarity threshold (0-1)"),
    limit: int = Query(5, description="Max number of results")
):
    """
    GET version of semantic search (for easy testing).
    
    Example:
    GET /api/search?q=carbon+emissions&company=CLCT&year=2024
    """
    
    request = SearchRequest(
        query=q,
        company=company,
        year=year,
        match_threshold=threshold,
        match_count=limit
    )
    
    return search_documents(request)

# ============================================================================
# Additional RAG Endpoints
# ============================================================================

@app.get("/api/companies/{company}/claims")
def get_company_claims(company: str, year: Optional[int] = None):
    """Get all sustainability claims for a company."""
    supabase = get_supabase_client()
    
    query = supabase.table('company_reports').select('claims, year').eq('company', company)
    
    if year:
        query = query.eq('year', year)
    
    result = query.execute()
    
    if not result.data:
        raise HTTPException(status_code=404, detail=f"No claims found for '{company}'")
    
    # Extract and flatten claims
    all_claims = []
    for report in result.data:
        year = report['year']
        for claim in report.get('claims', []):
            all_claims.append({
                **claim,
                'year': year
            })
    
    return {
        "company": company,
        "claims": all_claims,
        "total": len(all_claims)
    }

@app.get("/api/compare")
def compare_companies(
    companies: str = Query(..., description="Comma-separated company names"),
    metric: str = Query("leaf_rating", description="Metric to compare (leaf_rating, scope1_total, scope2_total)")
):
    """
    Compare sustainability metrics across multiple companies.
    
    Example:
    GET /api/compare?companies=CLCT,SGX Group&metric=leaf_rating
    """
    
    company_list = [c.strip() for c in companies.split(',')]
    
    supabase = get_supabase_client()
    
    results = []
    for company in company_list:
        # Get most recent data
        result = supabase.table('company_reports')\
            .select(f'company, year, {metric}')\
            .eq('company', company)\
            .order('year', desc=True)\
            .limit(1)\
            .execute()
        
        if result.data:
            results.append(result.data[0])
    
    if not results:
        raise HTTPException(status_code=404, detail="No data found for specified companies")
    
    # Sort by metric
    results.sort(key=lambda x: x.get(metric, 0) or 0, reverse=True)
    
    return {
        "metric": metric,
        "comparison": results
    }

# ============================================================================
# Utility Endpoints
# ============================================================================

@app.get("/api/stats")
def get_statistics():
    """Get overall system statistics."""
    supabase = get_supabase_client()
    
    # Count reports
    reports = supabase.table('company_reports').select('id', count='exact').execute()
    
    # Count chunks
    chunks = supabase.table('document_chunks').select('id', count='exact').execute()
    
    # Get unique companies
    companies = supabase.table('company_reports').select('company').execute()
    unique_companies = len(set(c['company'] for c in companies.data))
    
    return {
        "total_reports": reports.count,
        "total_chunks": chunks.count,
        "unique_companies": unique_companies,
        "avg_chunks_per_report": chunks.count / reports.count if reports.count > 0 else 0
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)