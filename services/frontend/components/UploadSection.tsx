'use client'

import { useState } from 'react'
import { Upload, Loader2, CheckCircle, XCircle, FileText } from 'lucide-react'
import axios from 'axios'

interface UploadResponse {
  document_id: string
  filename: string
  company: string
  year: number | string
  status: string
  message: string
}

export function UploadSection() {
  const [file, setFile] = useState<File | null>(null)
  const [company, setCompany] = useState('')
  const [year, setYear] = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<UploadResponse | null>(null)
  const [error, setError] = useState('')

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0]
    if (selectedFile) {
      if (selectedFile.type !== 'application/pdf') {
        setError('Please select a PDF file')
        setFile(null)
        return
      }
      setFile(selectedFile)
      setError('')
    }
  }

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (!file) {
      setError('Please select a file')
      return
    }

    setLoading(true)
    setError('')
    setResult(null)

    try {
      const formData = new FormData()
      formData.append('file', file)
      
      if (company.trim()) {
        formData.append('company', company.trim())
      }
      
      if (year.trim()) {
        formData.append('year', year.trim())
      }

      const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      
      const response = await axios.post<UploadResponse>(
        `${API_URL}/api/upload`,
        formData,
        {
          headers: {
            'Content-Type': 'multipart/form-data',
          },
        }
      )

      setResult(response.data)
      setFile(null)
      setCompany('')
      setYear('')
      
      // Reset file input
      const fileInput = document.getElementById('file-input') as HTMLInputElement
      if (fileInput) fileInput.value = ''
      
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Upload failed. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-6">
      {/* Upload Form */}
      <div className="card">
        <h2 className="text-2xl font-bold text-gray-900 mb-4">📤 Upload Sustainability Report</h2>
        <p className="text-gray-600 mb-6">
          Upload a PDF sustainability report for AI-powered greenwashing analysis
        </p>

        <form onSubmit={handleUpload} className="space-y-4">
          {/* File Upload */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              PDF File *
            </label>
            <div className="relative">
              <input
                id="file-input"
                type="file"
                accept=".pdf"
                onChange={handleFileChange}
                className="hidden"
              />
                <label
                  htmlFor="file-input"
                  className="flex items-center justify-center gap-2 w-full border-2 border-dashed border-gray-300 rounded-lg p-8 cursor-pointer text-gray-700 hover:border-primary-500 transition-colors"
                >
                {file ? (
                  <>
                    <FileText className="w-6 h-6 text-primary-600" />
                    <span className="text-gray-700">{file.name}</span>
                    <span className="text-gray-500">({(file.size / 1024 / 1024).toFixed(2)} MB)</span>
                  </>
                ) : (
                  <>
                    <Upload className="w-6 h-6 text-gray-400" />
                    <span className="text-gray-600">Click to upload PDF</span>
                  </>
                )}
              </label>
            </div>
          </div>

          {/* Company Name (Optional) */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Company Name (Optional)
            </label>
            <input
              type="text"
              value={company}
              onChange={(e) => setCompany(e.target.value)}
              placeholder="e.g., CLCT or will be parsed from filename"
              className="input w-full"
            />
            <p className="text-xs text-gray-500 mt-1">
              If not provided, will be extracted from filename (e.g., "CLCT_2024.pdf")
            </p>
          </div>

          {/* Year (Optional) */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Year (Optional)
            </label>
            <input
              type="number"
              value={year}
              onChange={(e) => setYear(e.target.value)}
              placeholder="e.g., 2024 or will be parsed from filename"
              min="2000"
              max="2030"
              className="input w-full"
            />
          </div>

          <button
            type="submit"
            disabled={loading || !file}
            className="btn-primary w-full flex items-center justify-center gap-2"
          >
            {loading ? (
              <>
                <Loader2 className="w-5 h-5 animate-spin" />
                Processing...
              </>
            ) : (
              <>
                <Upload className="w-5 h-5" />
                Upload & Process
              </>
            )}
          </button>
        </form>
      </div>

      {/* Error */}
      {error && (
        <div className="card border-red-200 bg-red-50">
          <div className="flex items-center gap-2">
            <XCircle className="w-5 h-5 text-red-600" />
            <p className="text-red-600">{error}</p>
          </div>
        </div>
      )}

      {/* Success */}
      {result && (
        <div className="card border-green-200 bg-green-50">
          <div className="flex items-start gap-3">
            <CheckCircle className="w-6 h-6 text-green-600 flex-shrink-0 mt-0.5" />
            <div className="flex-1">
              <h3 className="text-lg font-semibold text-green-900 mb-2">Upload Successful!</h3>
              <div className="space-y-1 text-sm text-green-800">
                <p><strong>Document ID:</strong> {result.document_id}</p>
                <p><strong>Filename:</strong> {result.filename}</p>
                <p><strong>Company:</strong> {result.company}</p>
                <p><strong>Year:</strong> {result.year}</p>
                <p><strong>Status:</strong> {result.status}</p>
              </div>
              <div className="mt-4 p-3 bg-white rounded border border-green-200">
                <p className="text-sm text-gray-700">
                  🔄 Your document is being processed through our AI pipeline:
                </p>
                <ol className="text-sm text-gray-600 mt-2 ml-4 list-decimal space-y-1">
                  <li>PDF extraction</li>
                  <li>AI audit with Gemini</li>
                  <li>Embeddings generation for RAG</li>
                </ol>
                <p className="text-sm text-gray-500 mt-3">
                  This typically takes 1-2 minutes. Check the Companies tab to see results!
                </p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Instructions */}
      <div className="card bg-blue-50 border-blue-200">
        <h4 className="font-semibold text-blue-900 mb-3">📋 Filename Format</h4>
        <p className="text-blue-800 text-sm mb-2">
          For automatic company/year extraction, name your file:
        </p>
        <div className="space-y-1 text-sm">
          <code className="bg-white px-2 py-1 rounded border border-blue-200 text-blue-900">
            Company_Name_2024.pdf
          </code>
          <p className="text-blue-700">Examples:</p>
          <ul className="list-disc ml-6 text-blue-700 space-y-1">
            <li><code>CLCT_2024.pdf</code></li>
            <li><code>Genting_Singapore_2025.pdf</code></li>
            <li><code>SGX_Group_2024.pdf</code></li>
          </ul>
        </div>
      </div>
    </div>
  )
}
