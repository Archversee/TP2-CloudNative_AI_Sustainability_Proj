import os
import json
import re
import requests
from dotenv import load_dotenv
import time

# --- Load environment variables ---
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY not found in environment")

INPUT_DIR = "/data/intermediate_json"
OUTPUT_DIR = "/data/processed_json"

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

# --- Helpers ---
def safe_filename(company, year):
    return f"{company.replace(' ', '_')}_{year}.json"

def deduplicate_metrics(metrics):
    """Remove duplicate metric entries by value & page."""
    dedup = {}
    for key, entries in metrics.items():
        seen = set()
        clean_list = []
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            val = entry.get("value")
            page = entry.get("page")
            if val is None or page is None:
                continue
            key_tuple = (val, page)
            if key_tuple not in seen:
                seen.add(key_tuple)
                # Keep the unit if present
                clean_entry = {"value": val, "page": page}
                if "unit" in entry and entry["unit"]:
                    clean_entry["unit"] = entry["unit"]
                clean_list.append(clean_entry)
        dedup[key] = clean_list
    return dedup

def sample_generic_metrics(metrics, max_samples=50):
    """Intelligently sample generic metrics to reduce payload size."""
    if len(metrics) <= max_samples:
        return metrics
    
    # Group metrics by page for proportional sampling
    by_page = {}
    for m in metrics:
        page = m.get('page', 0)
        if page not in by_page:
            by_page[page] = []
        by_page[page].append(m)
    
    # Sample proportionally from each page
    sampled = []
    total_pages = len(by_page)
    samples_per_page = max(1, max_samples // total_pages)
    
    for page in sorted(by_page.keys()):
        page_metrics = by_page[page]
        # Take first N metrics from each page (usually most relevant)
        sampled.extend(page_metrics[:samples_per_page])
        
        if len(sampled) >= max_samples:
            break
    
    return sampled[:max_samples]

def should_reduce_claims(claims):
    """Determine if we need to reduce claims to avoid rate limiting."""
    # If more than 20 claims, we might hit rate limits
    return len(claims) > 20

def prioritize_claims(claims, max_claims=15):
    """Prioritize and limit claims to most important ones."""
    if len(claims) <= max_claims:
        return claims
    
    # Priority order: net zero > carbon neutral > zero emissions > renewable energy
    priority = {
        "net zero": 1,
        "carbon neutral": 2, 
        "zero emissions": 3,
        "renewable energy": 4
    }
    
    # Sort by priority, then by page number
    sorted_claims = sorted(
        claims,
        key=lambda c: (priority.get(c.get('claim', ''), 99), c.get('page', 999))
    )
    
    return sorted_claims[:max_claims]

def parse_ai_json(raw_text):
    """Extract JSON object from AI output, handling markdown code blocks."""
    try:
        return json.loads(raw_text)
    except json.JSONDecodeError:
        # Try to extract from markdown code block
        code_block_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', raw_text, re.DOTALL)
        if code_block_match:
            try:
                return json.loads(code_block_match.group(1))
            except json.JSONDecodeError:
                pass
        
        # Try to find any JSON object
        match = re.search(r'\{.*\}', raw_text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
    return None

def aggregate_claim_metrics(claim, page_metrics):
    """Aggregate all relevant metrics for a specific claim from page_metrics."""
    claim_page = claim.get("page")
    claim_text = claim.get("claim", "").lower()
    
    # Get metrics from the claim's page
    relevant_metrics = {
        "scope1_emissions_tco2e": [],
        "scope2_emissions_tco2e": [],
        "generic_metrics": []
    }
    
    for page in page_metrics:
        if page.get("page") == claim_page:
            relevant_metrics["scope1_emissions_tco2e"] = page.get("scope1_emissions_tco2e", [])
            relevant_metrics["scope2_emissions_tco2e"] = page.get("scope2_emissions_tco2e", [])
            relevant_metrics["generic_metrics"] = page.get("generic_metrics", [])
            break
    
    return relevant_metrics

# --- Gemini AI call ---
def call_gemini_ai(metrics, claims, company, year):
    """Call Gemini AI to audit claims against metrics."""
    url = f"https://generativelanguage.googleapis.com/v1/models/{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
    headers = {"Content-Type": "application/json"}

    # Format metrics more clearly for the AI
    metrics_summary = []
    for key, values in metrics.items():
        if values:
            metrics_summary.append(f"{key}: {len(values)} entries")
            for v in values[:5]:  # Show first 5 as examples
                metrics_summary.append(f"  - {v}")
    
    claims_summary = []
    for i, claim in enumerate(claims, 1):
        claims_summary.append(f"Claim {i}: '{claim.get('claim')}' (Page {claim.get('page')})")
        if claim.get('target_year'):
            claims_summary.append(f"  Target Year: {claim.get('target_year')}")

    prompt = (
        f"Audit sustainability claims for {company} ({year}).\n\n"
        f"METRICS:\n{json.dumps(metrics, indent=2)}\n\n"
        f"CLAIMS:\n{json.dumps(claims, indent=2)}\n\n"
        "Score each claim 1-5 based on evidence:\n"
        "5=Fully supported | 4=Well supported | 3=Partially supported | 2=Minimal evidence | 1=No evidence\n\n"
        "Return ONLY this JSON (no markdown):\n"
        "{\n"
        '  "overall_score": 1-5,\n'
        '  "overall_summary": "one sentence",\n'
        '  "claim_reviews": [{"claim": "text", "page": N, "score": 1-5, "reason": "explanation with pages", "citations": [pages]}]\n'
        "}"
    )

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "maxOutputTokens": 4000,  # Reduced for focused claims
            "temperature": 0.1,
            "topP": 0.95
        },
        "safetySettings": [
            {"category": cat, "threshold": "BLOCK_NONE"}
            for cat in [
                "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                "HARM_CATEGORY_HATE_SPEECH",
                "HARM_CATEGORY_HARASSMENT",
                "HARM_CATEGORY_DANGEROUS_CONTENT"
            ]
        ]
    }

    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            
            # Handle potential API errors
            if "error" in result:
                error_msg = result['error'].get('message', 'Unknown error')
                print(f"  API Error: {error_msg}", flush=True)
                
                # Check if it's a rate limit error
                if "quota" in error_msg.lower() or "rate" in error_msg.lower():
                    if attempt < max_retries - 1:
                        wait_time = (attempt + 1) * 10  # Progressive backoff: 10s, 20s, 30s
                        print(f"  Rate limited, waiting {wait_time}s before retry...", flush=True)
                        time.sleep(wait_time)
                        continue
                
                return create_fallback_response(claims, f"API error: {error_msg}")
            
            # Extract text from response
            if "candidates" not in result or not result["candidates"]:
                print(f"  No candidates in response", flush=True)
                return create_fallback_response(claims, "No response candidates")
            
            candidate = result["candidates"][0]
            if "content" not in candidate or "parts" not in candidate["content"]:
                print(f"  Invalid response structure", flush=True)
                return create_fallback_response(claims, "Invalid response structure")
            
            raw_text = candidate["content"]["parts"][0]["text"].strip()
            
            # Parse JSON from response
            parsed = parse_ai_json(raw_text)
            
            if parsed and "overall_score" in parsed and "claim_reviews" in parsed:
                # Validate the response structure
                if validate_ai_response(parsed, claims):
                    return parsed
                else:
                    print(f"  Response validation failed, attempt {attempt + 1}/{max_retries}", flush=True)
            else:
                print(f"  Failed to parse valid JSON, attempt {attempt + 1}/{max_retries}", flush=True)
                if attempt == max_retries - 1:
                    # On last attempt, return what we have
                    return {
                        "overall_score": None,
                        "overall_summary": "Failed to parse AI response",
                        "claim_reviews": [],
                        "raw_response": raw_text[:500]
                    }
            
            # Wait before retry
            if attempt < max_retries - 1:
                time.sleep(2)
                
        except requests.exceptions.HTTPError as e:
            # Handle rate limiting specifically
            if e.response.status_code == 429:
                if attempt < max_retries - 1:
                    # More aggressive backoff for rate limits: 15s, 30s, 45s
                    wait_time = (attempt + 1) * 15
                    print(f"  Rate limited (429), waiting {wait_time}s before retry...", flush=True)
                    time.sleep(wait_time)
                else:
                    print(f"  Rate limit persists after {max_retries} attempts", flush=True)
                    return create_fallback_response(claims, "Rate limit exceeded")
            else:
                print(f"  HTTP Error {e.response.status_code}: {e}, attempt {attempt + 1}/{max_retries}", flush=True)
                if attempt < max_retries - 1:
                    time.sleep(3)
        except requests.exceptions.Timeout:
            print(f"  Request timeout, attempt {attempt + 1}/{max_retries}", flush=True)
            if attempt < max_retries - 1:
                time.sleep(3)
        except requests.exceptions.RequestException as e:
            print(f"  Request failed: {e}, attempt {attempt + 1}/{max_retries}", flush=True)
            if attempt < max_retries - 1:
                time.sleep(3)
        except Exception as e:
            print(f"  Unexpected error: {e}", flush=True)
            return create_fallback_response(claims, f"Unexpected error: {str(e)}")
    
    return create_fallback_response(claims, "Max retries exceeded")

