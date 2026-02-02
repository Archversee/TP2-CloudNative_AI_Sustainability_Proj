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
    
    print(f"\n{'='*60}")
    print(f"🔮 Generating Embeddings: {company} ({year})")
    print(f"   Document ID: {doc_id}")
    print(f"   Source: {audit_path}")
    print(f"{'='*60}\n")
    
    try:
        # Load audited JSON
        print(f"📄 Loading audit data from: {audit_path}")
        with open(audit_path, 'r') as f:
            data = json.load(f)
        
        print(f"✓ Loaded data:")
        print(f"   Company: {data.get('company', 'N/A')}")
        print(f"   Year: {data.get('year', 'N/A')}")
        print(f"   Claims: {len(data.get('claims', []))}")
        
        # Chunk the document
        print(f"\n✂️  Chunking document...")
        chunks = chunk_document(data)
        
        if not chunks:
            print(f"⚠️  Warning: No chunks created from document")
            print(f"   This might be because chunk_document() expects different data structure")
            print(f"   Data keys available: {list(data.keys())}")
            return False
        
        print(f"✓ Created {len(chunks)} chunks")
        
        # Show sample chunk
        if chunks:
            print(f"\n📋 Sample chunk:")
            print(f"   Company: {chunks[0].get('company')}")
            print(f"   Year: {chunks[0].get('year')}")
            print(f"   Page: {chunks[0].get('page')}")
            print(f"   Content preview: {chunks[0].get('content', '')[:100]}...")
        
        # Generate and store embeddings
        print(f"\n🧠 Generating and storing embeddings...")
        result = generate_embeddings(chunks, doc_id)
        
        print(f"\n✓ Embeddings task completed!")
        print(f"  Successful: {result.get('successful', 0)}")
        print(f"  Failed: {result.get('failed', 0)}")
        
        return result.get('successful', 0) > 0
    
    except FileNotFoundError as e:
        print(f"\n✗ File not found: {audit_path}")
        print(f"   Error: {e}")
        return False
    
    except json.JSONDecodeError as e:
        print(f"\n✗ Invalid JSON in {audit_path}")
        print(f"   Error: {e}")
        return False
    
    except Exception as e:
        print(f"\n✗ Error generating embeddings for {doc_id}: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Worker main loop."""
    print("\n" + "="*60)
    print("EMBEDDINGS WORKER")
    print("="*60)
    print(f"Working directory: {os.getcwd()}")
    print(f"Data directory: {'/data' if os.path.exists('/data') else 'NOT FOUND'}")
    print("="*60)
    print("\nUsing:")
    print("  - chunker.py: chunk_document()")
    print("  - embedder.py: generate_embeddings()")
    print("="*60)
    
    # Check if data directories exist
    os.makedirs("/data/chunks", exist_ok=True)
    os.makedirs("/data/processed_json", exist_ok=True)
    
    print("\n⏳ Waiting for tasks on 'embeddings' queue...\n")
    
    while True:
        try:
            task = dequeue_task("embeddings", timeout=5)
            
            if task:
                success = process_task(task)
                
                if success:
                    print(f"\n{'='*60}")
                    print(f"✅ Embeddings stored successfully")
                    print(f"{'='*60}\n")
                else:
                    print(f"\n{'='*60}")
                    print(f"❌ Embeddings generation failed")
                    print(f"{'='*60}\n")
                
        except KeyboardInterrupt:
            print("\n\n👋 Shutting down worker...")
            break
        except Exception as e:
            print(f"\n⚠️  Worker error: {e}")
            import traceback
            traceback.print_exc()
            time.sleep(5)

if __name__ == "__main__":
    main()