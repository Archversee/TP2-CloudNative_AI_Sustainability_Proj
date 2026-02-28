import requests
import time
import json
from pathlib import Path

# Configuration
API_URL = "http://localhost:30800"  # Change to your API endpoint
TEST_PDFS = [
    {"path": "../..//Downloads/2025_SGX_Sustainability_Report.pdf", "company": "SGX", "year": 2025},
    {"path": "../../Downloads/PUB_ASR_2025.pdf", "company": "PUB", "year": 2025},
    {"path": "../../Downloads/FPG-Sustainability-Report-2024.pdf", "company": "Fairprice", "year": 2024},
    {"path": "../../Downloads/temasek-sustainability-report-2024.pdf", "company": "Temasek", "year": 2024}
]

def upload_pdf(pdf_path, company, year):
    """Upload PDF and track processing time."""
    
    print(f"\n{'='*60}")
    print(f"Testing: {company} ({year})")
    print(f"{'='*60}")
    
    # Upload PDF
    with open(pdf_path, 'rb') as f:
        files = {'file': (Path(pdf_path).name, f, 'application/pdf')}
        data = {'company': company, 'year': year}
        
        upload_start = time.time()
        response = requests.post(f"{API_URL}/api/upload", files=files, data=data)
        upload_time = time.time() - upload_start
        
        if response.status_code != 200:
            print(f"✗ Upload failed: {response.status_code}")
            return None
        
        result = response.json()
        doc_id = result['document_id']
        print(f"✓ Uploaded in {upload_time:.2f}s")
        print(f"  Document ID: {doc_id}")
    
    # Poll for completion
    start_time = time.time()
    stages = {
        'pdf_extraction': None,
        'ai_audit': None,
        'embeddings': None
    }
    
    while True:
        time.sleep(2)  # Poll every 2 seconds
        
        try:
            status_response = requests.get(f"{API_URL}/api/documents/{doc_id}")
            status_data = status_response.json()
            
            elapsed = time.time() - start_time
            
            if status_data['status'] == 'completed':
                total_time = time.time() - start_time
                print(f"\n✓ Processing completed in {total_time:.2f}s")
                
                # Get document details
                doc_data = status_data.get('data', {})
                
                return {
                    'document_id': doc_id,
                    'company': company,
                    'year': year,
                    'pages': count_pages(pdf_path),
                    'upload_time': upload_time,
                    'total_time': total_time,
                    'claims_analyzed': doc_data.get('claims_analyzed_count', 0),
                    'leaf_rating': doc_data.get('leaf_rating', 0),
                    'scope1_total': doc_data.get('scope1_total', 0),
                    'scope2_total': doc_data.get('scope2_total', 0),
                    'scope3_total': doc_data.get('scope3_total', 0),
                }
            
            # Print progress
            print(f"  Processing... {elapsed:.1f}s elapsed", end='\r')
            
            if elapsed > 300:  # 5 minute timeout
                print(f"\n✗ Timeout after {elapsed:.1f}s")
                return None
                
        except Exception as e:
            print(f"\n✗ Error checking status: {e}")
            return None

def count_pages(pdf_path):
    """Count pages in PDF."""
    try:
        import PyPDF2
        with open(pdf_path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            return len(reader.pages)
    except:
        return None

def analyze_results(results):
    """Analyze and display performance metrics."""
    
    if not results:
        print("\nNo results to analyze")
        return
    
    print("\n" + "="*80)
    print("THROUGHPUT ANALYSIS")
    print("="*80)
    
    # Calculate statistics
    total_times = [r['total_time'] for r in results if r]
    pages = [r['pages'] for r in results if r and r['pages']]
    
    if total_times:
        print(f"\nProcessing Time Statistics:")
        print(f"  Mean:   {sum(total_times)/len(total_times):.2f}s")
        print(f"  Min:    {min(total_times):.2f}s")
        print(f"  Max:    {max(total_times):.2f}s")
        print(f"  Median: {sorted(total_times)[len(total_times)//2]:.2f}s")
    
    if pages and total_times:
        time_per_page = [t/p for t, p in zip(total_times, pages) if p > 0]
        if time_per_page:
            print(f"\nPer-Page Processing:")
            print(f"  Mean:   {sum(time_per_page)/len(time_per_page):.2f}s/page")
    
    # Detailed table
    print("\n" + "-"*80)
    print(f"{'Company':<20} {'Pages':>6} {'Time (s)':>10} {'s/page':>8} {'Claims':>7} {'Rating':>7}")
    print("-"*80)
    
    for r in results:
        if r:
            time_per_page = r['total_time'] / r['pages'] if r['pages'] else 0
            print(f"{r['company']:<20} {r['pages']:>6} {r['total_time']:>10.2f} "
                  f"{time_per_page:>8.2f} {r['claims_analyzed']:>7} {r['leaf_rating']:>7}/5")
    
    print("-"*80)
    
    # Save results to JSON
    with open('throughput_results.json', 'w') as f:
        json.dump(results, f, indent=2)
    print("\n✓ Results saved to throughput_results.json")

def main():
    """Run throughput evaluation."""
    
    print("="*80)
    print("ECOEYE THROUGHPUT EVALUATION")
    print("="*80)
    print(f"\nTesting {len(TEST_PDFS)} documents...")
    print(f"API Endpoint: {API_URL}")
    
    results = []
    
    for test_pdf in TEST_PDFS:
        result = upload_pdf(
            test_pdf['path'],
            test_pdf['company'],
            test_pdf['year']
        )
        results.append(result)
        
        # Brief pause between uploads
        time.sleep(3)
    
    # Analyze results
    analyze_results([r for r in results if r])
    
    print("\n" + "="*80)
    print("EVALUATION COMPLETE")
    print("="*80)

if __name__ == "__main__":
    main()