def validate_ai_response(response, claims):
    """Validate that AI response has correct structure and reasonable values."""
    if not isinstance(response, dict):
        return False
    
    overall_score = response.get("overall_score")
    if not isinstance(overall_score, (int, float)) or not (1 <= overall_score <= 5):
        return False
    
    claim_reviews = response.get("claim_reviews", [])
    if not isinstance(claim_reviews, list):
        return False
    
    # Check each claim review
    for review in claim_reviews:
        if not isinstance(review, dict):
            return False
        if "claim" not in review or "score" not in review:
            return False
        score = review.get("score")
        if not isinstance(score, (int, float)) or not (1 <= score <= 5):
            return False
    
    return True

def create_fallback_response(claims, error_msg):
    """Create a fallback response when AI call fails."""
    return {
        "overall_score": None,
        "overall_summary": f"Audit failed: {error_msg}",
        "claim_reviews": [
            {
                "claim": claim.get("claim", "Unknown"),
                "page": claim.get("page"),
                "score": None,
                "reason": "Could not evaluate due to processing error",
                "citations": []
            }
            for claim in claims
        ]
    }

# --- Main workflow ---
def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    print(f"Starting AI audit on {INPUT_DIR}", flush=True)
    
    successful = 0
    failed = 0

    for json_file in sorted(os.listdir(INPUT_DIR)):
        if not json_file.lower().endswith(".json"):
            continue

        input_path = os.path.join(INPUT_DIR, json_file)
        
        try:
            with open(input_path, "r") as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            print(f"✗ Failed to parse JSON {json_file}: {e}", flush=True)
            failed += 1
            continue

        company = data.get("company", "UNKNOWN")
        year = data.get("year", "UNKNOWN")
        
        print(f"\nProcessing {company} ({year})...", flush=True)

        # Skip if there was a processing error in the PDF stage
        if "processing_error" in data:
            print(f"  ⚠ Skipping - PDF processing error: {data['processing_error']}", flush=True)
            output = {**data, "ai_summary": create_fallback_response([], "PDF processing failed")}
            output.pop("page_metrics", None)
            output_path = os.path.join(OUTPUT_DIR, safe_filename(company, year))
            with open(output_path, "w") as f:
                json.dump(output, f, indent=2)
            failed += 1
            continue

        # Combine page-level metrics into a single dict for AI
        combined_metrics = {
            "scope1_emissions_tco2e": [],
            "scope2_emissions_tco2e": [],
            "generic_metrics": []
        }
        
        for page in data.get("page_metrics", []):
            page_num = page.get("page")
            
            # Metrics already have the correct structure: {"value": X, "page": Y, "unit": Z}
            # Just extend the lists directly
            combined_metrics["scope1_emissions_tco2e"].extend(
                page.get("scope1_emissions_tco2e", [])
            )
            combined_metrics["scope2_emissions_tco2e"].extend(
                page.get("scope2_emissions_tco2e", [])
            )
            combined_metrics["generic_metrics"].extend(
                page.get("generic_metrics", [])
            )

        # Deduplicate metrics
        combined_metrics = deduplicate_metrics(combined_metrics)
        
        # Sample generic metrics to reduce payload size
        original_count = len(combined_metrics.get('generic_metrics', []))
        if original_count > 50:
            combined_metrics['generic_metrics'] = sample_generic_metrics(
                combined_metrics['generic_metrics'], 
                max_samples=50
            )
            print(f"  Sampled {len(combined_metrics['generic_metrics'])} from {original_count} generic metrics", flush=True)
        
        # Get claims
        claims = data.get("claims", [])
        
        # Prioritize claims if too many (reduces payload and rate limiting)
        original_claim_count = len(claims)
        if should_reduce_claims(claims):
            claims = prioritize_claims(claims, max_claims=15)
            print(f"  ⚠ Too many claims ({original_claim_count}), prioritized to {len(claims)} most critical", flush=True)
        
        print(f"  Found {len(claims)} claims", flush=True)
        print(f"  Scope 1 metrics: {len(combined_metrics.get('scope1_emissions_tco2e', []))}", flush=True)
        print(f"  Scope 2 metrics: {len(combined_metrics.get('scope2_emissions_tco2e', []))}", flush=True)
        print(f"  Generic metrics: {len(combined_metrics.get('generic_metrics', []))}", flush=True)

        # AI call
        if claims:
            print(f"  Calling Gemini AI...", flush=True)
            ai_summary = call_gemini_ai(combined_metrics, claims, company, year)
            
            if ai_summary.get("overall_score") is not None:
                print(f"  ✓ AI Score: {ai_summary.get('overall_score')}/5", flush=True)
                successful += 1
            else:
                print(f"  ⚠ AI call succeeded but no valid score", flush=True)
                failed += 1
        else:
            print(f"  ℹ No claims found, skipping AI audit", flush=True)
            ai_summary = {
                "overall_score": None,
                "overall_summary": "No sustainability claims found in document",
                "claim_reviews": []
            }

        # Final output: keep claims, remove page_metrics to reduce size
        output = {
            "company": company,
            "year": year,
            "source": data.get("source", "Sustainability Report"),
            "schema_version": data.get("schema_version"),
            "processed_at": data.get("processed_at"),
            "claims": claims,
            "ai_summary": ai_summary
        }

        output_path = os.path.join(OUTPUT_DIR, safe_filename(company, year))
        with open(output_path, "w") as f:
            json.dump(output, f, indent=2)

        print(f"  ✓ Saved to {output_path}", flush=True)
        
        # Add delay between documents to avoid rate limiting
        # Longer delay for documents with many claims
        if len(claims) > 20:
            delay = 10
            print(f"  ⏸ Large document ({len(claims)} claims), waiting {delay}s before next...", flush=True)
        elif len(claims) > 10:
            delay = 5
        else:
            delay = 3
        time.sleep(delay)

    print(f"\n=== Audit Complete ===", flush=True)
    print(f"Successful: {successful}", flush=True)
    print(f"Failed/Skipped: {failed}", flush=True)

if __name__ == "__main__":
    main()