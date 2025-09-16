import { useEffect, useState, useRef, DragEvent, ChangeEvent } from 'react'
import './App.css'

function App() {
  const [healthStatus, setHealthStatus] = useState<string>('Checking...')
  const [isDragging, setIsDragging] = useState(false)
  const [uploadStatus, setUploadStatus] = useState<string>('')
  const fileInputRef = useRef<HTMLInputElement>(null)
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
    </div>
  )
}

export default App
