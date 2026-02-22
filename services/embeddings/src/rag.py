"""
RAG Query Service for EcoLens Phase 3
Performs semantic search and generates AI-powered answers with citations
"""

import os
from typing import List, Dict
from dotenv import load_dotenv
import requests
from supabase import create_client, Client

load_dotenv()

# Configuration
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Initialize Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def generate_query_embedding(query: str) -> List[float]:
    """Generate embedding for user query using local model."""
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer('all-MiniLM-L6-v2')
    return model.encode(query, convert_to_numpy=True).tolist()


def semantic_search(
    query: str,
    company: str = None,
    year: int = None,
    match_threshold: float = 0.3,
    match_count: int = 5
) -> List[Dict]:
    """
    Perform semantic search on document chunks.
    
    Args:
        query: User's question
        company: Optional company filter
        year: Optional year filter
        match_threshold: Minimum similarity score (0-1)
        match_count: Number of results to return
    
    Returns:
        List of matching chunks with metadata
    """
    # Generate query embedding
    query_embedding = generate_query_embedding(query)
    
    if query_embedding is None:
        return []
    
    try:
        # Call Supabase RPC function for vector search
        result = supabase.rpc(
            'search_documents',
            {
                'query_embedding': query_embedding,
                'match_threshold': match_threshold,
                'match_count': match_count,
                'filter_company': company,
                'filter_year': year
            }
        ).execute()
        
        return result.data
    
    except Exception as e:
        print(f"Error during semantic search: {e}")
        return []

def generate_rag_response(query: str, context_chunks: List[Dict]) -> Dict:
    """
    Generate AI response using retrieved context chunks.
    
    Args:
        query: User's question
        context_chunks: Relevant document chunks from vector search
    
    Returns:
        Dict with answer and citations
    """
    if not context_chunks:
        return {
            "answer": "I couldn't find relevant information to answer your question.",
            "citations": [],
            "confidence": "low"
        }
    
    # Build context from chunks
    context_text = "\n\n".join([
        f"[Source: {chunk['company']} {chunk['year']} Report, Page {chunk['page']}]\n{chunk['content']}"
        for chunk in context_chunks
    ])
    
    # Create prompt for Gemini
    prompt = f"""You are an ESG sustainability expert analyzing corporate sustainability reports.

USER QUESTION:
{query}

RELEVANT CONTEXT FROM REPORTS:
{context_text}

INSTRUCTIONS:
1. Answer the question based ONLY on the provided context
2. Include specific citations with company name, year, and page number
3. If the context doesn't fully answer the question, say so
4. Be precise and factual
5. Return your response in JSON format:

{{
  "answer": "Your detailed answer here",
  "citations": [
    {{"company": "...", "year": 2024, "page": 5, "quote": "relevant quote"}}
  ],
  "confidence": "high|medium|low"
}}

Respond with ONLY the JSON, no markdown or extra text."""

    url = f"https://generativelanguage.googleapis.com/v1/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"
    
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.2,
            "maxOutputTokens": 2000
        }
    }
    
    try:
        response = requests.post(url, json=payload, timeout=30)
        response.raise_for_status()
        
        raw_text = response.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
        
        # Parse JSON response
        import json
        import re
        
        # Remove markdown code blocks if present
        clean_text = re.sub(r'```json\s*|\s*```', '', raw_text)
        result = json.loads(clean_text)
        
        return result
    
    except Exception as e:
        print(f"Error generating RAG response: {e}")
        return {
            "answer": "Sorry, I encountered an error generating the response.",
            "citations": [],
            "confidence": "low",
            "error": str(e)
        }

def query_ecolens(
    question: str,
    company: str = None,
    year: int = None
) -> Dict:
    """
    Main RAG query function.
    
    Args:
        question: User's question about sustainability
        company: Optional company filter
        year: Optional year filter
    
    Returns:
        Dict with answer, citations, and metadata
    """
    print(f"\n🔍 Question: {question}")
    if company:
        print(f"   Company filter: {company}")
    if year:
        print(f"   Year filter: {year}")
    
    # Step 1: Semantic search
    print("\n📊 Searching documents...")
    chunks = semantic_search(
        query=question,
        company=company,
        year=year,
        match_threshold=0.7,
        match_count=5
    )
    
    if not chunks:
        return {
            "question": question,
            "answer": "No relevant information found in the database.",
            "citations": [],
            "confidence": "none"
        }
    
    print(f"   Found {len(chunks)} relevant chunks")
    for chunk in chunks:
        print(f"   - {chunk['company']} ({chunk['year']}), Page {chunk['page']}, Similarity: {chunk['similarity']:.2f}")
    
    # Step 2: Generate answer with RAG
    print("\n🤖 Generating answer...")
    response = generate_rag_response(question, chunks)
    
    # Add metadata
    response['question'] = question
    response['num_sources'] = len(chunks)
    
    return response

def get_company_overview(company: str, year: int = None) -> Dict:
    """
    Get company's leaf rating and summary.
    
    Args:
        company: Company name
        year: Optional year (defaults to most recent)
    
    Returns:
        Dict with company metadata
    """
    try:
        query = supabase.table('company_reports').select('*').eq('company', company)
        
        if year:
            query = query.eq('year', year)
        else:
            query = query.order('year', desc=True).limit(1)
        
        result = query.execute()
        
        if result.data:
            return result.data[0]
        else:
            return None
    
    except Exception as e:
        print(f"Error fetching company overview: {e}")
        return None

# Example usage
if __name__ == "__main__":
    # Example 1: General query
    result = query_ecolens(
        "What are CLCT's Scope 1 and Scope 2 emissions?",
        company="CLCT",
        year=2024
    )
    
    print("\n" + "="*60)
    print("ANSWER:")
    print("="*60)
    print(result['answer'])
    print("\n" + "="*60)
    print("CITATIONS:")
    print("="*60)
    for citation in result.get('citations', []):
        print(f"  📄 {citation.get('company')} ({citation.get('year')}), Page {citation.get('page')}")
        print(f"     \"{citation.get('quote', '')}\"")
        print()
    
    print(f"Confidence: {result.get('confidence', 'unknown')}")
    
    # Example 2: Get company overview
    print("\n" + "="*60)
    overview = get_company_overview("CLCT", 2024)
    if overview:
        print(f"\n🍃 CLCT 2024 Overview:")
        print(f"   Leaf Rating: {overview.get('leaf_rating', 'N/A')}/5")
        print(f"   Scope 1: {overview.get('scope1_total', 0):.1f} tCO2e")
        print(f"   Scope 2: {overview.get('scope2_total', 0):.1f} tCO2e")
        print(f"   Summary: {overview.get('ai_summary', 'N/A')}")