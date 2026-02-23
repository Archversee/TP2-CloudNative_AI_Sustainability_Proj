import pdfplumber
import os
import json
import re
from datetime import datetime
from collections import defaultdict

INPUT_DIR = "/data/raw_pdfs"
OUTPUT_DIR = "/data/intermediate_json"

# COMPREHENSIVE ESG KEYWORD TAXONOMY
# === CORE EMISSIONS KEYWORDS ===
EMISSIONS_KEYWORDS = [
    # Scope classifications
    "scope 1", "scope 2", "scope 3",
    "scope 1 emissions", "scope 2 emissions", "scope 3 emissions",
    "scope one", "scope two", "scope three",
    "scopes 1 and 2", "scopes 1, 2 and 3",
    
    # GHG terminology
    "GHG emissions", "greenhouse gas emissions",
    "greenhouse gas", "GHG protocol",
    "direct emissions", "indirect emissions",
    "operational emissions", "energy indirect emissions",
    "value chain emissions", "supply chain emissions",
    
    # Carbon terminology
    "carbon emissions", "CO2 emissions", "CO2e emissions",
    "carbon dioxide emissions", "carbon footprint",
    "total emissions", "total GHG emissions",
    "absolute emissions", "emissions intensity",
    
    # Specific gases
    "methane emissions", "CH4 emissions",
    "nitrous oxide", "N2O emissions",
    "fluorinated gases", "HFC emissions",
]

# === NET ZERO & TARGETS ===
TARGET_KEYWORDS = [
    # Net zero variations
    "net zero", "net-zero", "net zero emissions",
    "net zero by", "net zero target",
    "achieve net zero", "pathway to net zero",
    
    # Carbon neutral
    "carbon neutral", "carbon neutrality",
    "carbon neutral by", "carbon negative",
    
    # Climate goals
    "climate neutral", "climate positive",
    "zero emissions", "emissions-free",
    "decarbonization", "decarbonisation",
    
    # Science-based targets
    "science-based targets", "SBTi", "SBT",
    "1.5°C target", "2°C target", "Paris Agreement",
    "science based target initiative",
]

# === ENERGY & RENEWABLES ===
ENERGY_KEYWORDS = [
    "renewable energy", "clean energy", "green energy",
    "solar energy", "wind energy", "hydroelectric",
    "renewable electricity", "renewable power",
    "energy consumption", "energy efficiency",
    "energy intensity", "total energy use",
    "fossil fuel", "natural gas", "coal", "oil",
    "renewable energy certificate", "REC", "I-REC",
]

# === WATER & RESOURCES ===
RESOURCE_KEYWORDS = [
    "water consumption", "water usage", "water withdrawal",
    "water intensity", "water stress", "water scarcity",
    "waste generated", "waste recycled", "waste to landfill",
    "circular economy", "recycling rate",
    "material consumption", "raw materials",
]

# === BIODIVERSITY & NATURE ===
NATURE_KEYWORDS = [
    "biodiversity", "ecosystem", "habitat",
    "deforestation", "reforestation", "afforestation",
    "land use", "land degradation",
    "protected areas", "nature-based solutions",
]

# === SOCIAL & GOVERNANCE ===
SOCIAL_KEYWORDS = [
    "employee safety", "health and safety", "lost time injury",
    "diversity and inclusion", "gender diversity",
    "human rights", "labor practices",
    "community engagement", "stakeholder engagement",
]

# === CERTIFICATIONS & STANDARDS ===
STANDARDS_KEYWORDS = [
    "GRI", "TCFD", "CDP", "SASB", "ISSB",
    "ISO 14001", "ISO 50001",
    "LEED certification", "green building",
    "B Corp", "carbon disclosure",
]

# Combine all keywords and remove duplicates
ALL_SUSTAINABILITY_KEYWORDS = (
    EMISSIONS_KEYWORDS +
    TARGET_KEYWORDS +
    ENERGY_KEYWORDS +
    RESOURCE_KEYWORDS +
    NATURE_KEYWORDS +
    SOCIAL_KEYWORDS +
    STANDARDS_KEYWORDS
)

CLAIM_KEYWORDS = sorted(list(set(ALL_SUSTAINABILITY_KEYWORDS)))

