import { useState, useEffect } from 'react'
import './Header.css'

interface Props {
  onOpenSettings: () => void
}

export default function Header({ onOpenSettings }: Props) {
  const [connected, setConnected] = useState<boolean | null>(null)

  useEffect(() => {
    fetch('/health')
      .then(r => setConnected(r.ok))
      .catch(() => setConnected(false))
  }, [])

  return (
    <header className="header">
      <div className="header-brand">
        <span className="header-icon">◈</span>
        <span className="header-title">Terminal Todos</span>
      </div>
      <div className="header-right">
        <div className="header-status">
          <span className={`status-dot ${connected === null ? 'status-connecting' : connected ? 'status-ok' : 'status-error'}`} />
          <span className="status-label">
            {connected === null ? 'connecting…' : connected ? 'connected' : 'offline'}
          </span>
        </div>
        <button className="header-settings-btn" onClick={onOpenSettings} title="Settings">
          ⚙
        </button>
      </div>
    </header>
  )
}
