import pdfplumber
import os
import json
import re
from datetime import datetime
from collections import defaultdict

INPUT_DIR = "/data/raw_pdfs"
OUTPUT_DIR = "/data/intermediate_json"
SCHEMA_VERSION = "0.5"

# Focus on core climate claims
CLAIM_KEYWORDS = [
    "net zero",
    "carbon neutral",
    "zero emissions",
    "renewable energy"
]

# Claims that relate to carbon emissions
EMISSIONS_CLAIMS = {"net zero", "carbon neutral", "zero emissions"}

# Map claims to expected units for numeric evidence
CLAIM_UNITS = {
    "net zero": ["tCO2e", "tCO2", "tonnes CO2e"],
    "carbon neutral": ["tCO2e", "tCO2", "tonnes CO2e"],
    "zero emissions": ["tCO2e", "tCO2", "tonnes CO2e"],
    "renewable energy": ["MWh", "kWh", "GWh", "%", "percent"]
}

# Improved numeric regex patterns
# Matches numbers with commas, decimals, and various separators
NUMERIC_PATTERN = r"([\d]{1,3}(?:[,\s]?\d{3})*(?:\.\d+)?)\s*(tCO2e|tCO2|tonnes\s+CO2e?|t\s+CO2e?|kg|tonnes?|%|percent|MWh|kWh|GWh|L|liters?|m3|m³)?"

# Enhanced Scope extraction patterns
SCOPE_PATTERNS = {
    "scope1": [
        r"Scope\s*1[:\s]+([\d,]+(?:\.\d+)?)\s*(tCO2e|tCO2)?",
        r"Scope\s*1\s+emissions?[:\s]+([\d,]+(?:\.\d+)?)",
        r"Direct\s+emissions[:\s]+([\d,]+(?:\.\d+)?)",
    ],
    "scope2": [
        r"Scope\s*2[:\s]+([\d,]+(?:\.\d+)?)\s*(tCO2e|tCO2)?",
        r"Scope\s*2\s+emissions?[:\s]+([\d,]+(?:\.\d+)?)",
        r"Indirect\s+emissions[:\s]+([\d,]+(?:\.\d+)?)",
        r"Energy\s+indirect[:\s]+([\d,]+(?:\.\d+)?)",
    ]
}

def safe_filename(company, year):
    return f"{company.replace(' ', '_')}_{year}.json"

def parse_number(val):
    """Parse number, handling commas and various formats."""
    if not val:
        return None
    try:
        # Remove commas and spaces used as thousand separators
        cleaned = val.replace(",", "").replace(" ", "").rstrip(".")
        return float(cleaned)
    except (ValueError, AttributeError):
        return None

def normalize_unit(unit):
    """Normalize unit strings to standard format."""
    if not unit:
        return ""
    
    unit = unit.lower().strip()
    
    # Normalize CO2 units
    if any(x in unit for x in ["tco2e", "tonnes co2e", "t co2e"]):
        return "tCO2e"
    if "tco2" in unit or "t co2" in unit:
        return "tCO2e"
    
    # Normalize energy units
    if "gwh" in unit:
        return "GWh"
    if "mwh" in unit:
        return "MWh"
    if "kwh" in unit:
        return "kWh"
    
    # Normalize percentage
    if "percent" in unit or unit == "%":
        return "%"
    
    # Normalize weight
    if "tonne" in unit or unit == "t":
        return "tonnes"
    if unit == "kg":
        return "kg"
    
    return unit

def extract_target_year(text):
    """Extract target year from text with improved patterns."""
    patterns = [
        r"by\s+(20\d{2})",
        r"target\s+year[:\s]+(20\d{2})",
        r"achieve.*?(20\d{2})",
        r"reach.*?(20\d{2})",
        r"goal.*?(20\d{2})",
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text.lower())
        if match:
            year = int(match.group(1))
            # Sanity check: year should be between 2020 and 2100
            if 2020 <= year <= 2100:
                return year
    return None

def extract_scope_from_text(text, page_num):
    """Extract Scope 1 and 2 emissions with improved patterns."""
    clean = text.replace("\n", " ")
    scope1, scope2 = [], []
    
    # Try multiple patterns for Scope 1
    for pattern in SCOPE_PATTERNS["scope1"]:
        matches = re.findall(pattern, clean, re.I)
        for match in matches:
            # Handle tuple results from regex groups
            value_str = match[0] if isinstance(match, tuple) else match
            val = parse_number(value_str)
            if val is not None and val > 0:  # Filter out zeros
                scope1.append({
                    "value": val,
                    "page": page_num,
                    "unit": "tCO2e"
                })
    
    # Try multiple patterns for Scope 2
    for pattern in SCOPE_PATTERNS["scope2"]:
        matches = re.findall(pattern, clean, re.I)
        for match in matches:
            value_str = match[0] if isinstance(match, tuple) else match
            val = parse_number(value_str)
            if val is not None and val > 0:
                scope2.append({
                    "value": val,
                    "page": page_num,
                    "unit": "tCO2e"
                })
    
    return scope1, scope2

