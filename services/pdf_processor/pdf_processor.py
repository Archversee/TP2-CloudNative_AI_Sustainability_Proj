import pdfplumber
import os
import json
import re

INPUT_DIR = "/data/raw_pdfs"
OUTPUT_DIR = "/data/processed_json"

CLAIM_KEYWORDS = [
    "plastic-free",
    "net zero",
    "carbon neutral",
    "sustainable packaging",
    "renewable energy",
    "zero emissions",
    "energy efficiency",
    "recyclable materials",
    "waste reduction",
    "water stewardship",
    "sustainable sourcing"
]

def safe_filename(company, year):
    return f"{company.replace(' ', '_')}_{year}.json"

def extract_scope_values(text):
    """
    Extract Scope 1 and Scope 2 numbers from page text.
    Returns (scope1_list, scope2_list) as floats.
    """
    clean_text = text.replace("\n", " ").replace("\r", " ")
    scope1_matches = re.findall(r"Scope\s*1[^\d]*([\d,]+(?:\.\d+)?)", clean_text, re.IGNORECASE)
    scope2_matches = re.findall(r"Scope\s*2[^\d]*([\d,]+(?:\.\d+)?)", clean_text, re.IGNORECASE)

    def parse_number(val):
        if val:
            val_clean = val.replace(",", "").rstrip(".")
            try:
                return float(val_clean)
            except ValueError:
                return None
        return None

    scope1_list = [parse_number(v) for v in scope1_matches if parse_number(v) is not None]
    scope2_list = [parse_number(v) for v in scope2_matches if parse_number(v) is not None]

    return scope1_list, scope2_list

def extract_scope_from_tables(page):
    """
    Extract Scope 1 and Scope 2 numbers from tables on the page.
    Returns dict: {"scope1": [...], "scope2": [...]}
    """
    values = {"scope1": [], "scope2": []}

    def parse_number(cell):
        if not cell:
            return None
        match = re.search(r"\d+(?:\.\d+)?", cell.replace(",", ""))
        if match:
            return float(match.group())
        return None

    for table in page.extract_tables():
        for row in table:
            if not row:
                continue
            row_text = " ".join(cell or "" for cell in row).lower()
            if "scope 1" in row_text:
                for cell in row[1:]:
                    num = parse_number(cell)
                    if num is not None:
                        values["scope1"].append(num)
            if "scope 2" in row_text:
                for cell in row[1:]:
                    num = parse_number(cell)
                    if num is not None:
                        values["scope2"].append(num)
    return values

def process_pdf(file_path):
    data = {
        "metrics": {
            "scope1_emissions_tco2e": [],
            "scope2_emissions_tco2e": []
        },
        "claims": []
    }

    claim_pages = {kw: set() for kw in CLAIM_KEYWORDS}

    with pdfplumber.open(file_path) as pdf:
        for i, page in enumerate(pdf.pages):
            text = page.extract_text() or ""

            # --- Claims ---
            for kw in CLAIM_KEYWORDS:
                if kw.lower() in text.lower():
                    claim_pages[kw].add(i + 1)

            # --- Scope from text ---
            scope1_list, scope2_list = extract_scope_values(text)
            for val in scope1_list:
                data["metrics"]["scope1_emissions_tco2e"].append({
                    "value": val,
                    "page": i + 1
                })
            for val in scope2_list:
                data["metrics"]["scope2_emissions_tco2e"].append({
                    "value": val,
                    "page": i + 1
                })

            # --- Scope from tables ---
            table_values = extract_scope_from_tables(page)
            for val in table_values.get("scope1", []):
                data["metrics"]["scope1_emissions_tco2e"].append({
                    "value": val,
                    "page": i + 1
                })
            for val in table_values.get("scope2", []):
                data["metrics"]["scope2_emissions_tco2e"].append({
                    "value": val,
                    "page": i + 1
                })

    # --- Format claims ---
    data["claims"] = [
        {"claim": claim, "pages": sorted(list(pages))}
        for claim, pages in claim_pages.items() if pages
    ]

    return data

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    for pdf_file in os.listdir(INPUT_DIR):
        if not pdf_file.lower().endswith(".pdf"):
            continue

        parts = pdf_file.replace(".pdf", "").rsplit("_", 1)
        company = parts[0]
        year = int(parts[1])

        input_path = os.path.join(INPUT_DIR, pdf_file)
        result = process_pdf(input_path)

        output = {
            "company": company,
            "year": year,
            "source": "Sustainability Report",
            **result
        }

        output_path = os.path.join(OUTPUT_DIR, safe_filename(company, year))
        with open(output_path, "w") as f:
            json.dump(output, f, indent=2)

        print(f"Processed {pdf_file} → {output_path}")

if __name__ == "__main__":
    main()
