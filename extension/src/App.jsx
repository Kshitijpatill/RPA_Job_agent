import { useState } from 'react'
import './App.css'

function App() {
  const [status, setStatus] = useState("Ready to apply!")

  const handleFillForm = async () => {
    setStatus("Filling form...")
    
    // Find the active tab and send a message to our content script
    let [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (tab) {
      chrome.tabs.sendMessage(tab.id, { action: "trigger_fill" }, (response) => {
        if (chrome.runtime.lastError) {
          setStatus("Error: Refresh the page.")
        } else {
          setStatus("Form filled!")
        }
      });
    }
  }

  return (
    <div style={{ width: '300px', padding: '15px', fontFamily: 'sans-serif' }}>
      <h2>AI Job Agent</h2>
      <p style={{ color: '#555' }}>{status}</p>
      <button 
        onClick={handleFillForm}
        style={{ width: '100%', padding: '10px', backgroundColor: '#007bff', color: 'white', border: 'none', borderRadius: '5px', cursor: 'pointer', fontWeight: 'bold' }}
      >
        Auto-Fill Page
      </button>
    </div>
  )
}

export default App