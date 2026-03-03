import { useState, useEffect, useRef, useCallback } from 'react'
import type { ChatMessage, WsMessage, ExtractedTodoItem, Todo } from '../types'
import ChatMessageComponent from './ChatMessage'
import { createTodo, updateTodo, getLabels } from '../api/todos'
import './ChatInterface.css'

let msgIdCounter = 0
const newId = () => String(++msgIdCounter)

interface Props {
  onRefreshTodos: () => void
  todoContext: Todo | null
  onClearTodoContext: () => void
}

type ConnectionStatus = 'connecting' | 'open' | 'closed' | 'error'

interface QuickAction {
  label: string
  icon: string
  message: string
}

const QUICK_ACTIONS: QuickAction[] = [
  { icon: '📋', label: 'Active', message: 'List my active todos' },
  { icon: '📅', label: 'Due today', message: 'What todos are due today?' },
  { icon: '⚠', label: 'Overdue', message: 'Show me all overdue todos' },
  { icon: '⭐', label: 'Focus', message: 'Show my focus list' },
  { icon: '📊', label: 'Stats', message: 'Give me a summary of my todo stats' },
  { icon: '💡', label: 'Suggest', message: 'What should I focus on today? Give me your top suggestions' },
  { icon: '🗓', label: 'This week', message: 'What todos are due this week?' },
]

const PRIORITY_LABELS = ['', '!', '!!']