# Map emission-related claims
EMISSIONS_CLAIMS = {
    "scope 1", "scope 2", "scope 3",
    "scope 1 emissions", "scope 2 emissions", "scope 3 emissions",
    "net zero", "carbon neutral", "zero emissions", 
    "carbon footprint", "climate neutral",
    "GHG emissions", "greenhouse gas emissions",
    "direct emissions", "indirect emissions",
    "carbon emissions", "CO2 emissions", "total emissions"
}


# CLAIM-TO-UNIT MAPPINGS
CLAIM_UNITS = {
    # Emissions-related
    "net zero": ["tCO2e", "tCO2", "tonnes CO2e"],
    "carbon neutral": ["tCO2e", "tCO2", "tonnes CO2e"],
    "zero emissions": ["tCO2e", "tCO2", "tonnes CO2e"],
    "carbon footprint": ["tCO2e", "tCO2", "tonnes CO2e"],
    "climate neutral": ["tCO2e", "tCO2", "tonnes CO2e"],
    "GHG emissions": ["tCO2e", "tCO2", "tonnes CO2e"],
    "carbon emissions": ["tCO2e", "tCO2", "tonnes CO2e"],
    "scope 1": ["tCO2e", "tCO2", "tonnes CO2e"],
    "scope 2": ["tCO2e", "tCO2", "tonnes CO2e"],
    "scope 3": ["tCO2e", "tCO2", "tonnes CO2e"],
    
    # Energy-related
    "renewable energy": ["MWh", "kWh", "GWh", "%", "percent"],
    "green energy": ["MWh", "kWh", "GWh", "%", "percent"],
    "energy consumption": ["MWh", "kWh", "GWh", "TJ"],
    
    # Reduction targets
    "emission reduction": ["tCO2e", "tCO2", "%", "percent"],
    "sustainability target": ["tCO2e", "tCO2", "%", "percent"],
    
    # Water
    "water consumption": ["m3", "ML", "liters", "gallons"],
    
    # Waste
    "waste generated": ["tonnes", "kg", "tons"],
    "waste recycled": ["tonnes", "kg", "%", "percent"],
}

