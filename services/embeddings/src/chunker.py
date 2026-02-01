import pdfplumber
import os
import json
import re
from typing import List, Dict

INPUT_DIR = "/data/raw_pdfs"
OUTPUT_DIR = "/data/chunks"

# Chunking configuration
CHUNK_SIZE = 500  # characters
CHUNK_OVERLAP = 100  # overlap between chunks
MIN_CHUNK_SIZE = 100  # minimum viable chunk size

def clean_text(text: str) -> str:
    """Clean and normalize text."""
    # Remove excessive whitespace
    text = re.sub(r'\s+', ' ', text)
    # Remove page numbers and headers/footers patterns
    text = re.sub(r'Page \d+ of \d+', '', text, flags=re.I)
    text = re.sub(r'^\d+\s*$', '', text, flags=re.MULTILINE)
    return text.strip()

def split_into_sentences(text: str) -> List[str]:
    """Split text into sentences for semantic chunking."""
    # Simple sentence splitting (can be enhanced with spaCy/NLTK)
    sentences = re.split(r'(?<=[.!?])\s+', text)
    return [s.strip() for s in sentences if s.strip()]

def create_semantic_chunks(text: str, chunk_size: int = CHUNK_SIZE, 
                          overlap: int = CHUNK_OVERLAP) -> List[str]:
    """
    Create overlapping chunks that respect sentence boundaries.
    This preserves semantic meaning better than fixed-length splitting.
    """
    sentences = split_into_sentences(text)
    chunks = []
    current_chunk = []
    current_length = 0
    
    for sentence in sentences:
        sentence_length = len(sentence)
        
        # If adding this sentence exceeds chunk size
        if current_length + sentence_length > chunk_size and current_chunk:
            # Save current chunk
            chunks.append(' '.join(current_chunk))
            
            # Start new chunk with overlap
            # Keep last few sentences for context
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
    
    # Add final chunk
    if current_chunk:
        chunks.append(' '.join(current_chunk))
    
    return chunks

def extract_chunks_from_pdf(pdf_path: str) -> List[Dict]:
    """
    Extract text chunks from PDF with metadata.
    Returns list of dicts with chunk info.
    """
    chunks = []
    filename = os.path.basename(pdf_path)
    
    # Extract company and year from filename
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
                    
                    # Clean text
                    text = clean_text(text)
                    
                    # Create chunks for this page
                    page_chunks = create_semantic_chunks(text)
                    
                    # Add metadata to each chunk
                    for chunk_idx, chunk_text in enumerate(page_chunks):
                        if len(chunk_text) < MIN_CHUNK_SIZE:
                            continue  # Skip very small chunks
                        
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
            # Save chunks to JSON
            output_file = pdf_file.replace('.pdf', '_chunks.json')
            output_path = os.path.join(OUTPUT_DIR, output_file)
            
            with open(output_path, 'w') as f:
                json.dump(chunks, f, indent=2)
            
            print(f"✓ Created {len(chunks)} chunks → {output_path}")
            total_chunks += len(chunks)
            total_files += 1
        else:
            print(f"✗ No chunks created for {pdf_file}")
    
    print(f"\n=== Chunking Complete ===")
    print(f"Files processed: {total_files}")
    print(f"Total chunks: {total_chunks}")
    print(f"Average chunks per file: {total_chunks/total_files if total_files > 0 else 0:.1f}")

def chunk_document(report_data: dict) -> list:
    """
    Chunk an already-loaded report JSON (audited) into chunks.
    Returns list of dicts with chunk metadata.
    """
    chunks = []
    company = report_data.get('company', 'Unknown Company')
    year = report_data.get('year', 0)
    
    # Loop through pages or sections
    pages = report_data.get('pages', []) or report_data.get('page_text', [])
    
    if not pages and 'content' in report_data:
        # fallback if full text is in 'content'
        pages = [{'text': report_data['content']}]
    
    for page_num, page in enumerate(pages, 1):
        text = page.get('text', '') if isinstance(page, dict) else str(page)
        text = clean_text(text)
        page_chunks = create_semantic_chunks(text)
        
        for idx, chunk_text in enumerate(page_chunks):
            if len(chunk_text) < 100:
                continue  # skip tiny chunks
            chunks.append({
                'company': company,
                'year': year,
                'page': page_num,
                'chunk_index': idx,
                'content': chunk_text,
                'metadata': {
                    'source': report_data.get('source', 'Unknown'),
                    'chunk_size': len(chunk_text),
                    'total_page_chunks': len(page_chunks)
                }
            })
    
    return chunks


if __name__ == "__main__":
    process_all_pdfs()