export default function ChatInterface({ onRefreshTodos, todoContext, onClearTodoContext }: Props) {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: newId(),
      role: 'assistant',
      content: "Hello! I'm your AI assistant for Terminal Todos.\n\nYou can ask me to:\n- Create, update, or complete todos\n- Search and discuss your notes\n- Extract action items from meeting notes you paste in\n- Check what's due, overdue, or in your focus list\n- Generate email drafts\n\nUse the quick actions below or just type naturally.",
    },
  ])
  const [input, setInput] = useState('')
  const [sending, setSending] = useState(false)
  const [status, setStatus] = useState<ConnectionStatus>('connecting')
  const [showPastePanel, setShowPastePanel] = useState(false)
  const [pasteText, setPasteText] = useState('')
  const [availableLabels, setAvailableLabels] = useState<string[]>([])
  const wsRef = useRef<WebSocket | null>(null)
  const bottomRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const pasteRef = useRef<HTMLTextAreaElement>(null)
  const streamingIdRef = useRef<string | null>(null)

  const sendRaw = useCallback((text: string) => {
    const ws = wsRef.current
    if (!ws || ws.readyState !== WebSocket.OPEN || sending) return false
    setMessages(prev => [...prev, { id: newId(), role: 'user', content: text }])
    setSending(true)
    ws.send(JSON.stringify({ message: text }))
    return true
  }, [sending])

  const connect = useCallback(() => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const ws = new WebSocket(`${protocol}//${window.location.host}/ws/chat`)
    wsRef.current = ws

    ws.onopen = () => setStatus('open')
    ws.onerror = () => setStatus('error')
    ws.onclose = () => {
      setStatus('closed')
      setTimeout(connect, 3000)
    }

    ws.onmessage = (event) => {
      const msg: WsMessage = JSON.parse(event.data)

      switch (msg.type) {
        case 'token': {
          const token = msg.content ?? ''
          setMessages(prev => {
            const last = prev[prev.length - 1]
            if (last && last.role === 'assistant' && last.isStreaming) {
              return prev.map(m => m.id === last.id ? { ...m, content: m.content + token } : m)
            }
            const newMsg: ChatMessage = { id: newId(), role: 'assistant', content: token, isStreaming: true }
            streamingIdRef.current = newMsg.id
            return [...prev, newMsg]
          })
          break
        }
        case 'tool_start': {
          setMessages(prev => [...prev, { id: newId(), role: 'tool', content: 'running…', toolName: msg.tool ?? 'unknown' }])
          break
        }
        case 'tool_end': {
          const toolName = msg.tool ?? ''
          setMessages(prev => {
            const idx = [...prev].reverse().findIndex(m => m.role === 'tool' && m.toolName === toolName && m.content === 'running…')
            if (idx === -1) return prev
            const realIdx = prev.length - 1 - idx
            return prev.map((m, i) => i === realIdx ? { ...m, content: 'done' } : m)
          })
          break
        }
        case 'done': {
          setMessages(prev => prev.map(m => m.isStreaming ? { ...m, isStreaming: false } : m))
          streamingIdRef.current = null
          setSending(false)
          break
        }
        case 'refresh_todos': {
          onRefreshTodos()
          break
        }
        case 'error': {
          setMessages(prev => [...prev, { id: newId(), role: 'assistant', content: `⚠ Error: ${msg.message ?? 'Unknown error'}` }])
          setSending(false)
          break
        }
      }
    }
  }, [onRefreshTodos])

  useEffect(() => {
    connect()
    return () => { wsRef.current?.close() }
  }, [connect])

  // Fetch labels once on mount so they're ready when an extraction card appears.
  // Re-fetch whenever the paste panel opens to pick up any newly created labels.
  useEffect(() => {
    getLabels().then(setAvailableLabels).catch(() => {})
  }, [showPastePanel])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // Auto-focus the input and scroll when a todo is brought into context
  useEffect(() => {
    if (todoContext) {
      setTimeout(() => textareaRef.current?.focus(), 50)
    }
  }, [todoContext])

  const sendMessage = useCallback(() => {
    const text = input.trim()
    if (!text || sending || status !== 'open') return

    let payload = text
    if (todoContext) {
      const parts: string[] = [`[Todo #${todoContext.id}: "${todoContext.content}"`]
      if (todoContext.priority > 0) parts.push(`priority: ${todoContext.priority === 2 ? 'high' : 'medium'}`)
      if (todoContext.due_date) parts.push(`due: ${todoContext.due_date.slice(0, 10)}`)
      if (todoContext.labels && todoContext.labels.length > 0) parts.push(`labels: ${todoContext.labels.join(', ')}`)
      if (todoContext.focus_order !== null) parts.push('in focus list')
      payload = `${parts.join(', ')}]\n\n${text}`
    }

    const sent = sendRaw(payload)
    if (sent) {
      setInput('')
      onClearTodoContext()
      if (textareaRef.current) textareaRef.current.style.height = 'auto'
    }
  }, [input, sending, status, sendRaw, todoContext, onClearTodoContext])

  const handleExtractFromNotes = async () => {
    const text = pasteText.trim()
    if (!text) return
    setPasteText('')
    setShowPastePanel(false)

    // Show a loading placeholder in the chat
    const loadingId = newId()
    setMessages(prev => [...prev, {
      id: loadingId,
      role: 'assistant' as const,
      content: 'Analyzing your notes and extracting action items…',
      isStreaming: true,
    }])

    try {
      const res = await fetch('/api/notes/extract', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content: text }),
      })
      if (!res.ok) throw new Error(await res.text())
      const data = await res.json()

      // Replace loading message with the interactive extraction card
      setMessages(prev => prev.map(m =>
        m.id === loadingId
          ? {
              id: loadingId,
              role: 'extraction' as const,
              content: '',
              extractedTodos: data.todos,
              extractionTitle: data.title,
              extractionNoteType: data.note_type,
              extractionSubmitted: false,
              extractionAddedCount: 0,
            }
          : m,
      ))
    } catch (err) {
      setMessages(prev => prev.map(m =>
        m.id === loadingId
          ? { ...m, isStreaming: false, content: `⚠ Extraction failed: ${err instanceof Error ? err.message : 'Unknown error'}` }
          : m,
      ))
    }
  }

  const handleExtractionSubmit = useCallback(async (messageId: string, selected: ExtractedTodoItem[], label: string) => {
    // Create each selected todo via the REST API
    const created = await Promise.all(selected.map(t => createTodo(t.content, t.priority)))

    // Apply label to all created todos if one was specified
    if (label) {
      await Promise.all(created.map(todo => updateTodo(todo.id, { labels: [label] })))
    }

    // Update the message to show the confirmation state
    setMessages(prev => prev.map(m =>
      m.id === messageId
        ? { ...m, extractionSubmitted: true, extractionAddedCount: selected.length, extractionLabel: label || undefined }
        : m,
    ))

    // Refresh the todo panel
    onRefreshTodos()
  }, [onRefreshTodos])

  const handleSummarizeNotes = () => {
    const text = pasteText.trim()
    if (!text || status !== 'open') return
    const prompt = `Please summarize these notes and tell me the key points and any action items:\n\n${text}`
    const sent = sendRaw(prompt)
    if (sent) {
      setShowPastePanel(false)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  const handleInput = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInput(e.target.value)
    e.target.style.height = 'auto'
    e.target.style.height = Math.min(e.target.scrollHeight, 140) + 'px'
  }

  const statusLabel = { connecting: 'connecting…', open: 'ready', closed: 'reconnecting…', error: 'error' }[status]
  const canSend = input.trim().length > 0 && !sending && status === 'open'
  const canExtract = pasteText.trim().length > 0 && !sending && status === 'open'

  return (
    <div className="chat-interface">
      <div className="chat-header">
        <span className="chat-header-title">AI Chat</span>
        <div className="chat-header-right">
          <button
            className={`paste-toggle-btn ${showPastePanel ? 'active' : ''}`}
            onClick={() => { setShowPastePanel(v => !v); setTimeout(() => pasteRef.current?.focus(), 50) }}
            title="Paste notes to extract todos"
          >
            📋 Paste notes
          </button>
          <span className={`chat-status chat-status-${status}`}>{statusLabel}</span>
        </div>
      </div>

      {/* Paste notes panel */}
      {showPastePanel && (
        <div className="paste-panel">
          <div className="paste-panel-label">Paste meeting notes, emails, or any text — I'll extract todos or summarize for you</div>
          <textarea
            ref={pasteRef}
            className="paste-textarea"
            placeholder="Paste your notes here…"
            value={pasteText}
            onChange={e => setPasteText(e.target.value)}
            rows={6}
          />
          <div className="paste-actions">
            <button className="paste-btn paste-btn--primary" onClick={handleExtractFromNotes} disabled={!canExtract}>
              ✓ Extract todos &amp; add to list
            </button>
            <button className="paste-btn paste-btn--secondary" onClick={handleSummarizeNotes} disabled={!canExtract}>
              📝 Summarize &amp; discuss
            </button>
            <button className="paste-btn paste-btn--ghost" onClick={() => { setShowPastePanel(false); setPasteText('') }}>
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* Message list */}
      <div className="chat-messages">
        {messages.map(msg => (
          <ChatMessageComponent key={msg.id} message={msg} availableLabels={availableLabels} onExtractionSubmit={handleExtractionSubmit} />
        ))}
        {sending && !streamingIdRef.current && (
          <div className="chat-thinking">
            <span className="thinking-dot" /><span className="thinking-dot" /><span className="thinking-dot" />
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Quick action chips */}
      <div className="quick-actions">
        {QUICK_ACTIONS.map(qa => (
          <button
            key={qa.label}
            className="quick-action-chip"
            onClick={() => sendRaw(qa.message)}
            disabled={sending || status !== 'open'}
            title={qa.message}
          >
            <span>{qa.icon}</span>
            <span>{qa.label}</span>
          </button>
        ))}
      </div>

      {/* Todo context chip */}
      {todoContext && (
        <div className="todo-context-bar">
          <div className="todo-context-chip">
            <span className="todo-context-icon">📌</span>
            <span className="todo-context-label">Context:</span>
            <span className="todo-context-content">{todoContext.content}</span>
            {todoContext.priority > 0 && (
              <span className={`todo-context-badge priority-badge ${todoContext.priority === 2 ? 'high' : 'med'}`}>
                {PRIORITY_LABELS[todoContext.priority]}
              </span>
            )}
            {todoContext.due_date && (
              <span className="todo-context-badge">
                {new Date(todoContext.due_date.slice(0, 10) + 'T00:00:00').toLocaleDateString(undefined, { month: 'short', day: 'numeric' })}
              </span>
            )}
            {todoContext.labels && todoContext.labels.length > 0 && todoContext.labels.map(l => (
              <span key={l} className="todo-context-badge label-badge">{l}</span>
            ))}
            <button className="todo-context-dismiss" onClick={onClearTodoContext} title="Remove context">×</button>
          </div>
        </div>
      )}

      {/* Input area */}
      <div className="chat-input-area">
        <div className="chat-input-wrapper">
          <textarea
            ref={textareaRef}
            className="chat-input"
            placeholder={todoContext ? 'Ask about this todo… (Enter to send)' : 'Ask me anything… (Enter to send, Shift+Enter for newline)'}
            value={input}
            onChange={handleInput}
            onKeyDown={handleKeyDown}
            rows={1}
            disabled={status !== 'open'}
          />
          <button
            className={`chat-send-btn ${canSend ? 'active' : ''}`}
            onClick={sendMessage}
            disabled={!canSend}
            title="Send (Enter)"
          >
            ↑
          </button>
        </div>
      </div>
    </div>
  )
}