# SCOPE EXTRACTION PATTERNS
SCOPE_PATTERNS = {
    "scope1": [
        # Standard formats
        r"Scope\s*1[:\s]+emissions?[:\s]*([\d,]+(?:\.\d+)?)",
        r"Scope\s*1[:\s]+([\d,]+(?:\.\d+)?)\s*(tCO2e|tCO2|tonnes?\s*CO2e?)?",
        r"Scope\s*One[:\s]+emissions?[:\s]*([\d,]+(?:\.\d+)?)",
        
        # Direct emissions synonyms
        r"Direct\s+emissions[:\s]+([\d,]+(?:\.\d+)?)",
        r"Direct\s+GHG\s+emissions[:\s]+([\d,]+(?:\.\d+)?)",
        r"Stationary\s+combustion[:\s]+([\d,]+(?:\.\d+)?)",
        r"Mobile\s+combustion[:\s]+([\d,]+(?:\.\d+)?)",
        r"Process\s+emissions[:\s]+([\d,]+(?:\.\d+)?)",
        r"Fugitive\s+emissions[:\s]+([\d,]+(?:\.\d+)?)",
        
        # Table headers
        r"Scope\s*1\s*\n\s*([\d,]+(?:\.\d+)?)",
        r"\|\s*Scope\s*1\s*\|\s*([\d,]+(?:\.\d+)?)",
        
        # With units explicitly
        r"([\d,]+(?:\.\d+)?)\s*tCO2e?\s*\(Scope\s*1\)",
        r"([\d,]+(?:\.\d+)?)\s*tonnes?\s*CO2e?\s*\(Scope\s*1\)",
        
        # Financial year variations
        r"Scope\s*1.*?FY\d{2,4}[:\s]+([\d,]+(?:\.\d+)?)",
        r"Scope\s*1.*?20\d{2}[:\s]+([\d,]+(?:\.\d+)?)",
    ],
    
    "scope2": [
        # Standard formats
        r"Scope\s*2[:\s]+emissions?[:\s]*([\d,]+(?:\.\d+)?)",
        r"Scope\s*2[:\s]+([\d,]+(?:\.\d+)?)\s*(tCO2e|tCO2|tonnes?\s*CO2e?)?",
        r"Scope\s*Two[:\s]+emissions?[:\s]*([\d,]+(?:\.\d+)?)",
        
        # Indirect/energy synonyms
        r"Indirect\s+emissions[:\s]+([\d,]+(?:\.\d+)?)",
        r"Energy\s+indirect[:\s]+emissions?[:\s]*([\d,]+(?:\.\d+)?)",
        r"Purchased\s+electricity[:\s]+emissions?[:\s]*([\d,]+(?:\.\d+)?)",
        r"Electricity\s+consumption[:\s]+emissions?[:\s]*([\d,]+(?:\.\d+)?)",
        
        # Location-based vs Market-based
        r"Scope\s*2\s*\(location-based\)[:\s]+([\d,]+(?:\.\d+)?)",
        r"Scope\s*2\s*\(market-based\)[:\s]+([\d,]+(?:\.\d+)?)",
        r"Scope\s*2\s*-\s*Location[:\s]+([\d,]+(?:\.\d+)?)",
        r"Scope\s*2\s*-\s*Market[:\s]+([\d,]+(?:\.\d+)?)",
        
        # Table headers
        r"Scope\s*2\s*\n\s*([\d,]+(?:\.\d+)?)",
        r"\|\s*Scope\s*2\s*\|\s*([\d,]+(?:\.\d+)?)",
        
        # With units
        r"([\d,]+(?:\.\d+)?)\s*tCO2e?\s*\(Scope\s*2\)",
        r"([\d,]+(?:\.\d+)?)\s*tonnes?\s*CO2e?\s*\(Scope\s*2\)",
        
        # Financial year variations
        r"Scope\s*2.*?FY\d{2,4}[:\s]+([\d,]+(?:\.\d+)?)",
        r"Scope\s*2.*?20\d{2}[:\s]+([\d,]+(?:\.\d+)?)",
    ],
    
    "scope3": [
        # Standard formats
        r"Scope\s*3[:\s]+emissions?[:\s]*([\d,]+(?:\.\d+)?)",
        r"Scope\s*3[:\s]+([\d,]+(?:\.\d+)?)\s*(tCO2e|tCO2|tonnes?\s*CO2e?)?",
        r"Scope\s*Three[:\s]+emissions?[:\s]*([\d,]+(?:\.\d+)?)",
        
        # Value chain synonyms
        r"Value\s+chain\s+emissions[:\s]+([\d,]+(?:\.\d+)?)",
        r"Supply\s+chain\s+emissions[:\s]+([\d,]+(?:\.\d+)?)",
        r"Upstream\s+emissions[:\s]+([\d,]+(?:\.\d+)?)",
        r"Downstream\s+emissions[:\s]+([\d,]+(?:\.\d+)?)",
        r"Other\s+indirect\s+emissions[:\s]+([\d,]+(?:\.\d+)?)",
        
        # Specific categories
        r"Business\s+travel[:\s]+emissions?[:\s]*([\d,]+(?:\.\d+)?)",
        r"Employee\s+commuting[:\s]+emissions?[:\s]*([\d,]+(?:\.\d+)?)",
        r"Purchased\s+goods[:\s]+emissions?[:\s]*([\d,]+(?:\.\d+)?)",
        
        # Table headers
        r"Scope\s*3\s*\n\s*([\d,]+(?:\.\d+)?)",
        r"\|\s*Scope\s*3\s*\|\s*([\d,]+(?:\.\d+)?)",
    ],
    
    "total": [
        # Total emissions
        r"Total\s+GHG\s+emissions[:\s]+([\d,]+(?:\.\d+)?)",
        r"Total\s+emissions[:\s]+([\d,]+(?:\.\d+)?)",
        r"Total\s+carbon\s+emissions[:\s]+([\d,]+(?:\.\d+)?)",
        r"Gross\s+emissions[:\s]+([\d,]+(?:\.\d+)?)",
        r"Total\s+Scope\s+1\s+and\s+2[:\s]+([\d,]+(?:\.\d+)?)",
        r"Total\s+Scopes?\s+1,\s*2\s*(?:and|&)?\s*3[:\s]+([\d,]+(?:\.\d+)?)",
    ]
}

# Improved numeric regex patterns
NUMERIC_PATTERN = r"([\d]{1,3}(?:[,\s]?\d{3})*(?:\.\d+)?)\s*(tCO2e|tCO2|tonnes\s+CO2e?|t\s+CO2e?|kg|tonnes?|%|percent|MWh|kWh|GWh|TJ|L|liters?|m3|m³|ML)?"

# HELPER FUNCTIONS
def safe_filename(company, year):
    return f"{company.replace(' ', '_')}_{year}.json"

