'use client'

import { useState } from 'react'
import { Upload, Search as SearchIcon, TrendingUp, FileText } from 'lucide-react'
import { UploadSection } from '@/components/UploadSection'
import { SearchSection } from '@/components/SearchSection'
import { CompanyList } from '@/components/CompanyList'
import { StatsSection } from '@/components/StatsSection'

export default function Home() {
  const [activeTab, setActiveTab] = useState<'search' | 'upload' | 'companies'>('search')

  return (
    <div className="container mx-auto px-4 py-8">
      {/* Hero Section */}
      <div className="text-center mb-12">
        <h1 className="text-5xl font-bold text-gray-900 mb-4">
          🌱 EcoLens
        </h1>
        <p className="text-xl text-gray-600 max-w-2xl mx-auto">
          AI-Powered ESG Greenwashing Detection
        </p>
        <p className="text-gray-500 mt-2">
          Upload sustainability reports, analyze claims, and get truth scores powered by Gemini AI
        </p>
      </div>

      {/* Stats */}
      <StatsSection />

      {/* Tab Navigation */}
      <div className="flex justify-center mb-8 border-b border-gray-200">
        <button
          onClick={() => setActiveTab('search')}
          className={`px-6 py-3 flex items-center gap-2 border-b-2 transition-colors ${
            activeTab === 'search'
              ? 'border-primary-600 text-primary-600'
              : 'border-transparent text-gray-600 hover:text-gray-900'
          }`}
        >
          <SearchIcon className="w-5 h-5" />
          RAG Search
        </button>
        <button
          onClick={() => setActiveTab('upload')}
          className={`px-6 py-3 flex items-center gap-2 border-b-2 transition-colors ${
            activeTab === 'upload'
              ? 'border-primary-600 text-primary-600'
              : 'border-transparent text-gray-600 hover:text-gray-900'
          }`}
        >
          <Upload className="w-5 h-5" />
          Upload Report
        </button>
        <button
          onClick={() => setActiveTab('companies')}
          className={`px-6 py-3 flex items-center gap-2 border-b-2 transition-colors ${
            activeTab === 'companies'
              ? 'border-primary-600 text-primary-600'
              : 'border-transparent text-gray-600 hover:text-gray-900'
          }`}
        >
          <TrendingUp className="w-5 h-5" />
          Companies
        </button>
      </div>

      {/* Tab Content */}
      <div className="max-w-6xl mx-auto">
        {activeTab === 'search' && <SearchSection />}
        {activeTab === 'upload' && <UploadSection />}
        {activeTab === 'companies' && <CompanyList />}
      </div>
    </div>
  )
}
