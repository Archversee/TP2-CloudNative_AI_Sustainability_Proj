'use client'

import { useState } from 'react'
import { Search, Loader2, ExternalLink } from 'lucide-react'
import axios from 'axios'

interface Citation {
  company: string
  year: number
  page: number
  quote: string
}

interface SearchResponse {
  question: string
  answer: string
  citations: Citation[]
  confidence: string
  num_sources: number
}

export function SearchSection() {
  const [query, setQuery] = useState('')
  const [company, setCompany] = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<SearchResponse | null>(null)
  const [error, setError] = useState('')

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (!query.trim()) return

    setLoading(true)
    setError('')
    setResult(null)

    try {
      const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      
      const response = await axios.post<SearchResponse>(`${API_URL}/api/search`, {
        query: query.trim(),
        company: company.trim() || null,
        match_threshold: 0.4,
        match_count: 5
      })

      setResult(response.data)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Search failed. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  const getConfidenceColor = (confidence: string) => {
    switch (confidence.toLowerCase()) {
      case 'high': return 'text-green-600 bg-green-50'
      case 'medium': return 'text-yellow-600 bg-yellow-50'
      case 'low': return 'text-red-600 bg-red-50'
      default: return 'text-gray-600 bg-gray-50'
    }
  }

  return (
    <div className="space-y-6">
      {/* Search Form */}
      <div className="card">
        <h2 className="text-2xl font-bold text-gray-900 mb-4">🔍 Semantic Search</h2>
        <p className="text-gray-600 mb-6">
          Ask questions about sustainability reports and get AI-powered answers with citations
        </p>

        <form onSubmit={handleSearch} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Your Question
            </label>
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="e.g., What are the company's net zero targets?"
              className="input w-full"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Filter by Company (Optional)
            </label>
            <input
              type="text"
              value={company}
              onChange={(e) => setCompany(e.target.value)}
              placeholder="e.g., CLCT"
              className="input w-full"
            />
          </div>

          <button
            type="submit"
            disabled={loading || !query.trim()}
            className="btn-primary w-full flex items-center justify-center gap-2"
          >
            {loading ? (
              <>
                <Loader2 className="w-5 h-5 animate-spin" />
                Searching...
              </>
            ) : (
              <>
                <Search className="w-5 h-5" />
                Search
              </>
            )}
          </button>
        </form>
      </div>

      {/* Error */}
      {error && (
        <div className="card border-red-200 bg-red-50">
          <p className="text-red-600">{error}</p>
        </div>
      )}

      {/* Results */}
      {result && (
        <div className="space-y-6">
          {/* Answer */}
          <div className="card">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-xl font-bold text-gray-900">Answer</h3>
              <span className={`px-3 py-1 rounded-full text-sm font-medium ${getConfidenceColor(result.confidence)}`}>
                {result.confidence} confidence
              </span>
            </div>
            
            <p className="text-gray-700 leading-relaxed whitespace-pre-wrap">
              {result.answer}
            </p>

            <div className="mt-4 text-sm text-gray-500">
              Based on {result.num_sources} source{result.num_sources !== 1 ? 's' : ''}
            </div>
          </div>

          {/* Citations */}
          {result.citations.length > 0 && (
            <div className="card">
              <h3 className="text-xl font-bold text-gray-900 mb-4">📚 Citations</h3>
              
              <div className="space-y-3">
                {result.citations.map((citation, idx) => (
                  <div key={idx} className="border-l-4 border-primary-500 pl-4 py-2">
                    <div className="flex items-center gap-2 text-sm font-medium text-gray-900 mb-1">
                      <ExternalLink className="w-4 h-4" />
                      {citation.company} ({citation.year}) - Page {citation.page}
                    </div>
                    <p className="text-gray-600 italic">"{citation.quote}"</p>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Example Queries */}
      <div className="card bg-gray-50">
        <h4 className="font-semibold text-gray-900 mb-3">💡 Example Queries:</h4>
        <div className="flex flex-wrap gap-2">
          {[
            'What are the net zero targets?',
            'What renewable energy initiatives are mentioned?',
            'What are the Scope 1 and Scope 2 emissions?',
            'How is the company reducing carbon emissions?'
          ].map((example) => (
            <button
              key={example}
              onClick={() => setQuery(example)}
              className="px-3 py-1 bg-white border border-gray-300 rounded-full text-sm text-gray-900 hover:bg-gray-100 transition-colors"
            >
              {example}
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}
