import sys
import os
import json
import time

sys.path.append('/app')

from shared.tasks import dequeue_task, enqueue_task
from shared.database import get_supabase_client

from auditor import (
    call_gemini_ai, 
    deduplicate_metrics, 
    safe_filename,
    sample_generic_metrics
)

# Import priority keywords 
try:
    from claim_priorities import (
        HIGH_PRIORITY_CLAIMS,
        MEDIUM_PRIORITY_CLAIMS,
        LOW_PRIORITY_CLAIMS
    )
except ImportError:
    # Fallback: define inline if file doesn't exist
    HIGH_PRIORITY_CLAIMS = {
        "scope 1", "scope 1 emissions", "scope 2", "scope 2 emissions",
        "scope 3", "scope 3 emissions", "net zero", "carbon neutral",
        "GHG emissions", "greenhouse gas emissions", "renewable energy"
    }
    MEDIUM_PRIORITY_CLAIMS = {
        "emission reduction", "energy consumption", "water consumption"
    }
    LOW_PRIORITY_CLAIMS = {
        "employee safety", "diversity and inclusion", "GRI", "TCFD"
    }

# Remove duplicate claims from the same page.
def deduplicate_similar_claims(claims):
    seen = set()
    unique_claims = []
    
    for claim in claims:
        page = claim.get("page")
        keyword = claim.get("claim", "").lower()
        
        # Normalize keyword (remove common suffixes)
        base_keyword = keyword.replace(" emissions", "").replace(" target", "").strip()
        
        # Create unique key
        key = (page, base_keyword)
        
        if key not in seen:
            unique_claims.append(claim)
            seen.add(key)
    
    return unique_claims

# Scoring function to prioritize claims based on keyword and evidence quality
def score_claim(claim):
    score = 0
    
    keyword = claim.get("claim", "").lower()
    evidence = claim.get("evidence", {})
    
    # Priority-based scoring (0-40 points)
    if keyword in HIGH_PRIORITY_CLAIMS:
        score += 40
    elif keyword in MEDIUM_PRIORITY_CLAIMS:
        score += 20
    elif keyword in LOW_PRIORITY_CLAIMS:
        score += 5
    else:
        score += 10  # Unknown keywords get medium priority
    
    # Evidence-based scoring (0-30 points)
    if evidence.get("has_target_year"):
        score += 15  
    
    if evidence.get("has_numeric_data"):
        score += 10  
    
    if evidence.get("has_commitment_language"):
        score += 5 
    
    # Context quality scoring (0-20 points)
    context_length = len(claim.get("context", ""))
    if context_length > 200:
        score += 20  
    elif context_length > 100:
        score += 10  
    elif context_length > 50:
        score += 5   
    
    # Metrics availability scoring (0-10 points)
    metrics = claim.get("metrics", {})
    if metrics.get("scope1_emissions_tco2e") or metrics.get("scope2_emissions_tco2e"):
        score += 10  
    elif metrics.get("generic_metrics"):
        score += 5   
    
    return score

# Filter claims to send to AI based on priority and evidence
def filter_claims_for_ai(all_claims, max_claims=30):
    if not all_claims:
        return []
    
    # Step 1: Deduplicate similar claims
    deduplicated = deduplicate_similar_claims(all_claims)
    
    print(f"  Claim deduplication: {len(all_claims)} → {len(deduplicated)}", flush=True)
    
    # Step 2: Score each claim
    scored_claims = []
    for claim in deduplicated:
        score = score_claim(claim)
        scored_claims.append((score, claim))
    
    # Step 3: Sort by score (highest first)
    scored_claims.sort(reverse=True, key=lambda x: x[0])
    
    # Step 4: Take top N claims
    filtered = [claim for score, claim in scored_claims[:max_claims]]
    
    # Log filtering statistics
    if len(all_claims) > 0:
        print(f"  Claim filtering: {len(all_claims)} total → {len(filtered)} sent to AI", flush=True)
        
        # Count by priority
        high_count = sum(1 for c in filtered if c.get("claim", "").lower() in HIGH_PRIORITY_CLAIMS)
        medium_count = sum(1 for c in filtered if c.get("claim", "").lower() in MEDIUM_PRIORITY_CLAIMS)
        low_count = len(filtered) - high_count - medium_count
        
        print(f"    High priority: {high_count}", flush=True)
        print(f"    Medium priority: {medium_count}", flush=True)
        print(f"    Low/Other priority: {low_count}", flush=True)
        
        # Show top 5 claims by score for debugging
        print(f"  Top claims selected:", flush=True)
        for score, claim in scored_claims[:5]:
            print(f"    [{score:3d}] {claim.get('claim')} (page {claim.get('page')})", flush=True)
    
    return filtered


