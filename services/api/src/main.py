from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
import sys
import uuid
from datetime import datetime
import os

sys.path.append('/app')
from shared.tasks import enqueue_task, get_queue_length
from shared.database import get_supabase_client

app = FastAPI(title="EcoLens API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health_check():
    return {"status": "healthy"}

@app.get("/api/status")
def get_status():
    """Check queue status."""
    return {
        "pdf_queue": get_queue_length("pdf_processing"),
        "audit_queue": get_queue_length("ai_audit"),
        "embeddings_queue": get_queue_length("embeddings")
    }

@app.post("/api/upload")
async def upload_pdf(file: UploadFile = File(...)):
    """
    Upload PDF and trigger processing pipeline.
    
    Flow:
    1. Save PDF
    2. Enqueue PDF processing task
    3. Worker processes it and enqueues audit task
    4. Audit worker processes and enqueues embeddings task
    """
    # Generate unique ID
    doc_id = str(uuid.uuid4())
    
    file_dir = "/data/raw_pdfs"
    os.makedirs(file_dir, exist_ok=True)
    
    # Save uploaded file
    file_path = f"{file_dir}/{doc_id}.pdf"
    with open(file_path, "wb") as f:
        content = await file.read()
        f.write(content)
    
    # Create task
    task = {
        "id": doc_id,
        "filename": file.filename,
        "path": file_path,
        "uploaded_at": datetime.utcnow().isoformat()
    }
    
    # Enqueue for PDF processing
    enqueue_task("pdf_processing", task)
    
    return {
        "document_id": doc_id,
        "status": "queued",
        "message": "PDF uploaded and queued for processing"
    }

@app.get("/api/documents/{doc_id}")
def get_document_status(doc_id: str):
    """Get processing status of a document."""
    supabase = get_supabase_client()
    
    # Check company_reports table
    result = supabase.table('company_reports').select('*').eq('id', doc_id).execute()
    
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

@app.get("/api/companies")
def list_companies():
    """List all processed companies."""
    supabase = get_supabase_client()
    result = supabase.table('company_reports').select('company, year, leaf_rating').execute()
    return result.data

@app.get("/api/companies/{company}")
def get_company(company: str, year: int = None):
    """Get company details."""
    supabase = get_supabase_client()
    query = supabase.table('company_reports').select('*').eq('company', company)
    if year:
        query = query.eq('year', year)
    result = query.execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Company not found")
    return result.data[0]