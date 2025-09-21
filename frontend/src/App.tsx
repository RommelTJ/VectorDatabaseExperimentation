import { useEffect, useState, useRef } from 'react'
import type { DragEvent, ChangeEvent } from 'react'
import './App.css'

function App() {
  const [healthStatus, setHealthStatus] = useState<string>('Checking...')
  const [isDragging, setIsDragging] = useState(false)
  const [uploadStatus, setUploadStatus] = useState<string>('')
  const [textQuery, setTextQuery] = useState<string>('')
  const [textSearchStatus, setTextSearchStatus] = useState<string>('')
  const [imageSearchStatus, setImageSearchStatus] = useState<string>('')
  const fileInputRef = useRef<HTMLInputElement>(null)
  const imageInputRef = useRef<HTMLInputElement>(null)
  const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000'

  useEffect(() => {
    fetch(`${apiUrl}/api/health`)
      .then(response => response.json())
      .then(data => {
        setHealthStatus(`Backend ${data.service}: ${data.status}`)
      })
      .catch(error => {
        console.error('Error fetching health:', error)
        setHealthStatus('Backend not available')
      })
  }, [])

  const handleDragOver = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault()
    setIsDragging(true)
  }

  const handleDragLeave = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault()
    setIsDragging(false)
  }

  const handleDrop = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault()
    setIsDragging(false)

    const files = Array.from(e.dataTransfer.files)
    const pdfFile = files.find(file => file.name.toLowerCase().endsWith('.pdf'))

    if (pdfFile) {
      uploadFile(pdfFile)
    } else {
      setUploadStatus('Please upload a PDF file')
    }
  }

  const handleFileSelect = (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) {
      uploadFile(file)
    }
  }

  const uploadFile = async (file: File) => {
    if (!file.name.toLowerCase().endsWith('.pdf')) {
      setUploadStatus('Only PDF files are allowed')
      return
    }

    const formData = new FormData()
    formData.append('file', file)

    try {
      setUploadStatus('Uploading...')
      const response = await fetch(`${apiUrl}/api/upload`, {
        method: 'POST',
        body: formData
      })

      if (response.ok) {
        const data = await response.json()
        setUploadStatus(`Successfully uploaded: ${data.filename}`)
      } else {
        const error = await response.json()
        setUploadStatus(`Upload failed: ${error.detail || 'Unknown error'}`)
      }
    } catch (error) {
      setUploadStatus(`Upload failed: ${error}`)
    }
  }

  const handleTextSearch = async () => {
    if (!textQuery.trim()) {
      setTextSearchStatus('Please enter a search query')
      return
    }

    try {
      setTextSearchStatus('Searching...')
      const response = await fetch(`${apiUrl}/api/search/text`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          query: textQuery,
          limit: 10
        })
      })

      if (!response.ok) {
        const error = await response.json()
        setTextSearchStatus(`Error: ${error.detail || 'Search failed'}`)
      }
    } catch (error) {
      setTextSearchStatus(`Error: ${error}`)
    }
  }

  const handleImageSearch = async (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    const formData = new FormData()
    formData.append('file', file)

    try {
      setImageSearchStatus('Searching...')
      const response = await fetch(`${apiUrl}/api/search/image`, {
        method: 'POST',
        body: formData
      })

      if (!response.ok) {
        const error = await response.json()
        setImageSearchStatus(`Error: ${error.detail || 'Search failed'}`)
      }
    } catch (error) {
      setImageSearchStatus(`Error: ${error}`)
    }
  }

  return (
    <div>
      <h1>Vector Database Experimentation</h1>
      <p>Health check: {healthStatus}</p>

      <div
        className={`upload-area ${isDragging ? 'dragging' : ''}`}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
        style={{
          border: `2px dashed ${isDragging ? '#0066cc' : '#ccc'}`,
          borderRadius: '8px',
          padding: '40px',
          margin: '20px 0',
          textAlign: 'center',
          cursor: 'pointer',
          backgroundColor: isDragging ? '#f0f8ff' : 'transparent'
        }}
      >
        <p>Drag and drop a PDF file here, or click to select</p>
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf"
          onChange={handleFileSelect}
          style={{ display: 'none' }}
        />
      </div>

      {uploadStatus && <p>Status: {uploadStatus}</p>}

      <div style={{ marginTop: '40px' }}>
        <h2>Search</h2>

        <div style={{ marginBottom: '30px' }}>
          <h3>Text Search</h3>
          <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
            <input
              type="text"
              value={textQuery}
              onChange={(e) => setTextQuery(e.target.value)}
              placeholder="Enter search query..."
              style={{
                padding: '8px',
                borderRadius: '4px',
                border: '1px solid #ccc',
                flex: 1
              }}
              onKeyPress={(e) => e.key === 'Enter' && handleTextSearch()}
            />
            <button
              onClick={handleTextSearch}
              style={{
                padding: '8px 16px',
                borderRadius: '4px',
                border: '1px solid #0066cc',
                backgroundColor: '#0066cc',
                color: 'white',
                cursor: 'pointer'
              }}
            >
              Search
            </button>
          </div>
          {textSearchStatus && (
            <p style={{
              marginTop: '10px',
              padding: '10px',
              borderRadius: '4px',
              backgroundColor: textSearchStatus.includes('Error') ? '#ffebee' : '#e3f2fd',
              color: textSearchStatus.includes('Error') ? '#c62828' : '#1565c0'
            }}>
              {textSearchStatus}
            </p>
          )}
        </div>

        <div>
          <h3>Image Search</h3>
          <button
            onClick={() => imageInputRef.current?.click()}
            style={{
              padding: '8px 16px',
              borderRadius: '4px',
              border: '1px solid #0066cc',
              backgroundColor: '#0066cc',
              color: 'white',
              cursor: 'pointer'
            }}
          >
            Upload Image to Search
          </button>
          <input
            ref={imageInputRef}
            type="file"
            accept="image/*"
            onChange={handleImageSearch}
            style={{ display: 'none' }}
          />
          {imageSearchStatus && (
            <p style={{
              marginTop: '10px',
              padding: '10px',
              borderRadius: '4px',
              backgroundColor: imageSearchStatus.includes('Error') ? '#ffebee' : '#e3f2fd',
              color: imageSearchStatus.includes('Error') ? '#c62828' : '#1565c0'
            }}>
              {imageSearchStatus}
            </p>
          )}
        </div>
      </div>
    </div>
  )
}

export default App