def parse_number(val):
    """Parse number, handling commas and various formats."""
    if not val:
        return None
    try:
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
    if "tj" in unit:
        return "TJ"
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
    
    # Normalize volume
    if unit == "m3" or unit == "m³":
        return "m3"
    if unit == "ml":
        return "ML"
    
    return unit

def extract_target_year(text):
    """Extract target year from text with improved patterns."""
    patterns = [
        r"by\s+(20\d{2})",
        r"target\s+year[:\s]+(20\d{2})",
        r"achieve.*?(20\d{2})",
        r"reach.*?(20\d{2})",
        r"goal.*?(20\d{2})",
        r"commitment.*?(20\d{2})",
        r"pledge.*?(20\d{2})",
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text.lower())
        if match:
            year = int(match.group(1))
            if 2020 <= year <= 2100:
                return year
    return None

def extract_sentence_context(text, claim_keyword, num_sentences=3):
    """
    Extract full sentences around the claim for better context.
    Returns up to num_sentences before and after the claim.
    """
    claim_pos = text.lower().find(claim_keyword.lower())
    if claim_pos == -1:
        return ""
    
    sentences = re.split(r'(?<=[.!?])\s+', text)
    
    current_pos = 0
    claim_sentence_idx = -1
    
    for idx, sentence in enumerate(sentences):
        sentence_end = current_pos + len(sentence)
        if current_pos <= claim_pos < sentence_end:
            claim_sentence_idx = idx
            break
        current_pos = sentence_end + 1
    
    if claim_sentence_idx == -1:
        return extract_claim_context(text, claim_keyword, window=300)
    
    start_idx = max(0, claim_sentence_idx - num_sentences)
    end_idx = min(len(sentences), claim_sentence_idx + num_sentences + 1)
    
    context_sentences = sentences[start_idx:end_idx]
    context = " ".join(context_sentences).replace("\n", " ").strip()
    
    if len(context) > 500:
        context = context[:500] + "..."
    
    return context

def extract_claim_context(text, claim_keyword, window=300):
    """Extract surrounding text context for a claim (character-based fallback)."""
    claim_pos = text.lower().find(claim_keyword.lower())
    if claim_pos == -1:
        return ""
    
    start = max(0, claim_pos - window)
    end = min(len(text), claim_pos + len(claim_keyword) + window)
    context = text[start:end].replace("\n", " ").strip()
    
    return context

def extract_supporting_evidence(context, claim_keyword):
    """Extract key supporting information from context."""
    evidence = {
        "has_target_year": False,
        "has_numeric_data": False,
        "has_commitment_language": False,
        "key_phrases": []
    }
    
    target_year = extract_target_year(context)
    if target_year:
        evidence["has_target_year"] = True
        evidence["target_year"] = target_year
    
    numeric_matches = re.findall(NUMERIC_PATTERN, context, re.I)
    if numeric_matches:
        evidence["has_numeric_data"] = True
        evidence["numeric_count"] = len(numeric_matches)
    
    commitment_words = [
        "committed", "pledge", "target", "goal", "aim", 
        "plan", "strategy", "initiative", "invest", "reduce"
    ]
    
    found_commitments = [word for word in commitment_words if word in context.lower()]
    if found_commitments:
        evidence["has_commitment_language"] = True
        evidence["commitment_words"] = found_commitments[:3]
    
    sentences = re.split(r'[.!?]', context)
    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
        
        if re.search(r'\d', sentence) or any(word in sentence.lower() for word in commitment_words[:5]):
            if len(sentence) > 20:
                evidence["key_phrases"].append(sentence[:150])
                if len(evidence["key_phrases"]) >= 3:
                    break
    
    return evidence

