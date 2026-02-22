"""
Embeddings Worker - Integrates chunker.py and embedder.py for RAG
"""
import sys
import os
import json
import time

sys.path.append('/app')

from shared.tasks import dequeue_task
from chunker import chunk_document
from embedder import generate_embeddings

def process_task(task):
    """Process an embeddings task."""
    doc_id = task.get('document_id', task.get('id'))  # Handle both keys
    audit_path = task.get('audit_path')
    company = task.get('company', 'Unknown')
    year = task.get('year', 2024)
    
    print(f" Generating Embeddings: {company} ({year})")
    
    try:
        # Load audited JSON
        with open(audit_path, 'r') as f:
            data = json.load(f)
        
        print(f" Loaded data:")
        print(f"   Company: {data.get('company', 'N/A')}")
        print(f"   Year: {data.get('year', 'N/A')}")
        print(f"   Claims: {len(data.get('claims', []))}")
        
        # Chunk the document
        print(f"\n Chunking document...")
        chunks = chunk_document(data)
        
        if not chunks:
            print(f"  Warning: No chunks created from document")
            return False
        
        print(f" Created {len(chunks)} chunks")
        
        # Generate and store embeddings
        print(f"\n Generating and storing embeddings...")
        result = generate_embeddings(chunks, doc_id)
        
        print(f"\n Embeddings task completed!")
        print(f"  Successful: {result.get('successful', 0)}")
        print(f"  Failed: {result.get('failed', 0)}")
        
        return result.get('successful', 0) > 0
    
    except FileNotFoundError as e:
        print(f"\n File not found: {audit_path}")
        print(f"   Error: {e}")
        return False
    
    except json.JSONDecodeError as e:
        print(f"\n Invalid JSON in {audit_path}")
        print(f"   Error: {e}")
        return False
    
    except Exception as e:
        print(f"\n Error generating embeddings for {doc_id}: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Worker main loop."""
    print("EMBEDDINGS WORKER")
    print(f"Working directory: {os.getcwd()}")
    print(f"Data directory: {'/data' if os.path.exists('/data') else 'NOT FOUND'}")
    
    # Check if data directories exist
    os.makedirs("/data/chunks", exist_ok=True)
    os.makedirs("/data/processed_json", exist_ok=True)
    
    print("\n Waiting for tasks on 'embeddings' queue...\n")
    
    while True:
        try:
            task = dequeue_task("embeddings", timeout=5)
            
            if task:
                success = process_task(task)
                
                if success:
                    print(f"\n{'='*60}")
                    print(f" Embeddings stored successfully")
                    print(f"{'='*60}\n")
                else:
                    print(f"\n{'='*60}")
                    print(f" Embeddings generation failed")
                    print(f"{'='*60}\n")
                
        except KeyboardInterrupt:
            print("\n\n Shutting down worker...")
            break
        except Exception as e:
            print(f"\n  Worker error: {e}")
            import traceback
            traceback.print_exc()
            time.sleep(5)

if __name__ == "__main__":
    main()