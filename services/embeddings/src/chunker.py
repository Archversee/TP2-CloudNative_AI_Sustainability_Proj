"""
Enhanced chunker.py that works with both raw PDFs and audited JSON
"""
import pdfplumber
import os
import json
import re
from typing import List, Dict

INPUT_DIR = "/data/raw_pdfs"
OUTPUT_DIR = "/data/chunks"

# Chunking configuration
CHUNK_SIZE = 500
CHUNK_OVERLAP = 100
MIN_CHUNK_SIZE = 100

def clean_text(text: str) -> str:
    """Clean and normalize text."""
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'Page \d+ of \d+', '', text, flags=re.I)
    text = re.sub(r'^\d+\s*$', '', text, flags=re.MULTILINE)
    return text.strip()

def split_into_sentences(text: str) -> List[str]:
    """Split text into sentences for semantic chunking."""
    sentences = re.split(r'(?<=[.!?])\s+', text)
    return [s.strip() for s in sentences if s.strip()]

def create_semantic_chunks(text: str, chunk_size: int = CHUNK_SIZE, 
                          overlap: int = CHUNK_OVERLAP) -> List[str]:
    """Create overlapping chunks that respect sentence boundaries."""
    sentences = split_into_sentences(text)
    chunks = []
    current_chunk = []
    current_length = 0
    
    for sentence in sentences:
        sentence_length = len(sentence)
        
        if current_length + sentence_length > chunk_size and current_chunk:
            chunks.append(' '.join(current_chunk))
            
            overlap_sentences = []
            overlap_length = 0
            for s in reversed(current_chunk):
                if overlap_length + len(s) <= overlap:
                    overlap_sentences.insert(0, s)
                    overlap_length += len(s)
                else:
                    break
            
            current_chunk = overlap_sentences
            current_length = overlap_length
        
        current_chunk.append(sentence)
        current_length += sentence_length
    
    if current_chunk:
        chunks.append(' '.join(current_chunk))
    
    return chunks

def extract_chunks_from_pdf(pdf_path: str) -> List[Dict]:
    """Extract text chunks from PDF with metadata."""
    chunks = []
    filename = os.path.basename(pdf_path)
    
    try:
        name, year = filename.replace('.pdf', '').rsplit('_', 1)
        company = name.replace('_', ' ')
        year = int(year)
    except:
        print(f"Warning: Could not parse filename {filename}")
        company = filename
        year = 0
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages, 1):
                try:
                    text = page.extract_text() or ""
                    if not text.strip():
                        continue
                    
                    text = clean_text(text)
                    page_chunks = create_semantic_chunks(text)
                    
                    for chunk_idx, chunk_text in enumerate(page_chunks):
                        if len(chunk_text) < MIN_CHUNK_SIZE:
                            continue
                        
                        chunks.append({
                            'company': company,
                            'year': year,
                            'page': page_num,
                            'chunk_index': chunk_idx,
                            'content': chunk_text,
                            'metadata': {
                                'source': filename,
                                'chunk_size': len(chunk_text),
                                'total_page_chunks': len(page_chunks)
                            }
                        })
                
                except Exception as e:
                    print(f"Error processing page {page_num} in {filename}: {e}")
                    continue
    
    except Exception as e:
        print(f"Error opening PDF {pdf_path}: {e}")
        return []
    
    return chunks