# SCOPE EXTRACTION FUNCTIONS
def extract_scope_from_text(text, page_num):
    """Extract Scope 1, 2, and 3 emissions with comprehensive patterns."""
    clean = text.replace("\n", " ")
    scope1, scope2, scope3, total = [], [], [], []
    
    # Extract Scope 1
    for pattern in SCOPE_PATTERNS["scope1"]:
        matches = re.findall(pattern, clean, re.I)
        for match in matches:
            value_str = match[0] if isinstance(match, tuple) else match
            val = parse_number(value_str)
            if val is not None and val > 0:
                scope1.append({
                    "value": val,
                    "page": page_num,
                    "unit": "tCO2e",
                    "source": "text_extraction"
                })
    
    # Extract Scope 2
    for pattern in SCOPE_PATTERNS["scope2"]:
        matches = re.findall(pattern, clean, re.I)
        for match in matches:
            value_str = match[0] if isinstance(match, tuple) else match
            val = parse_number(value_str)
            if val is not None and val > 0:
                scope2.append({
                    "value": val,
                    "page": page_num,
                    "unit": "tCO2e",
                    "source": "text_extraction"
                })
    
    # Extract Scope 3 (NEW!)
    for pattern in SCOPE_PATTERNS["scope3"]:
        matches = re.findall(pattern, clean, re.I)
        for match in matches:
            value_str = match[0] if isinstance(match, tuple) else match
            val = parse_number(value_str)
            if val is not None and val > 0:
                scope3.append({
                    "value": val,
                    "page": page_num,
                    "unit": "tCO2e",
                    "source": "text_extraction"
                })
    
    # Extract Total
    for pattern in SCOPE_PATTERNS["total"]:
        matches = re.findall(pattern, clean, re.I)
        for match in matches:
            value_str = match[0] if isinstance(match, tuple) else match
            val = parse_number(value_str)
            if val is not None and val > 0:
                total.append({
                    "value": val,
                    "page": page_num,
                    "unit": "tCO2e",
                    "source": "text_extraction"
                })
    
    return scope1, scope2, scope3, total

def extract_scope_from_tables(page, page_num):
    """
    Enhanced table extraction with column detection and multiple strategies.
    """
    scope1, scope2, scope3, total = [], [], [], []
    
    try:
        tables = page.extract_tables()
        if not tables:
            return scope1, scope2, scope3, total
        
        for table_idx, table in enumerate(tables):
            if not table or len(table) < 2:
                continue
            
            # Strategy 1: Find header row
            header_row_idx = -1
            for idx, row in enumerate(table):
                if not row:
                    continue
                row_text = " ".join(str(cell or "") for cell in row).lower()
                
                if any(h in row_text for h in ["scope", "emissions", "ghg", "category", "type"]):
                    header_row_idx = idx
                    break
            
            # Strategy 2: Find column indices for scope data
            scope1_cols, scope2_cols, scope3_cols = [], [], []
            
            if header_row_idx >= 0 and header_row_idx < len(table):
                header = table[header_row_idx]
                for col_idx, cell in enumerate(header):
                    if not cell:
                        continue
                    cell_text = str(cell).lower()
                    
                    if "scope 1" in cell_text or "scope1" in cell_text:
                        scope1_cols.append(col_idx)
                    if "scope 2" in cell_text or "scope2" in cell_text:
                        scope2_cols.append(col_idx)
                    if "scope 3" in cell_text or "scope3" in cell_text:
                        scope3_cols.append(col_idx)
            
            # Strategy 3: Process data rows
            for row_idx in range(header_row_idx + 1, len(table)):
                row = table[row_idx]
                if not row:
                    continue
                
                # Check row label
                row_label = str(row[0] or "").lower() if row else ""
                
                # Extract from identified columns
                for col_idx in scope1_cols:
                    if col_idx < len(row) and row[col_idx]:
                        val = parse_number(str(row[col_idx]))
                        if val and val > 0:
                            scope1.append({
                                "value": val,
                                "page": page_num,
                                "unit": "tCO2e",
                                "source": f"table_{table_idx}_col_{col_idx}"
                            })
                
                for col_idx in scope2_cols:
                    if col_idx < len(row) and row[col_idx]:
                        val = parse_number(str(row[col_idx]))
                        if val and val > 0:
                            scope2.append({
                                "value": val,
                                "page": page_num,
                                "unit": "tCO2e",
                                "source": f"table_{table_idx}_col_{col_idx}"
                            })
                
                for col_idx in scope3_cols:
                    if col_idx < len(row) and row[col_idx]:
                        val = parse_number(str(row[col_idx]))
                        if val and val > 0:
                            scope3.append({
                                "value": val,
                                "page": page_num,
                                "unit": "tCO2e",
                                "source": f"table_{table_idx}_col_{col_idx}"
                            })
                
                # Strategy 4: Check row labels for scope keywords
                if any(kw in row_label for kw in ["scope 1", "scope1", "direct emission"]):
                    for cell in row[1:]:
                        if cell:
                            val = parse_number(str(cell))
                            if val and val > 0:
                                scope1.append({
                                    "value": val,
                                    "page": page_num,
                                    "unit": "tCO2e",
                                    "source": f"table_{table_idx}_label"
                                })
                
                if any(kw in row_label for kw in ["scope 2", "scope2", "indirect", "energy indirect"]):
                    for cell in row[1:]:
                        if cell:
                            val = parse_number(str(cell))
                            if val and val > 0:
                                scope2.append({
                                    "value": val,
                                    "page": page_num,
                                    "unit": "tCO2e",
                                    "source": f"table_{table_idx}_label"
                                })
                
                if any(kw in row_label for kw in ["scope 3", "scope3", "value chain", "supply chain"]):
                    for cell in row[1:]:
                        if cell:
                            val = parse_number(str(cell))
                            if val and val > 0:
                                scope3.append({
                                    "value": val,
                                    "page": page_num,
                                    "unit": "tCO2e",
                                    "source": f"table_{table_idx}_label"
                                })
    
    except Exception as e:
        print(f"  Table extraction warning on page {page_num}: {type(e).__name__}", flush=True)
    
    return scope1, scope2, scope3, total

