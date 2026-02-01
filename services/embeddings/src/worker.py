import sys
sys.path.append('/app')

from shared.tasks import dequeue_task
import time
import json

from embedder import generate_embeddings 
from chunker import chunk_document

def process_task(task):
    """Process an embeddings task."""
    doc_id = task['id']
    audit_path = task['audit_path']
    
    print(f"🔮 Generating embeddings: {doc_id}")
    
    try:
        # Load audited JSON
        with open(audit_path, 'r') as f:
            data = json.load(f)
        
        # Chunk the document
        chunks = chunk_document(data)
        
        # Generate and store embeddings
        generate_embeddings(chunks, doc_id)
        
        print(f"✓ Embeddings stored: {doc_id}")
        
        return True
    
    except Exception as e:
        print(f"✗ Error generating embeddings {doc_id}: {e}")
        return False

def main():
    """Worker main loop."""
    print("Embeddings Worker starting...")
    print("Waiting for tasks on 'embeddings' queue...")
    
    while True:
        try:
            task = dequeue_task("embeddings", timeout=5)
            
            if task:
                process_task(task)
                
        except KeyboardInterrupt:
            print("\nShutting down worker...")
            break
        except Exception as e:
            print(f"Worker error: {e}")
            time.sleep(5)

if __name__ == "__main__":
    main()