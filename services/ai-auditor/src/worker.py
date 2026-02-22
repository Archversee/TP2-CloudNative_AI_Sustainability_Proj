"""
AI Auditor Worker with Supabase Integration
Processes PDFs and stores results in Supabase
"""
import sys
import os
import json
import time

sys.path.append('/app')

from shared.tasks import dequeue_task, enqueue_task
from shared.database import get_supabase_client

from auditor import call_gemini_ai, deduplicate_metrics, safe_filename

def process_task(task):
    """Process an AI audit task and save to Supabase."""
    doc_id = task['document_id']
    intermediate_path = task['intermediate_path']
    company = task['company']
    year = task['year']
    
    print(f"AI Auditing: {company} ({year})")
    
    try:
        # Load intermediate JSON
        with open(intermediate_path, 'r') as f:
            data = json.load(f)
        
        print(f" Loaded data:")
        print(f"   Pages: {len(data.get('page_metrics', []))}")
        print(f"   Claims: {len(data.get('claims', []))}")
        
        # Combine page-level metrics
        combined_metrics = {
            "scope1_emissions_tco2e": [],
            "scope2_emissions_tco2e": [],
            "generic_metrics": []
        }
        
        for page in data.get("page_metrics", []):
            combined_metrics["scope1_emissions_tco2e"].extend(
                page.get("scope1_emissions_tco2e", [])
            )
            combined_metrics["scope2_emissions_tco2e"].extend(
                page.get("scope2_emissions_tco2e", [])
            )
            combined_metrics["generic_metrics"].extend(
                page.get("generic_metrics", [])
            )
        
        # Deduplicate and sample if needed
        combined_metrics = deduplicate_metrics(combined_metrics)
        
        # Sample generic metrics if too many
        if len(combined_metrics.get('generic_metrics', [])) > 50:
            combined_metrics['generic_metrics'] = combined_metrics['generic_metrics'][:50]
        
        claims = data.get('claims', [])
        
        # Prioritize claims if too many
        if len(claims) > 15:
            print(f"Too many claims ({len(claims)}), prioritizing to 15...")
            claims = claims[:15]
        
        # Call Gemini AI
        if claims:
            print(f"\nCalling Gemini AI for audit...")
            ai_summary = call_gemini_ai(combined_metrics, claims, company, year)
            
            if ai_summary.get("overall_score"):
                print(f" AI Audit completed")
                print(f"  Overall Score: {ai_summary.get('overall_score')}/5")
                print(f"  Summary: {ai_summary.get('overall_summary', 'N/A')[:100]}...")
            else:
                print(f"AI audit returned no score")
        else:
            print(f"No claims found, skipping AI audit")
            ai_summary = {
                "overall_score": None,
                "overall_summary": "No sustainability claims found in document",
                "claim_reviews": []
            }
        
        # Calculate total emissions
        scope1_total = sum(
            m.get('value', 0) 
            for m in combined_metrics.get('scope1_emissions_tco2e', [])
        )
        
        scope2_total = sum(
            m.get('value', 0)
            for m in combined_metrics.get('scope2_emissions_tco2e', [])
        )
        
        # Prepare final output
        output = {
            "company": company,
            "year": year,
            "document_id": doc_id,
            "source": data.get("source", "Sustainability Report"),
            "schema_version": data.get("schema_version"),
            "processed_at": data.get("processed_at"),
            "claims": claims,
            "ai_summary": ai_summary
        }
        
        # Save processed JSON
        output_dir = "/data/processed_json"
        os.makedirs(output_dir, exist_ok=True)
        
        output_filename = safe_filename(company, year)
        output_path = os.path.join(output_dir, output_filename)
        
        with open(output_path, 'w') as f:
            json.dump(output, f, indent=2)
        
        # Store in Supabase
        print(f"\n Storing in Supabase...")
        try:
            supabase = get_supabase_client()
            
            supabase_data = {
                "document_id": doc_id,
                "company": company,
                "year": year,
                "source": output.get("source"),
                "leaf_rating": ai_summary.get("overall_score"),
                "truth_score": ai_summary.get("overall_score"),
                "ai_summary": ai_summary.get("overall_summary", ""),
                "claims": claims,
                "scope1_total": scope1_total,
                "scope2_total": scope2_total,
                "processed_at": output.get("processed_at")
            }
            
            result = supabase.table('company_reports').upsert(supabase_data).execute()
            
            print(f" Stored in Supabase")
        
        except Exception as e:
            print(f"Failed to store in Supabase: {e}")
            # Continue anyway - we have the JSON file
        
        # Enqueue for embeddings
        embeddings_task = {
            **task,
            "audit_path": output_path,
            "audited_at": time.time()
        }
        
        print(f"\n Enqueuing for embeddings generation...")
        enqueue_task("embeddings", embeddings_task)
        
        return True
    
    except Exception as e:
        print(f"\nError auditing {doc_id}: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Worker main loop."""
    print("AI AUDITOR WORKER")
    
    os.makedirs("/data/processed_json", exist_ok=True)
    
    print("\n Waiting for tasks on 'ai_audit' queue...\n")
    
    while True:
        try:
            task = dequeue_task("ai_audit", timeout=5)
            
            if task:
                success = process_task(task)
                if success:
                    print(f"Audit completed successfully")
                else:
                    print(f"Audit failed")
                
        except KeyboardInterrupt:
            print("\n\nShutting down worker...")
            break
        except Exception as e:
            print(f"\nWorker error: {e}")
            import traceback
            traceback.print_exc()
            time.sleep(5)

if __name__ == "__main__":
    main()