def chunk_document(report_data: dict) -> list:
    """
    Chunk an audited report JSON into searchable chunks.
    Works with the output from ai_auditor.
    
    Args:
        report_data: Audited JSON with 'claims' and 'ai_summary'
    
    Returns:
        List of chunk dicts with embeddings-ready structure
    """
    chunks = []
    company = report_data.get('company', 'Unknown Company')
    year = report_data.get('year', 0)
    
    # Chunk from AI summary (overall context)
    ai_summary = report_data.get('ai_summary', {})
    if ai_summary.get('overall_summary'):
        summary_text = ai_summary.get('overall_summary', '')
        
        chunks.append({
            'company': company,
            'year': year,
            'page': 1,  # Summary doesn't have specific page
            'chunk_index': 0,
            'content': f"Company: {company} ({year}). Overall Assessment: {summary_text}",
            'metadata': {
                'type': 'summary',
                'source': 'ai_audit',
                'overall_score': ai_summary.get('overall_score')
            }
        })
    
    # Create chunks from claims
    claims = report_data.get('claims', [])
    
    for idx, claim in enumerate(claims, start=1):
        claim_text = claim.get('claim', '')
        page = claim.get('page', 1)
        context = claim.get('context', '')
        target_year = claim.get('target_year')
        
        # Find AI review for this claim
        claim_review = None
        for review in ai_summary.get('claim_reviews', []):
            if review.get('claim') == claim_text and review.get('page') == page:
                claim_review = review
                break
        
        # Build rich chunk content
        content_parts = [
            f"Company: {company} ({year})",
            f"Sustainability Claim: {claim_text}"
        ]
        
        if target_year:
            content_parts.append(f"Target Year: {target_year}")
        
        if context:
            # Clean up context
            clean_context = clean_text(context)
            if clean_context:
                content_parts.append(f"Context: {clean_context}")
        
        if claim_review:
            score = claim_review.get('score', 'N/A')
            reason = claim_review.get('reason', '')
            citations = claim_review.get('citations', [])
            
            content_parts.append(f"AI Assessment Score: {score}/5")
            if reason:
                content_parts.append(f"Analysis: {reason}")
            if citations:
                content_parts.append(f"Referenced Pages: {', '.join(map(str, citations))}")
        
        chunk_content = ' | '.join(content_parts)
        
        # Only add if substantial content
        if len(chunk_content) >= MIN_CHUNK_SIZE:
            chunks.append({
                'company': company,
                'year': year,
                'page': page,
                'chunk_index': idx,
                'content': chunk_content,
                'metadata': {
                    'type': 'claim',
                    'source': 'sustainability_report',
                    'claim': claim_text,
                    'target_year': target_year,
                    'ai_score': claim_review.get('score') if claim_review else None
                }
            })
    
    # If no chunks created, try extracting from page_metrics
    if not chunks and 'page_metrics' in report_data:
        for page_data in report_data.get('page_metrics', [])[:5]:  # First 5 pages
            page_num = page_data.get('page', 0)
            
            # Create chunk from emissions data
            scope1 = page_data.get('scope1_emissions_tco2e', [])
            scope2 = page_data.get('scope2_emissions_tco2e', [])
            
            if scope1 or scope2:
                emissions_text = f"Company: {company} ({year}). "
                
                if scope1:
                    total_s1 = sum(m.get('value', 0) for m in scope1)
                    emissions_text += f"Scope 1 emissions: {total_s1:.2f} tCO2e. "
                
                if scope2:
                    total_s2 = sum(m.get('value', 0) for m in scope2)
                    emissions_text += f"Scope 2 emissions: {total_s2:.2f} tCO2e. "
                
                chunks.append({
                    'company': company,
                    'year': year,
                    'page': page_num,
                    'chunk_index': len(chunks),
                    'content': emissions_text,
                    'metadata': {
                        'type': 'emissions_data',
                        'source': 'pdf_extraction'
                    }
                })
    
    return chunks

def process_all_pdfs():
    """Process all PDFs and save chunks to JSON."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    total_chunks = 0
    total_files = 0
    
    for pdf_file in sorted(os.listdir(INPUT_DIR)):
        if not pdf_file.lower().endswith('.pdf'):
            continue
        
        print(f"\nProcessing {pdf_file}...")
        pdf_path = os.path.join(INPUT_DIR, pdf_file)
        
        chunks = extract_chunks_from_pdf(pdf_path)
        
        if chunks:
            output_file = pdf_file.replace('.pdf', '_chunks.json')
            output_path = os.path.join(OUTPUT_DIR, output_file)
            
            with open(output_path, 'w') as f:
                json.dump(chunks, f, indent=2)
            
            print(f" Created {len(chunks)} chunks → {output_path}")
            total_chunks += len(chunks)
            total_files += 1
        else:
            print(f" No chunks created for {pdf_file}")
    
    print(f"\n Chunking Complete - Processed {total_files} PDFs, created {total_chunks} chunks")

if __name__ == "__main__":
    process_all_pdfs()