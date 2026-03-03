import { useCallback, useEffect, useRef, useState } from 'react'
import './App.css'
import Header from './components/Header'
import TodoPanel from './components/TodoPanel'
import ChatInterface from './components/ChatInterface'
import SettingsModal from './components/SettingsModal'
import type { Todo } from './types'

const COLLAPSE_BREAKPOINT = 768

function App() {
  const refreshTodosRef = useRef<(() => void) | null>(null)
  // Start collapsed if the window is already narrow
  const [panelCollapsed, setPanelCollapsed] = useState(() => window.innerWidth < COLLAPSE_BREAKPOINT)
  // Track whether the user manually toggled at wide width — don't auto-override their choice
  const userOverrodeRef = useRef(false)

  useEffect(() => {
    const onResize = () => {
      if (window.innerWidth < COLLAPSE_BREAKPOINT) {
        // Always collapse below breakpoint
        setPanelCollapsed(true)
        userOverrodeRef.current = false
      } else if (!userOverrodeRef.current) {
        // Auto-expand when going wide again, unless the user manually collapsed it
        setPanelCollapsed(false)
      }
    }
    window.addEventListener('resize', onResize)
    return () => window.removeEventListener('resize', onResize)
  }, [])

  const handleToggleCollapse = useCallback(() => {
    // Flag that the user explicitly chose a state at this width
    userOverrodeRef.current = window.innerWidth >= COLLAPSE_BREAKPOINT
    setPanelCollapsed(v => !v)
  }, [])

  const [chatTodoContext, setChatTodoContext] = useState<Todo | null>(null)
  const [showSettings, setShowSettings] = useState(false)

  const handleRefreshTodos = useCallback(() => {
    refreshTodosRef.current?.()
  }, [])

  const registerRefresh = useCallback((fn: () => void) => {
    refreshTodosRef.current = fn
  }, [])

  const handleSendToChat = useCallback((todo: Todo) => {
    setChatTodoContext(todo)
    // Expand the panel if collapsed on mobile so the user can see the chip
  }, [])

  const handleClearTodoContext = useCallback(() => {
    setChatTodoContext(null)
  }, [])

  return (
    <div className="app">
      <Header onOpenSettings={() => setShowSettings(true)} />
      <div className={`app-body ${panelCollapsed ? 'panel-collapsed' : ''}`}>
        <TodoPanel
          onRegisterRefresh={registerRefresh}
          collapsed={panelCollapsed}
          onToggleCollapse={handleToggleCollapse}
          onSendToChat={handleSendToChat}
        />
        <ChatInterface
          onRefreshTodos={handleRefreshTodos}
          todoContext={chatTodoContext}
          onClearTodoContext={handleClearTodoContext}
        />
      </div>
      {showSettings && (
        <SettingsModal onClose={() => setShowSettings(false)} />
      )}
    </div>
  )
}

export default App
