"""
Performance Evaluation: Retrieval Quality
Measures Precision@K, Recall@K, and MRR for semantic search
"""
import requests
import json
from typing import List, Dict

# Configuration
API_URL = "http://localhost:30800"

# Test queries with known relevant pages/companies
# Format: {query, expected_company, expected_pages, category}
TEST_QUERIES = [
    # Numeric queries - asking for specific emission values
    {
        "query": "What are Fairprice's Scope 1 emissions?",
        "company": "Fairprice",
        "year": 2024,
        "expected_pages": [16, 40],  # Pages where Scope 1 data appears
        "category": "numeric"
    },
    {
        "query": "What are PUB's Scope 2 emissions?",
        "company": "Pub",
        "year": 2025,
        "expected_pages": [48, 49],
        "category": "numeric"
    },
    
    # Target queries - asking about goals/commitments
    {
        "query": "When does Fairprice target net zero?",
        "company": "Fairprice",
        "year": 2024,
        "expected_pages": [4, 6, 12],
        "category": "target"
    },
    {
        "query": "What is SGX's net zero target year?",
        "company": "Sgx",
        "year": 2025,
        "expected_pages": [21, 23],
        "category": "target"
    },
    
    # Comparative queries - comparing metrics
    {
        "query": "Compare renewable energy usage",
        "company": None,  # Multi-company
        "year": None,
        "expected_pages": None,  # Just check if results span multiple companies
        "category": "comparative"
    },
    
]

def search_query(query: str, company: str = None, year: int = None, 
                threshold: float = 0.4, limit: int = 5) -> Dict:
    """Execute search query and return results."""
    
    params = {
        'q': query,
        'threshold': threshold,
        'limit': limit
    }
    
    if company:
        params['company'] = company
    if year:
        params['year'] = year
    
    try:
        response = requests.get(f"{API_URL}/api/search", params=params)
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"✗ Search failed: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"✗ Error: {e}")
        return None

def calculate_precision_at_k(retrieved_pages: List[int], 
                            expected_pages: List[int], 
                            k: int = 5) -> float:
    """Calculate Precision@K."""
    
    if not retrieved_pages or not expected_pages:
        return 0.0
    
    top_k = retrieved_pages[:k]
    relevant_in_top_k = sum(1 for page in top_k if page in expected_pages)
    
    return relevant_in_top_k / len(top_k) if top_k else 0.0

def calculate_recall_at_k(retrieved_pages: List[int], 
                         expected_pages: List[int], 
                         k: int = 5) -> float:
    """Calculate Recall@K."""
    
    if not expected_pages:
        return 0.0
    
    top_k = retrieved_pages[:k]
    relevant_in_top_k = sum(1 for page in top_k if page in expected_pages)
    
    return relevant_in_top_k / len(expected_pages)

def calculate_mrr(retrieved_pages: List[int], 
                 expected_pages: List[int]) -> float:
    """Calculate Mean Reciprocal Rank."""
    
    for rank, page in enumerate(retrieved_pages, 1):
        if page in expected_pages:
            return 1.0 / rank
    
    return 0.0

def evaluate_query(test_case: Dict, threshold: float = 0.4) -> Dict:
    """Evaluate a single query."""
    
    query = test_case['query']
    company = test_case.get('company')
    year = test_case.get('year')
    expected_pages = test_case.get('expected_pages', [])
    category = test_case.get('category', 'general')
    
    print(f"\n{'='*60}")
    print(f"Query: {query}")
    print(f"Category: {category}")
    if company:
        print(f"Filter: {company} ({year if year else 'all years'})")
    print(f"{'='*60}")
    
    # Execute search
    result = search_query(query, company, year, threshold=threshold, limit=5)
    
    if not result:
        return None
    
    # Extract retrieved page numbers
    retrieved_pages = []
    if 'citations' in result:
        retrieved_pages = [cite['page'] for cite in result['citations']]
    
    print(f"\nRetrieved pages: {retrieved_pages}")
    print(f"Expected pages: {expected_pages}")
    
    # Calculate metrics
    if expected_pages:
        precision = calculate_precision_at_k(retrieved_pages, expected_pages, k=5)
        recall = calculate_recall_at_k(retrieved_pages, expected_pages, k=5)
        mrr = calculate_mrr(retrieved_pages, expected_pages)
        
        print(f"\nMetrics:")
        print(f"  Precision@5: {precision:.2%}")
        print(f"  Recall@5:    {recall:.2%}")
        print(f"  MRR:         {mrr:.3f}")
        
        return {
            'query': query,
            'category': category,
            'threshold': threshold,
            'num_results': len(retrieved_pages),
            'precision': precision,
            'recall': recall,
            'mrr': mrr,
            'retrieved_pages': retrieved_pages,
            'expected_pages': expected_pages,
            'answer': result.get('answer', ''),
            'confidence': result.get('confidence', '')
        }
    else:
        # For comparative queries, just check diversity
        companies_found = set()
        if 'citations' in result:
            companies_found = set(cite['company'] for cite in result['citations'])
        
        print(f"\nCompanies in results: {companies_found}")
        
        return {
            'query': query,
            'category': category,
            'threshold': threshold,
            'num_results': len(retrieved_pages),
            'companies_found': len(companies_found),
            'answer': result.get('answer', '')
        }

