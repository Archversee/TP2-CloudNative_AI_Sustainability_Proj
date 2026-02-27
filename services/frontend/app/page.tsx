'use client'

import { useState } from 'react'
import { Upload, Search as SearchIcon, TrendingUp } from 'lucide-react'
import { UploadSection } from '@/components/UploadSection'
import { SearchSection } from '@/components/SearchSection'
import { CompanyList } from '@/components/CompanyList'
import { StatsSection } from '@/components/StatsSection'

export default function Home() {
  const [activeTab, setActiveTab] = useState<'search' | 'upload' | 'companies'>('search')

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Combined Hero & Stats Section with Single Windmill Background */}
      <div 
        className="relative w-full"
        style={{
          backgroundImage: "url('https://images.unsplash.com/photo-1532601224476-15c79f2f7a51?q=80&w=2070&auto=format&fit=crop')",
          backgroundSize: 'cover',
          backgroundPosition: 'center',
          backgroundRepeat: 'no-repeat',
          backgroundAttachment: 'scroll',
        }}
      >
        {/* Dark Gradient Overlay for better text contrast */}
        <div className="absolute inset-0 bg-gradient-to-b from-black/60 via-black/60 to-black/70"></div>
        
        {/* Hero & Stats Content */}
        <div className="relative">
          {/* Hero Content - Centered */}
          <div className="max-w-7xl mx-auto px-6 pt-16 pb-12 flex flex-col items-center text-center">
            <h1 className="text-5xl md:text-6xl font-bold text-white mb-4">
              EcoEye
            </h1>
            <h2 className="text-xl md:text-2xl font-semibold text-white mb-2">
              AI-Powered ESG Greenwashing Detection
            </h2>
            <p className="text-sm md:text-base text-white/90 font-light max-w-3xl">
              Upload sustainability reports, analyze claims, and get truth scores powered by Gemini AI
            </p>
          </div>

          {/* Stats Section */}push
          <div className="max-w-7xl mx-auto px-6 pb-12">
            <StatsSection />
          </div>
        </div>
      </div>

      {/* Main Content - Added top margin */}
      <main className="max-w-7xl mx-auto px-6 pb-20 pt-8">
        {/* Tab Card */}
        <div className="bg-white rounded-2xl shadow-xl overflow-hidden">
          {/* Tab Navigation */}
          <div className="flex border-b border-gray-200">
            <button
              onClick={() => setActiveTab('search')}
              className={`flex-1 flex items-center justify-center gap-3 px-6 py-5 font-semibold text-base transition-all relative ${
                activeTab === 'search'
                  ? 'text-gray-900 bg-white'
                  : 'text-gray-500 hover:text-gray-700 hover:bg-gray-50'
              }`}
            >
              <div className={`flex items-center justify-center w-8 h-8 rounded-full ${
                activeTab === 'search' ? 'bg-gray-900 text-white' : 'bg-gray-200 text-gray-600'
              }`}>
                <span className="text-sm font-bold">1</span>
              </div>
              <span>RAG Search</span>
              {activeTab === 'search' && (
                <div className="absolute bottom-0 left-0 right-0 h-1 bg-gray-900"></div>
              )}
            </button>
            
            <button
              onClick={() => setActiveTab('upload')}
              className={`flex-1 flex items-center justify-center gap-3 px-6 py-5 font-semibold text-base transition-all relative ${
                activeTab === 'upload'
                  ? 'text-gray-900 bg-white'
                  : 'text-gray-500 hover:text-gray-700 hover:bg-gray-50'
              }`}
            >
              <div className={`flex items-center justify-center w-8 h-8 rounded-full ${
                activeTab === 'upload' ? 'bg-gray-900 text-white' : 'bg-gray-200 text-gray-600'
              }`}>
                <span className="text-sm font-bold">2</span>
              </div>
              <span>Upload Report</span>
              {activeTab === 'upload' && (
                <div className="absolute bottom-0 left-0 right-0 h-1 bg-gray-900"></div>
              )}
            </button>
            
            <button
              onClick={() => setActiveTab('companies')}
              className={`flex-1 flex items-center justify-center gap-3 px-6 py-5 font-semibold text-base transition-all relative ${
                activeTab === 'companies'
                  ? 'text-gray-900 bg-white'
                  : 'text-gray-500 hover:text-gray-700 hover:bg-gray-50'
              }`}
            >
              <div className={`flex items-center justify-center w-8 h-8 rounded-full ${
                activeTab === 'companies' ? 'bg-gray-900 text-white' : 'bg-gray-200 text-gray-600'
              }`}>
                <span className="text-sm font-bold">3</span>
              </div>
              <span>Companies</span>
              {activeTab === 'companies' && (
                <div className="absolute bottom-0 left-0 right-0 h-1 bg-gray-900"></div>
              )}
            </button>
          </div>

          {/* Tab Content */}
          <div className="p-8 md:p-12">
            {activeTab === 'search' && <SearchSection />}
            {activeTab === 'upload' && <UploadSection />}
            {activeTab === 'companies' && <CompanyList />}
          </div>
        </div>
      </main>
    </div>
  )
}
