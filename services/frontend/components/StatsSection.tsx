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
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

  useEffect(() => {
    fetchStats()
  }, [])

  const fetchStats = async () => {
    try {
      const response = await axios.get(`${apiUrl}/api/stats`)
      setStats(response.data)
    } catch (err) {
      console.error('Failed to fetch stats:', err)
    }
  }

  if (!stats) return null

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
      {/* Reports Analysed Card */}
      <div className="bg-white/10 backdrop-blur-md rounded-2xl p-8 text-center border border-white/20 shadow-2xl hover:bg-white/15 transition-all">
        <div className="flex justify-center mb-4">
          <div className="w-16 h-16 bg-green-600/30 rounded-full flex items-center justify-center">
            <FileText className="w-8 h-8 text-white" strokeWidth={2} />
          </div>
        </div>
        <h3 className="text-5xl font-bold text-white mb-2">
          {stats.total_reports}
        </h3>
        <p className="text-white font-medium text-base">Reports Analysed</p>
      </div>

      {/* Companies Card */}
      <div className="bg-white/10 backdrop-blur-md rounded-2xl p-8 text-center border border-white/20 shadow-2xl hover:bg-white/15 transition-all">
        <div className="flex justify-center mb-4">
          <div className="w-16 h-16 bg-green-600/30 rounded-full flex items-center justify-center">
            <Building2 className="w-8 h-8 text-white" strokeWidth={2} />
          </div>
        </div>
        <h3 className="text-5xl font-bold text-white mb-2">
          {stats.unique_companies}
        </h3>
        <p className="text-white font-medium text-base">Companies</p>
      </div>

      {/* Document Chunks Card */}
      <div className="bg-white/10 backdrop-blur-md rounded-2xl p-8 text-center border border-white/20 shadow-2xl hover:bg-white/15 transition-all">
        <div className="flex justify-center mb-4">
          <div className="w-16 h-16 bg-green-600/30 rounded-full flex items-center justify-center">
            <Database className="w-8 h-8 text-white" strokeWidth={2} />
          </div>
        </div>
        <h3 className="text-5xl font-bold text-white mb-2">
          {stats.total_chunks}
        </h3>
        <p className="text-white font-medium text-base">Document Chunks</p>
      </div>
    </div>
  )
}