def test_threshold_sensitivity(test_cases: List[Dict]):
    """Test different similarity thresholds."""
    
    print("\n" + "="*80)
    print("THRESHOLD SENSITIVITY ANALYSIS")
    print("="*80)
    
    thresholds = [0.3, 0.4, 0.5, 0.6]
    
    print(f"\n{'Threshold':<12} {'Precision@5':<14} {'Recall@5':<12} {'MRR':<8} {'Avg Results':<12}")
    print("-"*70)
    
    threshold_results = {}
    
    for threshold in thresholds:
        results = []
        
        for test_case in test_cases:
            if test_case.get('expected_pages'):  # Only for queries with expected pages
                result = evaluate_query(test_case, threshold=threshold)
                if result:
                    results.append(result)
        
        if results:
            avg_precision = sum(r['precision'] for r in results) / len(results)
            avg_recall = sum(r['recall'] for r in results) / len(results)
            avg_mrr = sum(r['mrr'] for r in results) / len(results)
            avg_num_results = sum(r['num_results'] for r in results) / len(results)
            
            threshold_results[threshold] = {
                'precision': avg_precision,
                'recall': avg_recall,
                'mrr': avg_mrr,
                'avg_results': avg_num_results
            }
            
            print(f"{threshold:<12.1f} {avg_precision:<14.2%} {avg_recall:<12.2%} "
                  f"{avg_mrr:<8.3f} {avg_num_results:<12.1f}")
    
    print("-"*70)
    
    return threshold_results

def analyze_by_category(results: List[Dict]):
    """Analyze performance by query category."""
    
    print("\n" + "="*80)
    print("CATEGORY ANALYSIS")
    print("="*80)
    
    categories = {}
    
    for result in results:
        if result and 'category' in result and 'precision' in result:
            category = result['category']
            if category not in categories:
                categories[category] = []
            categories[category].append(result)
    
    print(f"\n{'Category':<15} {'Count':<8} {'Precision@5':<14} {'Recall@5':<12} {'MRR':<8}")
    print("-"*70)
    
    for category, cat_results in categories.items():
        avg_precision = sum(r['precision'] for r in cat_results) / len(cat_results)
        avg_recall = sum(r['recall'] for r in cat_results) / len(cat_results)
        avg_mrr = sum(r['mrr'] for r in cat_results) / len(cat_results)
        
        print(f"{category:<15} {len(cat_results):<8} {avg_precision:<14.2%} "
              f"{avg_recall:<12.2%} {avg_mrr:<8.3f}")
    
    print("-"*70)

def main():
    """Run retrieval quality evaluation."""
    
    print("="*80)
    print("ECOEYE RETRIEVAL QUALITY EVALUATION")
    print("="*80)
    print(f"\nTesting {len(TEST_QUERIES)} queries...")
    print(f"API Endpoint: {API_URL}")
    
    # Evaluate at default threshold (0.4)
    print("\n" + "="*80)
    print("EVALUATING AT DEFAULT THRESHOLD (0.4)")
    print("="*80)
    
    results = []
    for test_case in TEST_QUERIES:
        result = evaluate_query(test_case, threshold=0.4)
        results.append(result)
    
    # Overall statistics at threshold 0.4
    valid_results = [r for r in results if r and 'precision' in r]
    
    if valid_results:
        print("\n" + "="*80)
        print("OVERALL METRICS (Threshold = 0.4)")
        print("="*80)
        
        avg_precision = sum(r['precision'] for r in valid_results) / len(valid_results)
        avg_recall = sum(r['recall'] for r in valid_results) / len(valid_results)
        avg_mrr = sum(r['mrr'] for r in valid_results) / len(valid_results)
        avg_results = sum(r['num_results'] for r in valid_results) / len(valid_results)
        
        print(f"\nPrecision@5: {avg_precision:.2%}")
        print(f"Recall@5:    {avg_recall:.2%}")
        print(f"MRR:         {avg_mrr:.3f}")
        print(f"Avg Results: {avg_results:.1f}")
    
    # Category analysis
    analyze_by_category(results)
    
    # Threshold sensitivity
    threshold_results = test_threshold_sensitivity(TEST_QUERIES)
    
    # Save results
    output = {
        'default_threshold_results': results,
        'threshold_sensitivity': threshold_results
    }
    
    with open('retrieval_quality_results.json', 'w') as f:
        json.dump(output, f, indent=2)
    
    print("\n✓ Results saved to retrieval_quality_results.json")
    
    print("\n" + "="*80)
    print("EVALUATION COMPLETE")
    print("="*80)

if __name__ == "__main__":
    main()