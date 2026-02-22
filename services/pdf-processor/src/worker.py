import sys
import os
import json
import time
import re
import traceback
from datetime import datetime

sys.path.append('/app')

from shared.tasks import dequeue_task, enqueue_task
from shared.database import get_supabase_client
from processor import process_pdf

def normalize_company_name(name: str) -> str:
    """
    Normalize company names to a consistent canonical form.
    Handles aliases, casing, and report-specific noise.
    """
    if not name or not isinstance(name, str):
        return "Unknown"
    
    # Standardize casing and whitespace
    normalized = name.lower().strip()
    normalized = re.sub(r'[^a-z0-9\s]', ' ', normalized)
    normalized = ' '.join(normalized.split())
    
    # Final fallback: title case with cleanup
    return normalized.title() or "Unknown"


def extract_company_year_from_filename(filename: str):
    if not filename:
        return "Unknown", datetime.utcnow().year

    name = re.sub(r'\.pdf$', '', filename, flags=re.IGNORECASE)
    name = re.sub(r'[^a-zA-Z0-9\s_-]', ' ', name)
    name = re.sub(r'[_\-]+', ' ', name)

    name = ' '.join(name.split())

    year = None

    # Priority 1: Year at START
    m = re.match(r'^(19\d{2}|20\d{2})\s+(.+)$', name)
    if m:
        year = int(m.group(1))
        name = m.group(2)

    # Priority 2: Year at END
    if not year:
        m = re.match(r'^(.+?)\s+(19\d{2}|20\d{2})$', name)
        if m:
            name = m.group(1)
            year = int(m.group(2))

    # Priority 3: Year anywhere
    if not year:
        m = re.search(r'\b(19\d{2}|20\d{2})\b', name)
        if m:
            year = int(m.group(1))
            name = re.sub(rf'\b{year}\b', '', name)
        

    # Remove report noise
    company = re.sub(
        r'\b(sustainability|report|esg|annual|csr|corporate|responsibility)\b',
        '',
        name,
        flags=re.IGNORECASE
    )

    company = ' '.join(company.split())

    if not company:
        company = "Unknown"

    if not year:
        year = datetime.utcnow().year

    company = normalize_company_name(company)

    return company, year



