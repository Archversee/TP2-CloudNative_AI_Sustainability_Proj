'use client'

import { useState, useEffect } from 'react'
import { Loader2, TrendingUp, TrendingDown, Leaf, ExternalLink } from 'lucide-react'
import axios from 'axios'
import Link from 'next/link'

interface Company {
  company: string
  year: number
  leaf_rating: number | null
  scope1_total: number | null
  scope2_total: number | null
}

export function CompanyList() {
  const [companies, setCompanies] = useState<Company[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    fetchCompanies()
  }, [])

  const fetchCompanies = async () => {
    try {
      const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      const response = await axios.get(`${API_URL}/api/companies`)
      setCompanies(response.data.companies || [])
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load companies')
    } finally {
      setLoading(false)
    }
  }

  const getLeafRatingColor = (rating: number | null) => {
    if (!rating) return 'text-gray-400'
    if (rating >= 4) return 'text-green-600'
    if (rating >= 3) return 'text-yellow-600'
    return 'text-red-600'
  }

  const renderLeaves = (rating: number | null) => {
    if (!rating) return <span className="text-gray-400">N/A</span>
    
    return (
      <div className="flex items-center gap-1">
        {[...Array(5)].map((_, i) => (
          <Leaf
            key={i}
            className={`w-5 h-5 ${
              i < rating ? getLeafRatingColor(rating) : 'text-gray-200'
            }`}
            fill={i < rating ? 'currentColor' : 'none'}
          />
        ))}
        <span className="ml-2 font-medium">{rating}/5</span>
      </div>
    )
  }

  if (loading) {
    return (
      <div className="card flex items-center justify-center py-12">
        <Loader2 className="w-8 h-8 animate-spin text-primary-600" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="card border-red-200 bg-red-50">
        <p className="text-red-600">{error}</p>
      </div>
    )
  }

  if (companies.length === 0) {
    return (
      <div className="card text-center py-12">
        <p className="text-gray-600 mb-4">No companies analyzed yet</p>
        <p className="text-sm text-gray-500">Upload a sustainability report to get started!</p>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="card">
        <h2 className="text-2xl font-bold text-gray-900 mb-4">📊 Analyzed Companies</h2>
        <p className="text-gray-600 mb-6">
          Browse {companies.length} company report{companies.length !== 1 ? 's' : ''} with AI-generated sustainability scores
        </p>

        <div className="grid gap-4">
          {companies.map((company, idx) => (
            <div
              key={`${company.company}-${company.year}-${idx}`}
              className="border border-gray-200 rounded-lg p-4 hover:border-primary-500 transition-colors"
            >
              <div className="flex items-start justify-between mb-3">
                <div>
                  <h3 className="text-lg font-semibold text-gray-900">{company.company}</h3>
                  <p className="text-sm text-gray-500">Year: {company.year}</p>
                </div>
                
                <Link
                  href={`/company/${encodeURIComponent(company.company)}?year=${company.year}`}
                  className="text-primary-600 hover:text-primary-700 flex items-center gap-1"
                >
                  Details
                  <ExternalLink className="w-4 h-4" />
                </Link>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {/* Leaf Rating */}
                <div>
                  <p className="text-xs text-gray-500 mb-1">Sustainability Score</p>
                  {renderLeaves(company.leaf_rating)}
                </div>

                {/* Scope 1 Emissions */}
                <div>
                  <p className="text-xs text-gray-500 mb-1">Scope 1 Emissions</p>
                  <div className="flex items-center gap-2">
                    <TrendingUp className="w-4 h-4 text-orange-500" />
                    <span className="font-medium">
                      {company.scope1_total
                        ? `${company.scope1_total.toLocaleString()} tCO₂e`
                        : 'N/A'}
                    </span>
                  </div>
                </div>

                {/* Scope 2 Emissions */}
                <div>
                  <p className="text-xs text-gray-500 mb-1">Scope 2 Emissions</p>
                  <div className="flex items-center gap-2">
                    <TrendingDown className="w-4 h-4 text-blue-500" />
                    <span className="font-medium">
                      {company.scope2_total
                        ? `${company.scope2_total.toLocaleString()} tCO₂e`
                        : 'N/A'}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