def extract_generic_metrics(text, page_num):
    """Extract all numeric patterns with improved unit detection."""
    matches = re.findall(NUMERIC_PATTERN, text, re.I)
    metrics = []
    
    for val, unit in matches:
        num = parse_number(val)
        if num is not None and num > 0:
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
    allowed_units_normalized = [normalize_unit(u) for u in allowed_units]
    
    filtered = []
    for m in metrics:
        metric_unit = m.get("unit", "")
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


# MAIN PROCESSING FUNCTION
def process_pdf(file_path):
    """Process PDF with comprehensive keyword extraction and improved error handling."""
    page_metrics = []
    claims = []
    pdf_filename = os.path.basename(file_path)
    
    stats = {
        "total_pages": 0,
        "text_extraction_failures": 0,
        "table_extraction_failures": 0,
        "claims_found": 0,
        "claims_with_context": 0,
        "claims_with_evidence": 0,
        "scope1_found": 0,
        "scope2_found": 0,
        "scope3_found": 0,
        "keywords_loaded": len(CLAIM_KEYWORDS)
    }

    print(f"  Processing with {stats['keywords_loaded']} ESG keywords...", flush=True)

    try:
        with pdfplumber.open(file_path) as pdf:
            stats["total_pages"] = len(pdf.pages)
            
            for i, page in enumerate(pdf.pages):
                page_num = i + 1
                
                # Extract text
                text = ""
                try:
                    text = page.extract_text() or ""
                except Exception as e:
                    stats["text_extraction_failures"] += 1
                    print(f"  Warning: Page {page_num} text extraction failed: {type(e).__name__}", flush=True)

                # Extract emissions from text
                s1_text, s2_text, s3_text, total_text = extract_scope_from_text(text, page_num)
                
                # Extract emissions from tables
                s1_table, s2_table, s3_table, total_table = [], [], [], []
                try:
                    s1_table, s2_table, s3_table, total_table = extract_scope_from_tables(page, page_num)
                except Exception as e:
                    stats["table_extraction_failures"] += 1
                
                # Combine and deduplicate
                scope1 = deduplicate_metrics_on_page(s1_text + s1_table)
                scope2 = deduplicate_metrics_on_page(s2_text + s2_table)
                scope3 = deduplicate_metrics_on_page(s3_text + s3_table)
                total_emissions = deduplicate_metrics_on_page(total_text + total_table)
                
                generic_metrics = extract_generic_metrics(text, page_num)
                generic_metrics = deduplicate_metrics_on_page(generic_metrics)

                # Update stats
                stats["scope1_found"] += len(scope1)
                stats["scope2_found"] += len(scope2)
                stats["scope3_found"] += len(scope3)

                page_metrics.append({
                    "page": page_num,
                    "scope1_emissions_tco2e": scope1,
                    "scope2_emissions_tco2e": scope2,
                    "scope3_emissions_tco2e": scope3,
                    "total_emissions_tco2e": total_emissions,
                    "generic_metrics": generic_metrics
                })

                # Detect claims with comprehensive keyword list
                for kw in CLAIM_KEYWORDS:
                    if kw.lower() in text.lower():
                        context = extract_sentence_context(text, kw, num_sentences=3)
                        
                        if not context or len(context) < 50:
                            context = extract_claim_context(text, kw, window=300)
                        
                        evidence = extract_supporting_evidence(context, kw)
                        
                        # Determine metrics for this claim
                        if kw in EMISSIONS_CLAIMS:
                            claim_metrics = {
                                "scope1_emissions_tco2e": scope1,
                                "scope2_emissions_tco2e": scope2,
                                "scope3_emissions_tco2e": scope3,
                                "generic_metrics": []
                            }
                        else:
                            claim_metrics = {
                                "scope1_emissions_tco2e": [],
                                "scope2_emissions_tco2e": [],
                                "scope3_emissions_tco2e": [],
                                "generic_metrics": filter_metrics_by_claim(generic_metrics, kw)
                            }

                        claim_obj = {
                            "claim": kw,
                            "page": page_num,
                            "target_year": extract_target_year(context),
                            "context": context,
                            "evidence": evidence,
                            "metrics": claim_metrics
                        }
                        
                        claims.append(claim_obj)
                        stats["claims_found"] += 1
                        
                        if context and len(context) > 50:
                            stats["claims_with_context"] += 1
                        if evidence.get("has_numeric_data") or evidence.get("has_target_year"):
                            stats["claims_with_evidence"] += 1
            
            # Log statistics
            print(f"  Extraction complete:", flush=True)
            print(f"    Pages: {stats['total_pages']}", flush=True)
            print(f"    Claims found: {stats['claims_found']}", flush=True)
            print(f"    Scope 1 metrics: {stats['scope1_found']}", flush=True)
            print(f"    Scope 2 metrics: {stats['scope2_found']}", flush=True)
            print(f"    Scope 3 metrics: {stats['scope3_found']}", flush=True)
            
            if stats["text_extraction_failures"] > 0:
                print(f"    Text failures: {stats['text_extraction_failures']}", flush=True)
            if stats["table_extraction_failures"] > 0:
                print(f"    Table failures: {stats['table_extraction_failures']}", flush=True)

    except Exception as e:
        print(f"  ERROR: Failed to process PDF: {type(e).__name__}: {e}", flush=True)
        return {
            "processed_at": datetime.utcnow().isoformat(),
            "page_metrics": [],
            "claims": [],
            "processing_error": str(e),
            "stats": stats
        }

    return {
        "processed_at": datetime.utcnow().isoformat(),
        "page_metrics": page_metrics,
        "claims": claims,
        "stats": stats
    }

