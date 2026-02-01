"""
PDF Processor Worker with Proper Naming and Supabase Integration
"""
import sys
import os
import json
import time
import re

sys.path.append('/app')

from shared.tasks import dequeue_task, enqueue_task
from shared.database import get_supabase_client

from processor import process_pdf

def extract_company_year_from_filename(filename: str):
    """
    Extract company name and year from filename.
    Expected format: Company_Name_2024.pdf
    """
    # Remove .pdf extension
    name_without_ext = filename.replace('.pdf', '').replace('.PDF', '')
    
    # Try to split by last underscore to get year
    parts = name_without_ext.rsplit('_', 1)
    
    if len(parts) == 2 and parts[1].isdigit() and len(parts[1]) == 4:
        company = parts[0].replace('_', ' ')
        year = int(parts[1])
        return company, year
    else:
        # If no year found, try to extract from content later
        company = name_without_ext.replace('_', ' ')
        return company, None

def safe_filename(company, year):
    """Generate safe filename for JSON output."""
    return f"{company.replace(' ', '_')}_{year}.json"

def process_task(task):
    """Process a PDF task and save to Supabase."""
    doc_id = task['id']
    file_path = task['path']
    original_filename = task.get('filename', f'{doc_id}.pdf')
    
    print(f"\n{'='*60}")
    print(f"📄 Processing PDF: {doc_id}")
    print(f"   Original filename: {original_filename}")
    print(f"   File path: {file_path}")
    print(f"{'='*60}\n")
    
    # Verify file exists
    if not os.path.exists(file_path):
        print(f"✗ File not found: {file_path}")
        return False
    
    file_size = os.path.getsize(file_path)
    print(f"✓ File exists, size: {file_size:,} bytes")
    
    try:
        # Extract company and year from original filename
        company_from_filename, year_from_filename = extract_company_year_from_filename(original_filename)
        
        print(f"📋 Extracted from filename:")
        print(f"   Company: {company_from_filename}")
        print(f"   Year: {year_from_filename}")
        
        # Run your existing PDF processor
        print(f"\n🔄 Running PDF processor...")
        result = process_pdf(file_path)
        
        # Use filename info if processor didn't find it
        company = result.get('company') or company_from_filename or 'Unknown'
        year = result.get('year') or year_from_filename or 2024
        
        # Override with filename info (more reliable)
        if company_from_filename:
            company = company_from_filename
        if year_from_filename:
            year = year_from_filename
        
        # Update result with correct naming
        result['company'] = company
        result['year'] = year
        result['document_id'] = doc_id
        result['original_filename'] = original_filename
        
        # Save intermediate JSON with proper naming
        output_dir = "/data/intermediate_json"
        os.makedirs(output_dir, exist_ok=True)
        
        output_filename = safe_filename(company, year)
        output_path = os.path.join(output_dir, output_filename)
        
        with open(output_path, 'w') as f:
            json.dump(result, f, indent=2)
        
        print(f"\n✓ PDF processed successfully!")
        print(f"  Company: {company}")
        print(f"  Year: {year}")
        print(f"  Saved to: {output_path}")
        print(f"  Claims found: {len(result.get('claims', []))}")
        
        # Enqueue for AI audit
        audit_task = {
            **task,
            "intermediate_path": output_path,
            "company": company,
            "year": year,
            "document_id": doc_id,
            "processed_at": time.time()
        }
        
        print(f"\n📤 Enqueuing for AI audit...")
        enqueue_task("ai_audit", audit_task)
        print(f"✓ Enqueued to ai_audit queue")
        
        return True
    
    except Exception as e:
        print(f"\n✗ Error processing {doc_id}: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Worker main loop."""
    print("\n" + "="*60)
    print("PDF PROCESSOR WORKER")
    print("="*60)
    print(f"Working directory: {os.getcwd()}")
    print(f"Data directory: {'/data' if os.path.exists('/data') else 'NOT FOUND'}")
    print(f"raw_pdfs: {'/data/raw_pdfs' if os.path.exists('/data/raw_pdfs') else 'NOT FOUND'}")
    print("="*60)
    
    # Create directories if they don't exist
    os.makedirs("/data/raw_pdfs", exist_ok=True)
    os.makedirs("/data/intermediate_json", exist_ok=True)
    
    print("\n⏳ Waiting for tasks on 'pdf_processing' queue...\n")
    
    while True:
        try:
            # Block until task available (5 second timeout)
            task = dequeue_task("pdf_processing", timeout=5)
            
            if task:
                success = process_task(task)
                if success:
                    print(f"\n{'='*60}")
                    print(f"✅ Task completed successfully")
                    print(f"{'='*60}\n")
                else:
                    print(f"\n{'='*60}")
                    print(f"❌ Task failed")
                    print(f"{'='*60}\n")
                
        except KeyboardInterrupt:
            print("\n\n👋 Shutting down worker...")
            break
        except Exception as e:
            print(f"\n⚠️  Worker error: {e}")
            import traceback
            traceback.print_exc()
            time.sleep(5)

if __name__ == "__main__":
    main()