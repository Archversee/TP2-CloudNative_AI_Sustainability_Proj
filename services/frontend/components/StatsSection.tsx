'use client'

import { useState, useEffect } from 'react'
import { FileText, Database, Building2 } from 'lucide-react'
import axios from 'axios'

interface Stats {
  total_reports: number
  total_chunks: number
  unique_companies: number
  avg_chunks_per_report: number
}

export function StatsSection() {
  const [stats, setStats] = useState<Stats | null>(null)

  useEffect(() => {
    fetchStats()
  }, [])

  const fetchStats = async () => {
    try {
      const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      const response = await axios.get(`${API_URL}/api/stats`)
      setStats(response.data)
    } catch (err) {
      console.error('Failed to fetch stats:', err)
    }
  }

  if (!stats) return null

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-12">
      <div className="card text-center">
        <div className="flex justify-center mb-3">
          <FileText className="w-8 h-8 text-primary-600" />
        </div>
        <h3 className="text-3xl font-bold text-gray-900 mb-1">
          {stats.total_reports}
        </h3>
        <p className="text-gray-600">Reports Analyzed</p>
      </div>

      <div className="card text-center">
        <div className="flex justify-center mb-3">
          <Building2 className="w-8 h-8 text-primary-600" />
        </div>
        <h3 className="text-3xl font-bold text-gray-900 mb-1">
          {stats.unique_companies}
        </h3>
        <p className="text-gray-600">Companies</p>
      </div>

      <div className="card text-center">
        <div className="flex justify-center mb-3">
          <Database className="w-8 h-8 text-primary-600" />
        </div>
        <h3 className="text-3xl font-bold text-gray-900 mb-1">
          {stats.total_chunks}
        </h3>
        <p className="text-gray-600">Document Chunks</p>
      </div>
    </div>
  )
}
