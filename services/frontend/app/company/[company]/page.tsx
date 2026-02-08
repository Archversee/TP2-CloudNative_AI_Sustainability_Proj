'use client'

import { useState, useEffect } from 'react'
import { useParams, useSearchParams } from 'next/navigation'
import { Loader2, Leaf, TrendingUp, ArrowLeft, FileText } from 'lucide-react'
import axios from 'axios'
import Link from 'next/link'

interface CompanyData {
  company: string
  year: number
  leaf_rating: number | null
  ai_summary: string
  scope1_total: number | null
  scope2_total: number | null
  claims: any[]
  source: string
}

export default function CompanyPage() {
  const params = useParams()
  const searchParams = useSearchParams()
  const company = decodeURIComponent(params.company as string)
  const year = searchParams.get('year')
  
  const [data, setData] = useState<CompanyData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    fetchCompanyData()
  }, [company, year])

  const fetchCompanyData = async () => {
    try {
      const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      const url = year
        ? `${API_URL}/api/companies/${encodeURIComponent(company)}?year=${year}`
        : `${API_URL}/api/companies/${encodeURIComponent(company)}`
      
      const response = await axios.get(url)
      setData(response.data)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load company data')
    } finally {
      setLoading(false)
    }
  }

  const renderLeaves = (rating: number | null) => {
    if (!rating) return <span className="text-gray-400">N/A</span>
    
    const color = rating >= 4 ? 'text-green-600' : rating >= 3 ? 'text-yellow-600' : 'text-red-600'
    
    return (
      <div className="flex items-center gap-1">
        {[...Array(5)].map((_, i) => (
          <Leaf
            key={i}
            className={`w-6 h-6 ${i < rating ? color : 'text-gray-200'}`}
            fill={i < rating ? 'currentColor' : 'none'}
          />
        ))}
        <span className="ml-2 text-2xl font-bold">{rating}/5</span>
      </div>
    )
  }

  if (loading) {
    return (
      <div className="container mx-auto px-4 py-8">
        <div className="card flex items-center justify-center py-12">
          <Loader2 className="w-8 h-8 animate-spin text-primary-600" />
        </div>
      </div>
    )
  }

  if (error || !data) {
    return (
      <div className="container mx-auto px-4 py-8">
        <div className="card border-red-200 bg-red-50">
          <p className="text-red-600">{error || 'Company not found'}</p>
          <Link href="/" className="text-primary-600 hover:text-primary-700 mt-4 inline-block">
            ← Back to home
          </Link>
        </div>
      </div>
    )
  }

  return (
    <div className="container mx-auto px-4 py-8 max-w-4xl">
      {/* Back Button */}
      <Link href="/" className="text-primary-600 hover:text-primary-700 flex items-center gap-2 mb-6">
        <ArrowLeft className="w-4 h-4" />
        Back to home
      </Link>

      {/* Header */}
      <div className="card mb-6">
        <div className="flex items-start justify-between mb-4">
          <div>
            <h1 className="text-3xl font-bold text-gray-900 mb-2">{data.company}</h1>
            <p className="text-gray-600">Report Year: {data.year}</p>
          </div>
          <div className="text-right">
            <p className="text-sm text-gray-500 mb-2">Sustainability Score</p>
            {renderLeaves(data.leaf_rating)}
          </div>
        </div>
      </div>

      {/* AI Summary */}
      {data.ai_summary && (
        <div className="card mb-6">
          <h2 className="text-xl font-bold text-gray-900 mb-3">🤖 AI Analysis</h2>
          <p className="text-gray-700 leading-relaxed whitespace-pre-wrap">
            {data.ai_summary}
          </p>
        </div>
      )}

      {/* Emissions */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
        <div className="card">
          <h3 className="text-lg font-semibold text-gray-900 mb-2">Scope 1 Emissions</h3>
          <div className="flex items-center gap-2">
            <TrendingUp className="w-5 h-5 text-orange-500" />
            <span className="text-2xl font-bold text-gray-900">
              {data.scope1_total?.toLocaleString() || 'N/A'}
            </span>
            {data.scope1_total && <span className="text-gray-500">tCO₂e</span>}
          </div>
        </div>

        <div className="card">
          <h3 className="text-lg font-semibold text-gray-900 mb-2">Scope 2 Emissions</h3>
          <div className="flex items-center gap-2">
            <TrendingUp className="w-5 h-5 text-blue-500" />
            <span className="text-2xl font-bold text-gray-900">
              {data.scope2_total?.toLocaleString() || 'N/A'}
            </span>
            {data.scope2_total && <span className="text-gray-500">tCO₂e</span>}
          </div>
        </div>
      </div>

      {/* Claims */}
      {data.claims && data.claims.length > 0 && (
        <div className="card">
          <h2 className="text-xl font-bold text-gray-900 mb-4">📋 Sustainability Claims</h2>
          <div className="space-y-4">
            {data.claims.map((claim, idx) => (
              <div key={idx} className="border-l-4 border-primary-500 pl-4 py-2">
                <div className="flex items-start justify-between mb-2">
                  <p className="font-medium text-gray-900">{claim.claim}</p>
                  <span className="text-sm text-gray-500">Page {claim.page}</span>
                </div>
                
                {claim.target_year && (
                  <p className="text-sm text-gray-600 mb-1">
                    Target Year: {claim.target_year}
                  </p>
                )}
                
                {claim.context && (
                  <p className="text-sm text-gray-600 italic">
                    "{claim.context.substring(0, 150)}..."
                  </p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
