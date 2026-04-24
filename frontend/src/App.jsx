import { useState, useCallback } from 'react'
import { useSelector } from 'react-redux'
import LogInteractionForm from './components/LogInteractionForm'
import ChatInterface from './components/ChatInterface'
import InteractionHistory from './components/InteractionHistory'

// ── Toast ──────────────────────────────────────────────────────────────────
function ToastContainer({ toasts }) {
  return (
    <div className="toast-container">
      {toasts.map((t) => (
        <div key={t.id} className={`toast ${t.type}`}>
          <span className="toast-icon">
            {t.type === 'success' ? '✅' : t.type === 'error' ? '❌' : 'ℹ️'}
          </span>
          {t.message}
        </div>
      ))}
    </div>
  )
}

let _toastId = 0

export default function App() {
  const [toasts, setToasts] = useState([])

  const addToast = useCallback((message, type = 'success') => {
    const id = ++_toastId
    setToasts((prev) => [...prev, { id, message, type }])
    setTimeout(() => setToasts((prev) => prev.filter((t) => t.id !== id)), 3200)
  }, [])

  return (
    <div className="app-shell">
      {/* Header */}
      <header className="app-header">
        <h1>
          <span className="logo-accent">HCP</span> CRM
          <span style={{ color: 'var(--muted)', fontWeight: 300, marginLeft: 8, fontSize: '0.85rem' }}>
            Healthcare Professional Manager
          </span>
        </h1>
        <span className="header-tag">AI-Powered · LangGraph</span>
      </header>

      {/* Main two-panel layout */}
      <div className="main-panels">
        {/* Left — Log Interaction Form */}
        <div className="left-panel">
          <div className="panel-header">
            <div className="cyan-bar" />
            <div>
              <h2>Log HCP Interaction</h2>
              <div className="panel-subtitle">Record and analyze HCP engagements</div>
            </div>
          </div>
          <LogInteractionForm onToast={addToast} />
        </div>

        {/* Right — Chat Interface */}
        <div className="right-panel">
          <div className="panel-header">
            <div className="purple-bar" />
            <div>
              <h2>🤖 AI Assistant</h2>
              <div className="panel-subtitle">Log interaction via chat</div>
            </div>
          </div>
          <ChatInterface onToast={addToast} />
        </div>
      </div>

      {/* Bottom — Interaction History */}
      <InteractionHistory onToast={addToast} />

      {/* Toasts */}
      <ToastContainer toasts={toasts} />
    </div>
  )
}
