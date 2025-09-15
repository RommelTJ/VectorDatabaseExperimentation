import { useEffect, useState } from 'react'
import './App.css'

function App() {
  const [healthStatus, setHealthStatus] = useState<string>('Checking...')

  useEffect(() => {
    const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000'
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

  return (
    <div>
      <h1>Hello World</h1>
      <p>Health check: {healthStatus}</p>
    </div>
  )
}

export default App