def extract_scope_from_tables(page, page_num):
    """Extract Scope 1 and 2 emissions from tables with better error handling."""
    scope1, scope2 = [], []
    
    try:
        tables = page.extract_tables()
        if not tables:
            return scope1, scope2
        
        for table in tables:
            if not table or len(table) < 2:  # Need at least header + 1 row
                continue
            
            for row_idx, row in enumerate(table):
                if not row:
                    continue
                
                # Join cells to check for scope keywords
                row_text = " ".join(str(cell or "") for cell in row).lower()
                
                # Look for Scope 1
                if any(keyword in row_text for keyword in ["scope 1", "scope1", "direct emission"]):
                    # Extract numbers from this row
                    for cell in row[1:]:  # Skip first cell (label)
                        if cell:
                            val = parse_number(str(cell))
                            if val is not None and val > 0:
                                scope1.append({
                                    "value": val,
                                    "page": page_num,
                                    "unit": "tCO2e"
                                })
                
                # Look for Scope 2
                if any(keyword in row_text for keyword in ["scope 2", "scope2", "indirect emission", "energy indirect"]):
                    for cell in row[1:]:
                        if cell:
                            val = parse_number(str(cell))
                            if val is not None and val > 0:
                                scope2.append({
                                    "value": val,
                                    "page": page_num,
                                    "unit": "tCO2e"
                                })
    
    except Exception as e:
        # Silently continue if table extraction fails
        pass
    
    return scope1, scope2

def extract_generic_metrics(text, page_num):
    """Extract all numeric patterns with improved unit detection."""
    matches = re.findall(NUMERIC_PATTERN, text, re.I)
    metrics = []
    
    for val, unit in matches:
        num = parse_number(val)
        if num is not None and num > 0:  # Filter out zeros
            normalized_unit = normalize_unit(unit)
            metrics.append({
                "value": num,
                "unit": normalized_unit,
                "page": page_num
            })
    
    return metrics

def filter_metrics_by_claim(metrics, claim):
    """Filter extracted metrics based on claim-specific allowed units."""
    allowed_units = CLAIM_UNITS.get(claim, [])
    
    # Normalize allowed units
    allowed_units_normalized = [normalize_unit(u) for u in allowed_units]
    
    filtered = []
    for m in metrics:
        metric_unit = m.get("unit", "")
        # Include if: no unit specified, or unit matches allowed units
        if not metric_unit or metric_unit in allowed_units_normalized:
            filtered.append(m)
    
    return filtered

def deduplicate_metrics_on_page(metrics):
    """Remove duplicate metrics on the same page."""
    seen = set()
    deduped = []
    
    for m in metrics:
        key = (m.get("value"), m.get("unit"))
        if key not in seen:
            seen.add(key)
            deduped.append(m)
    
    return deduped

def extract_claim_context(text, claim_keyword, window=200):
    """Extract surrounding text context for a claim."""
    claim_pos = text.lower().find(claim_keyword.lower())
    if claim_pos == -1:
        return ""
    
    start = max(0, claim_pos - window)
    end = min(len(text), claim_pos + len(claim_keyword) + window)
    context = text[start:end].replace("\n", " ").strip()
    
    return context

