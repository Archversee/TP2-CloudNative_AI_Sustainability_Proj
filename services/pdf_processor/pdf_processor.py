import pdfplumber
import os
import json
import re
from datetime import datetime

INPUT_DIR = "/data/raw_pdfs"
OUTPUT_DIR = "/data/intermediate_json"
SCHEMA_VERSION = "0.4"

CLAIM_KEYWORDS = [
    # Focus on core climate claims only
    "net zero",
    "carbon neutral",
    "zero emissions",
    "renewable energy"
]

# Claims that relate to carbon emissions
EMISSIONS_CLAIMS = {"net zero", "carbon neutral", "zero emissions"}

# Map claims to expected units for numeric evidence
CLAIM_UNITS = {
    "net zero": ["tCO2e"],
    "carbon neutral": ["tCO2e"],
    "zero emissions": ["tCO2e"],
    "renewable energy": ["MWh", "kWh", "%"]
}

# Generic numeric regex with optional unit
NUMERIC_PATTERN = r"([\d,.]+)\s*(tCO2e|t|kg|tonnes|%|MWh|kWh|L|liters|m3)?"

def safe_filename(company, year):
    return f"{company.replace(' ', '_')}_{year}.json"

def parse_number(val):
    if not val:
        return None
    try:
        return float(val.replace(",", "").rstrip("."))
    except ValueError:
        return None

def extract_target_year(text):
    match = re.search(r"\bby\s+(20\d{2})\b", text.lower())
    return int(match.group(1)) if match else None

def extract_scope_from_text(text, page_num):
    """Extract Scope 1 and 2 emissions."""
    clean = text.replace("\n", " ")
    s1 = [{"value": parse_number(v), "page": page_num, "unit": "tCO2e"} 
          for v in re.findall(r"Scope\s*1[^\d]*([\d,]+(?:\.\d+)?)", clean, re.I) if parse_number(v) is not None]
    s2 = [{"value": parse_number(v), "page": page_num, "unit": "tCO2e"} 
          for v in re.findall(r"Scope\s*2[^\d]*([\d,]+(?:\.\d+)?)", clean, re.I) if parse_number(v) is not None]
    return s1, s2

def extract_scope_from_tables(page, page_num):
    """Extract Scope 1 and 2 emissions from tables."""
    scope1, scope2 = [], []
    try:
        tables = page.extract_tables()
        if not tables:
            return scope1, scope2
            
        for table in tables:
            if not table:
                continue
            for row in table:
                if not row:
                    continue
                row_text = " ".join(cell or "" for cell in row).lower()
                if "scope 1" in row_text:
                    for cell in row[1:]:
                        val = parse_number(cell or "")
                        if val is not None:
                            scope1.append({"value": val, "page": page_num, "unit": "tCO2e"})
                if "scope 2" in row_text:
                    for cell in row[1:]:
                        val = parse_number(cell or "")
                        if val is not None:
                            scope2.append({"value": val, "page": page_num, "unit": "tCO2e"})
    except Exception as e:
        # If table extraction fails, return empty lists
        pass
    return scope1, scope2

def extract_generic_metrics(text, page_num):
    """Extract all numeric patterns with units."""
    matches = re.findall(NUMERIC_PATTERN, text)
    metrics = []
    for val, unit in matches:
        num = parse_number(val)
        if num is not None:
            metrics.append({"value": num, "unit": unit, "page": page_num})
    return metrics

def filter_metrics_by_claim(metrics, claim):
    """Filter extracted metrics based on claim-specific allowed units."""
    allowed_units = CLAIM_UNITS.get(claim, [])
    filtered = [m for m in metrics if not m.get("unit") or m.get("unit") in allowed_units]
    return filtered

def process_pdf(file_path):
    page_metrics = []
    claims = []
    pdf_filename = os.path.basename(file_path)

    try:
        with pdfplumber.open(file_path) as pdf:
            for i, page in enumerate(pdf.pages):
                page_num = i + 1
                
                # Try to extract text with error handling
                try:
                    text = page.extract_text() or ""
                except Exception as e:
                    print(f"Warning: Failed to extract text from page {page_num} in {pdf_filename}: {type(e).__name__}", flush=True)
                    text = ""

                # Extract emissions metrics from text
                s1_text, s2_text = extract_scope_from_text(text, page_num)
                
                # Try to extract from tables with error handling
                try:
                    s1_table, s2_table = extract_scope_from_tables(page, page_num)
                except Exception as e:
                    print(f"Warning: Failed to extract tables from page {page_num} in {pdf_filename}: {type(e).__name__}", flush=True)
                    s1_table, s2_table = [], []
                
                scope1 = s1_text + s1_table
                scope2 = s2_text + s2_table

                # Extract all numeric metrics
                generic_metrics = extract_generic_metrics(text, page_num)

                page_metrics.append({
                    "page": page_num,
                    "scope1_emissions_tco2e": scope1,
                    "scope2_emissions_tco2e": scope2,
                    "generic_metrics": generic_metrics
                })

                # Detect claims on this page
                for kw in CLAIM_KEYWORDS:
                    if kw.lower() in text.lower():
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
                            "target_year": extract_target_year(text),
                            "metrics": claim_metrics
                        })

    except Exception as e:
        print(f"Error: Failed to open or process PDF {pdf_filename}: {type(e).__name__}: {e}", flush=True)
        # Return minimal valid structure even on complete failure
        return {
            "schema_version": SCHEMA_VERSION,
            "processed_at": datetime.utcnow().isoformat(),
            "page_metrics": [],
            "claims": [],
            "processing_error": str(e)
        }

    return {
        "schema_version": SCHEMA_VERSION,
        "processed_at": datetime.utcnow().isoformat(),
        "page_metrics": page_metrics,
        "claims": claims
    }

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    successful = 0
    failed = 0
    
    for pdf_file in os.listdir(INPUT_DIR):
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

            output_path = os.path.join(OUTPUT_DIR, safe_filename(name, year))
            with open(output_path, "w") as f:
                json.dump(output, f, indent=2)

            print(f"✓ Processed {pdf_file} → {output_path}", flush=True)
            successful += 1
            
        except Exception as e:
            print(f"✗ Failed to process {pdf_file}: {type(e).__name__}: {e}", flush=True)
            failed += 1
    
    print(f"\n=== Processing Complete ===", flush=True)
    print(f"Successful: {successful}", flush=True)
    print(f"Failed: {failed}", flush=True)

if __name__ == "__main__":
    main()