# STANDALONE EXECUTION (for testing)
def main():
    """Standalone execution for testing."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    successful = 0
    failed = 0
    
    total_claims = 0
    total_scope1 = 0
    total_scope2 = 0
    total_scope3 = 0
    claims_with_good_context = 0
    
    print(f"\n=== PDF Processor with {len(CLAIM_KEYWORDS)} ESG Keywords ===\n", flush=True)
    
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

            claims_count = len(output.get("claims", []))
            total_claims += claims_count
            
            for claim in output.get("claims", []):
                if claim.get("context") and len(claim.get("context", "")) > 100:
                    claims_with_good_context += 1
            
            for page in output.get("page_metrics", []):
                total_scope1 += len(page.get("scope1_emissions_tco2e", []))
                total_scope2 += len(page.get("scope2_emissions_tco2e", []))
                total_scope3 += len(page.get("scope3_emissions_tco2e", []))

            output_path = os.path.join(OUTPUT_DIR, safe_filename(name, year))
            with open(output_path, "w") as f:
                json.dump(output, f, indent=2)

            print(f"✓ {pdf_file} → {claims_count} claims, S1:{total_scope1}, S2:{total_scope2}, S3:{total_scope3}", flush=True)
            successful += 1
            
        except Exception as e:
            print(f"✗ Failed: {pdf_file}: {type(e).__name__}: {e}", flush=True)
            failed += 1
    
    print(f"\n=== Processing Complete ===", flush=True)
    print(f"Successful: {successful}", flush=True)
    print(f"Failed: {failed}", flush=True)
    print(f"Keywords used: {len(CLAIM_KEYWORDS)}", flush=True)
    print(f"Total claims: {total_claims}", flush=True)
    print(f"Claims with context (>100 chars): {claims_with_good_context}", flush=True)
    print(f"Total Scope 1 metrics: {total_scope1}", flush=True)
    print(f"Total Scope 2 metrics: {total_scope2}", flush=True)
    print(f"Total Scope 3 metrics: {total_scope3}", flush=True)

if __name__ == "__main__":
    main()