def process_pdf(file_path):
    """Process PDF with improved extraction and error handling."""
    page_metrics = []
    claims = []
    pdf_filename = os.path.basename(file_path)
    
    # Track statistics for logging
    stats = {
        "total_pages": 0,
        "text_extraction_failures": 0,
        "table_extraction_failures": 0
    }

    try:
        with pdfplumber.open(file_path) as pdf:
            stats["total_pages"] = len(pdf.pages)
            
            for i, page in enumerate(pdf.pages):
                page_num = i + 1
                
                # Extract text with error handling
                text = ""
                try:
                    text = page.extract_text() or ""
                except Exception as e:
                    stats["text_extraction_failures"] += 1
                    print(f"Warning: Failed to extract text from page {page_num} in {pdf_filename}: {type(e).__name__}", flush=True)

                # Extract emissions metrics from text
                s1_text, s2_text = extract_scope_from_text(text, page_num)
                
                # Extract from tables
                s1_table, s2_table = [], []
                try:
                    s1_table, s2_table = extract_scope_from_tables(page, page_num)
                except Exception as e:
                    stats["table_extraction_failures"] += 1
                    print(f"Warning: Failed to extract tables from page {page_num} in {pdf_filename}: {type(e).__name__}", flush=True)
                
                # Combine and deduplicate scope emissions
                scope1 = deduplicate_metrics_on_page(s1_text + s1_table)
                scope2 = deduplicate_metrics_on_page(s2_text + s2_table)

                # Extract all numeric metrics
                generic_metrics = extract_generic_metrics(text, page_num)
                generic_metrics = deduplicate_metrics_on_page(generic_metrics)

                page_metrics.append({
                    "page": page_num,
                    "scope1_emissions_tco2e": scope1,
                    "scope2_emissions_tco2e": scope2,
                    "generic_metrics": generic_metrics
                })

                # Detect claims on this page
                for kw in CLAIM_KEYWORDS:
                    if kw.lower() in text.lower():
                        # Extract context around the claim
                        context = extract_claim_context(text, kw)
                        
                        if kw in EMISSIONS_CLAIMS:
                            claim_metrics = {
                                "scope1_emissions_tco2e": scope1,
                                "scope2_emissions_tco2e": scope2,
                                "generic_metrics": []
                            }
                        else:
                            claim_metrics = {
                                "scope1_emissions_tco2e": [],
                                "scope2_emissions_tco2e": [],
                                "generic_metrics": filter_metrics_by_claim(generic_metrics, kw)
                            }

                        claims.append({
                            "claim": kw,
                            "page": page_num,
                            "target_year": extract_target_year(context),
                            "context": context[:100] if context else "",  # First 100 chars
                            "metrics": claim_metrics
                        })
            
            # Log extraction statistics
            if stats["text_extraction_failures"] > 0 or stats["table_extraction_failures"] > 0:
                print(f"  Stats for {pdf_filename}:", flush=True)
                print(f"    Pages processed: {stats['total_pages']}", flush=True)
                print(f"    Text failures: {stats['text_extraction_failures']}", flush=True)
                print(f"    Table failures: {stats['table_extraction_failures']}", flush=True)

    except Exception as e:
        print(f"Error: Failed to open or process PDF {pdf_filename}: {type(e).__name__}: {e}", flush=True)
        # Return minimal valid structure even on complete failure
        return {
            "schema_version": SCHEMA_VERSION,
            "processed_at": datetime.utcnow().isoformat(),
            "page_metrics": [],
            "claims": [],
            "processing_error": str(e),
            "stats": stats
        }

    return {
        "schema_version": SCHEMA_VERSION,
        "processed_at": datetime.utcnow().isoformat(),
        "page_metrics": page_metrics,
        "claims": claims,
        "stats": stats
    }

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    successful = 0
    failed = 0
    
    total_claims = 0
    total_scope1 = 0
    total_scope2 = 0
    
    for pdf_file in sorted(os.listdir(INPUT_DIR)):
        if not pdf_file.lower().endswith(".pdf"):
            continue

        try:
            name, year = pdf_file.replace(".pdf", "").rsplit("_", 1)
            year = int(year)
            input_path = os.path.join(INPUT_DIR, pdf_file)
            extracted = process_pdf(input_path)

            output = {
                "company": name,
                "year": year,
                "source": "Sustainability Report",
                **extracted
            }

            # Count metrics for summary
            claims_count = len(output.get("claims", []))
            total_claims += claims_count
            
            for page in output.get("page_metrics", []):
                total_scope1 += len(page.get("scope1_emissions_tco2e", []))
                total_scope2 += len(page.get("scope2_emissions_tco2e", []))

            output_path = os.path.join(OUTPUT_DIR, safe_filename(name, year))
            with open(output_path, "w") as f:
                json.dump(output, f, indent=2)

            print(f"✓ Processed {pdf_file} → {claims_count} claims found", flush=True)
            successful += 1
            
        except Exception as e:
            print(f"✗ Failed to process {pdf_file}: {type(e).__name__}: {e}", flush=True)
            failed += 1
    
    print(f"\n=== Processing Complete ===", flush=True)
    print(f"Successful: {successful}", flush=True)
    print(f"Failed: {failed}", flush=True)
    print(f"Total claims: {total_claims}", flush=True)
    print(f"Total Scope 1 metrics: {total_scope1}", flush=True)
    print(f"Total Scope 2 metrics: {total_scope2}", flush=True)

if __name__ == "__main__":
    main()