def process_task(task):
    doc_id = task['document_id']
    intermediate_path = task['intermediate_path']
    company = task['company']
    year = task['year']
    
    print(f"\n{'='*60}")
    print(f"AI AUDITING: {company} ({year})")
    print(f"{'='*60}")
    
    try:
        # Load intermediate JSON
        with open(intermediate_path, 'r') as f:
            data = json.load(f)
        
        print(f"\n Loaded intermediate data:")
        print(f"   Pages processed: {len(data.get('page_metrics', []))}")
        print(f"   Total claims extracted: {len(data.get('claims', []))}")
        
        # Combine page-level metrics
        combined_metrics = {
            "scope1_emissions_tco2e": [],
            "scope2_emissions_tco2e": [],
            "scope3_emissions_tco2e": [],  
            "generic_metrics": []
        }
        
        for page in data.get("page_metrics", []):
            combined_metrics["scope1_emissions_tco2e"].extend(
                page.get("scope1_emissions_tco2e", [])
            )
            combined_metrics["scope2_emissions_tco2e"].extend(
                page.get("scope2_emissions_tco2e", [])
            )
            combined_metrics["scope3_emissions_tco2e"].extend(
                page.get("scope3_emissions_tco2e", [])
            )
            combined_metrics["generic_metrics"].extend(
                page.get("generic_metrics", [])
            )
        
        # Deduplicate metrics
        combined_metrics = deduplicate_metrics(combined_metrics)
        
        # Log metrics found
        print(f"\n Metrics extracted:")
        print(f"   Scope 1: {len(combined_metrics.get('scope1_emissions_tco2e', []))} values")
        print(f"   Scope 2: {len(combined_metrics.get('scope2_emissions_tco2e', []))} values")
        print(f"   Scope 3: {len(combined_metrics.get('scope3_emissions_tco2e', []))} values")
        print(f"   Generic: {len(combined_metrics.get('generic_metrics', []))} values")
        
        # Sample generic metrics if too many 
        if len(combined_metrics.get('generic_metrics', [])) > 50:
            print(f"   Sampling generic metrics: {len(combined_metrics['generic_metrics'])} → 50")
            combined_metrics['generic_metrics'] = sample_generic_metrics(
                combined_metrics['generic_metrics'], max_samples=50
            )
        
        # Get all claims
        all_claims = data.get('claims', [])
        
        # INTELLIGENT CLAIM FILTERING
        print(f"\n Filtering claims for AI analysis...")
        filtered_claims = filter_claims_for_ai(all_claims, max_claims=20)
        
        # Call Gemini AI with filtered claims
        if filtered_claims:
            print(f"\n Calling Gemini AI...")
            print(f"   Sending {len(filtered_claims)} prioritized claims")
            
            ai_summary = call_gemini_ai(combined_metrics, filtered_claims, company, year)
            
            if ai_summary.get("overall_score"):
                print(f"\n AI Audit completed successfully!")
                print(f"   Leaf Rating: {ai_summary.get('overall_score')}/5 score")
                summary_preview = ai_summary.get('overall_summary', 'N/A')
                if len(summary_preview) > 100:
                    summary_preview = summary_preview[:100] + "..."
                print(f"   Summary: {summary_preview}")
            else:
                print(f" AI audit returned no score (check logs)")
        else:
            print(f"\n No claims found after filtering, skipping AI audit")
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
        
        scope3_total = sum(
            m.get('value', 0)
            for m in combined_metrics.get('scope3_emissions_tco2e', [])
        )
        
        print(f"\n Emission totals:")
        print(f"   Scope 1: {scope1_total:,.2f} tCO2e")
        print(f"   Scope 2: {scope2_total:,.2f} tCO2e")
        print(f"   Scope 3: {scope3_total:,.2f} tCO2e")
        
        # Prepare final output (save ALL claims, not just filtered)
        output = {
            "company": company,
            "year": year,
            "document_id": doc_id,
            "source": data.get("source", "Sustainability Report"),
            "schema_version": data.get("schema_version"),
            "processed_at": data.get("processed_at"),
            "claims": filtered_claims,
            "claims_analyzed_by_ai": len(filtered_claims),  # Track how many AI analyzed
            "ai_summary": ai_summary,
            "metrics_summary": {
                "scope1_total": scope1_total,
                "scope2_total": scope2_total,
                "scope3_total": scope3_total,
                "scope1_count": len(combined_metrics.get('scope1_emissions_tco2e', [])),
                "scope2_count": len(combined_metrics.get('scope2_emissions_tco2e', [])),
                "scope3_count": len(combined_metrics.get('scope3_emissions_tco2e', []))
            }
        }
        
        # Save processed JSON
        output_dir = "/data/processed_json"
        os.makedirs(output_dir, exist_ok=True)
        
        output_filename = safe_filename(company, year)
        output_path = os.path.join(output_dir, output_filename)
        
        with open(output_path, 'w') as f:
            json.dump(output, f, indent=2)
        
        print(f"\n Saved to: {output_path}")
        
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
                "claims": filtered_claims,
                "scope1_total": scope1_total,
                "scope2_total": scope2_total,
                "scope3_total": scope3_total,  
                "processed_at": output.get("processed_at"),
                "claims_analyzed_count": len(filtered_claims)  # Track AI analysis
            }
            
            result = supabase.table('company_reports').upsert(supabase_data).execute()
            
            print(f"  Stored in Supabase (company_reports table)")
        
        except Exception as e:
            print(f"  Failed to store in Supabase: {e}")
            import traceback
            traceback.print_exc()
        
        # Enqueue for embeddings
        embeddings_task = {
            **task,
            "audit_path": output_path,
            "audited_at": time.time(),
            "claims_count": len(filtered_claims) 
        }
        
        print(f"\n Enqueuing for embeddings generation...")
        print(f"   {len(filtered_claims)} claims will be embedded")
        enqueue_task("embeddings", embeddings_task)
        
        print(f" AUDIT COMPLETED: {company} ({year})")
        
        return True
    
    except Exception as e:
        print(f" ERROR AUDITING: {company} ({year})")
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    print("AI AUDITOR WORKER ")
    print(f"\nMax claims sent to AI: 30 (prioritized)")
    
    os.makedirs("/data/processed_json", exist_ok=True)
    
    print("Waiting for tasks on 'ai_audit' queue...\n")
    
    while True:
        try:
            task = dequeue_task("ai_audit", timeout=5)
            
            if task:
                success = process_task(task)
                if not success:
                    print(f"\n Audit failed - check logs above\n")
                
        except KeyboardInterrupt:
            print("Shutting down AI Auditor Worker...")
            break
        except Exception as e:
            print(f"\nWorker error: {e}")
            import traceback
            traceback.print_exc()
            time.sleep(5)


if __name__ == "__main__":
    main()