def process_task(task):
    """
    Process a PDF task with robust metadata handling and normalization.
    
    Task structure expected:
    {
        "id": "uuid",
        "filename": "original.pdf",
        "path": "/path/to/file.pdf",
        "uploaded_at": "iso8601",
        "company": "optional_override",  
        "year": 2024,                  
        "metadata_source": "api_provided|filename_parsed"
    }
    """
    doc_id = task['id']
    file_path = task['path']
    original_filename = task.get('filename', f'{doc_id}.pdf')
    
    print(f" PROCESSING PDF TASK: {doc_id}")
    print(f" Original filename: {original_filename}")
    print(f" File path: {file_path}")
    print(f" Uploaded at: {task.get('uploaded_at', 'N/A')}")
    
    # Verify file exists
    if not os.path.exists(file_path):
        error_msg = f"File not found: {file_path}"
        print(error_msg)
        _log_error_to_supabase(doc_id, "file_not_found", error_msg)
        return False
    
    file_size = os.path.getsize(file_path)
    print(f"File exists ({file_size:,} bytes)")
    
    # API-provided metadata (most reliable)
    company = task.get('company')
    year = task.get('year')
    metadata_source = task.get('metadata_source', 'unknown')
    
    if company and year:
        print(f" Using API-provided metadata:")
        print(f"   Company: '{company}' | Year: {year}")
        metadata_source = "api_provided"
    
    #Filename parsing (fallback)
    else:
        print(f" No API metadata provided - parsing filename...")
        inferred_company, inferred_year = extract_company_year_from_filename(original_filename)
        company = company or inferred_company or "Unknown"
        year = year or inferred_year or datetime.utcnow().year
        metadata_source = "filename_parsed"
        print(f"   Inferred company: '{inferred_company}' | year: {inferred_year}")
    
    # Normalize company name to canonical form
    normalized_company = normalize_company_name(company)
    normalized_year = int(year)
    
    print(f"   Raw company: '{company}' → Normalized: '{normalized_company}'")
    print(f"   Raw year: {year} → Normalized: {normalized_year}")
    
    # Prevent year-in-company-name issues
    if str(normalized_year) in normalized_company:
        clean_company = re.sub(r'\b' + str(normalized_year) + r'\b', '', normalized_company)
        clean_company = ' '.join(clean_company.strip().split())
        if clean_company and clean_company != normalized_company:
            print(f"Removed year from company name: '{normalized_company}' → '{clean_company}'")
            normalized_company = clean_company
    
    try:
        # Run PDF processor
        result = process_pdf(file_path)
        
        # Override processor's metadata with normalized values
        result['company'] = normalized_company
        result['year'] = normalized_year
        result['document_id'] = doc_id
        result['original_filename'] = original_filename
        result['metadata_source'] = metadata_source
        
        # Add processing metadata
        result['processed_at'] = datetime.utcnow().isoformat()
        result['file_size_bytes'] = file_size
        
        print(f" PDF processed successfully!")
        print(f"   Company: {normalized_company}")
        print(f"   Year: {normalized_year}")
        print(f"   Claims extracted: {len(result.get('claims', []))}")
        print(f"   Pages processed: {len(result.get('pages', []))}")
        
    except Exception as e:
        error_msg = f"PDF processing failed: {str(e)}"
        print(f"\n{error_msg}")
        traceback.print_exc()
        _log_error_to_supabase(doc_id, "pdf_processing_error", error_msg)
        return False
    
    try:
        output_dir = "/data/intermediate_json"
        os.makedirs(output_dir, exist_ok=True)
        
        # Generate safe filename using NORMALIZED values
        safe_company = normalized_company.replace(' ', '_').replace('/', '_')
        output_filename = f"{safe_company}_{normalized_year}.json"
        output_path = os.path.join(output_dir, output_filename)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        
        print(f" Saved to: {output_path}")
        
    except Exception as e:
        error_msg = f"Failed to save intermediate JSON: {str(e)}"
        print(f"{error_msg}")
        traceback.print_exc()
        _log_error_to_supabase(doc_id, "save_error", error_msg)
        return False
    
    # Enqueue for next stage (AI Audit) with normalized metadata
    print(f" ENQUEUING FOR AI AUDIT")
    
    try:
        audit_task = {
            "id": doc_id,
            "filename": original_filename,
            "path": file_path,
            "intermediate_path": output_path,
            "company": normalized_company,  
            "year": normalized_year,       
            "document_id": doc_id,
            "metadata_source": metadata_source,
            "processed_at": time.time(),
            "claims_count": len(result.get('claims', []))
        }
        
        enqueue_task("ai_audit", audit_task)
        print(f"Enqueued to 'ai_audit' queue")
        print(f"Company: '{normalized_company}' | Year: {normalized_year}")
        
    except Exception as e:
        error_msg = f"Failed to enqueue audit task: {str(e)}"
        print(f"{error_msg}")
        traceback.print_exc()
        _log_error_to_supabase(doc_id, "enqueue_error", error_msg)
        return False
    
    # Success summary
    print(f" TASK COMPLETED SUCCESSFULLY")
    print(f" Document ID: {doc_id}")
    print(f" Company: {normalized_company}")
    print(f" Year: {normalized_year}")
    print(f" Claims: {len(result.get('claims', []))}")
    print(f" Output: {output_path}")
    
    return True


def _log_error_to_supabase(doc_id: str, error_type: str, message: str):
    """Log processing errors to Supabase for monitoring."""
    try:
        supabase = get_supabase_client()
        supabase.table('processing_errors').insert({
            'document_id': doc_id,
            'error_type': error_type,
            'message': message,
            'worker': 'pdf_processor',
            'timestamp': datetime.utcnow().isoformat()
        }).execute()
    except Exception as e:
        print(f"  Failed to log error to Supabase: {e}")


def main():
    """Worker main loop with health checks."""
    print(" PDF PROCESSOR WORKER")
    print(f"Working directory: {os.getcwd()}")
    
    # Create required directories
    os.makedirs("/data/raw_pdfs", exist_ok=True)
    os.makedirs("/data/intermediate_json", exist_ok=True)
    
    print("\n Waiting for tasks on 'pdf_processing' queue...\n")
    
    while True:
        try:
            # Block until task available (5 second timeout for graceful shutdown)
            task = dequeue_task("pdf_processing", timeout=5)
            
            if task:
                print(f"\n New task received: {task.get('id', 'unknown')}")
                success = process_task(task)
                
                if not success:
                    print(f" TASK FAILED - See logs above for details")
                
        except KeyboardInterrupt:
            print("\n\n Shutting down worker gracefully...")
            break
        except Exception as e:
            print(f"\n  UNEXPECTED WORKER ERROR: {e}")
            traceback.print_exc()
            time.sleep(5)  # Prevent tight error loops


if __name__ == "__main__":
    main()