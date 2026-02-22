import os
import json
import time
from typing import List, Dict
from dotenv import load_dotenv
import requests
from supabase import create_client, Client

load_dotenv()

# Configuration
CHUNKS_DIR = "/data/chunks"
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY")

# Initialize Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def generate_embedding_local(text: str) -> List[float]:
    """
    Generate embedding using local sentence-transformers.
    Free alternative to OpenAI.
    """
    try:
        from sentence_transformers import SentenceTransformer
        
        # Load model
        model = SentenceTransformer('all-MiniLM-L6-v2')
        
        # Generate embedding (384 dimensions)
        embedding = model.encode(text, convert_to_numpy=True)
        return embedding.tolist()
    
    except ImportError:
        print("sentence-transformers not installed. Run: pip install sentence-transformers")
        return None

def store_chunk_in_supabase(chunk: Dict, embedding: List[float]) -> bool:
    """Store chunk with embedding in Supabase."""
    try:
        data = {
            "company": chunk['company'],
            "year": chunk['year'],
            "page": chunk['page'],
            "chunk_index": chunk['chunk_index'],
            "content": chunk['content'],
            "embedding": embedding,
            "metadata": chunk.get('metadata', {})
        }
        
        result = supabase.table('document_chunks').upsert(data).execute()
        return True
    
    except Exception as e:
        print(f"Error storing chunk in Supabase: {e}")
        return False

def process_chunks_file(chunks_file: str, use_local: bool = True):
    """Process a chunks JSON file and store embeddings."""
    print(f"\nProcessing {chunks_file}...")
    
    chunks_path = os.path.join(CHUNKS_DIR, chunks_file)
    
    with open(chunks_path, 'r') as f:
        chunks = json.load(f)
    
    successful = 0
    failed = 0
    
    for i, chunk in enumerate(chunks):
        # Generate embedding       
        embedding = generate_embedding_local(chunk['content'])
        
        if embedding is None:
            print(f"   Failed to generate embedding for chunk {i}")
            failed += 1
            continue
        
        # Store in Supabase
        if store_chunk_in_supabase(chunk, embedding):
            successful += 1
            if (i + 1) % 10 == 0:
                print(f"  Progress: {i+1}/{len(chunks)} chunks processed")
        else:
            failed += 1
        
        # Rate limiting - small delay between requests
        if not use_local:
            time.sleep(0.1)  # For API calls
    
    print(f"   Stored {successful} chunks, {failed} failed")
    return successful, failed

def process_all_chunks(use_local: bool = True):
    """Process all chunk files and generate embeddings."""
    if not os.path.exists(CHUNKS_DIR):
        print(f"Error: Chunks directory not found: {CHUNKS_DIR}")
        print("Please run text_chunker.py first!")
        return
    
    total_successful = 0
    total_failed = 0
    
    chunk_files = [f for f in os.listdir(CHUNKS_DIR) if f.endswith('_chunks.json')]
    
    print(f"Found {len(chunk_files)} chunk files to process")
    print(f"Using {'LOCAL' if use_local else 'OpenAI'} embeddings")
    
    for chunk_file in sorted(chunk_files):
        successful, failed = process_chunks_file(chunk_file, use_local)
        total_successful += successful
        total_failed += failed
    
    print(f"\n=== Embedding Complete ===")
    print(f"Total chunks stored: {total_successful}")
    print(f"Total failures: {total_failed}")

def store_report_metadata(processed_json_dir: str = "/data/processed_json"):
    """
    Store report metadata (from Phase 2) in company_reports table.
    This links the AI audit results with the vector embeddings.
    """
    print("\nStoring report metadata...")
    
    if not os.path.exists(processed_json_dir):
        print(f"Error: Processed JSON directory not found: {processed_json_dir}")
        return
    
    successful = 0
    
    for json_file in sorted(os.listdir(processed_json_dir)):
        if not json_file.endswith('.json'):
            continue
        
        json_path = os.path.join(processed_json_dir, json_file)
        
        with open(json_path, 'r') as f:
            report_data = json.load(f)
        
        try:
            ai_summary = report_data.get('ai_summary', {})
            
            # Calculate total emissions
            scope1_total = sum(
                m.get('value', 0) 
                for page in report_data.get('page_metrics', [])
                for m in page.get('scope1_emissions_tco2e', [])
            )
            
            scope2_total = sum(
                m.get('value', 0)
                for page in report_data.get('page_metrics', [])
                for m in page.get('scope2_emissions_tco2e', [])
            )
            
            data = {
                "company": report_data.get('company'),
                "year": report_data.get('year'),
                "source": report_data.get('source', 'Sustainability Report'),
                "leaf_rating": ai_summary.get('overall_score'), 
                "truth_score": ai_summary.get('overall_score'),
                "ai_summary": ai_summary.get('overall_summary', ''),
                "claims": report_data.get('claims', []),
                "scope1_total": scope1_total,
                "scope2_total": scope2_total,
                "processed_at": report_data.get('processed_at')
            }
            
            result = supabase.table('company_reports').upsert(data).execute()
            print(f"   Stored metadata for {data['company']} ({data['year']})")
            successful += 1
        
        except Exception as e:
            print(f"   Failed to store {json_file}: {e}")
    
    print(f"\nStored {successful} report metadata entries")

def generate_embeddings(chunks: List[Dict], doc_id: str, use_local: bool = True):
    """
    Generate embeddings for chunks produced by chunker
    and store them in Supabase.
    """
    print(f"Storing embeddings for {doc_id} ({len(chunks)} chunks)")

    successful = 0
    failed = 0

    for i, chunk in enumerate(chunks):
        if use_local:
            embedding = generate_embedding_local(chunk["content"])
        else:
            raise NotImplementedError("OpenAI embeddings not implemented")

        if embedding is None:
            failed += 1
            continue

        if store_chunk_in_supabase(chunk, embedding):
            successful += 1
        else:
            failed += 1

    print(f"Embeddings complete for {doc_id}: {successful} stored, {failed} failed")
    return {"successful": successful, "failed": failed}


if __name__ == "__main__":
    import sys
    
    # Process chunks and generate embeddings
    process_all_chunks(use_local=True)
    
    # Store report metadata
    store_report_metadata()