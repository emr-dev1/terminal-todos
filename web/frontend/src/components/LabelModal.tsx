import { useState, useEffect, useRef, useCallback } from 'react'
import type { Todo } from '../types'
import { listTodos, updateTodo, getLabels } from '../api/todos'
import './LabelModal.css'

// Deterministic color palette (must match TodoItem.tsx + TodoPanel.tsx)
const LABEL_PALETTE = [
  '#1a3a52', '#1a3d2b', '#3d1f1a', '#2d1a3d',
  '#1a2d3d', '#3d3000', '#2a1a3d', '#1a2d2d',
]
function hashCode(s: string): number {
  let h = 0
  for (let i = 0; i < s.length; i++) h = (Math.imul(31, h) + s.charCodeAt(i)) | 0
  return h
}
function labelColor(label: string): string {
  return LABEL_PALETTE[Math.abs(hashCode(label)) % LABEL_PALETTE.length]
}

interface Props {
  availableLabels: string[]
  onClose: () => void
  onLabeled: () => void
}

type Mode = 'unlabeled' | 'all'

export default function LabelModal({ availableLabels: initialLabels, onClose, onLabeled }: Props) {
  const [todos, setTodos] = useState<Todo[]>([])
  const [currentIdx, setCurrentIdx] = useState(0)
  const [mode, setMode] = useState<Mode>('unlabeled')
  // staged: per-todo label sets (draft until saved)
  const [staged, setStaged] = useState<Map<number, string[]>>(new Map())
  const [input, setInput] = useState('')
  const [suggestions, setSuggestions] = useState<string[]>(initialLabels)
  const [savedIds, setSavedIds] = useState<Set<number>>(new Set())
  const [loading, setLoading] = useState(true)
  const inputRef = useRef<HTMLInputElement>(null)

  const loadTodos = useCallback(async (m: Mode) => {
    setLoading(true)
    try {
      const all = await listTodos('active')
      const filtered = m === 'unlabeled'
        ? all.filter(t => !t.labels || t.labels.length === 0)
        : all
      setTodos(filtered)
      // Pre-populate staged from existing labels
      const map = new Map<number, string[]>()
      filtered.forEach(t => { if (t.labels && t.labels.length > 0) map.set(t.id, [...t.labels]) })
      setStaged(map)
      setCurrentIdx(0)
    } finally {
      setLoading(false)
    }
  }, [])

  // Refresh label suggestions from server
  const refreshSuggestions = useCallback(async () => {
    try {
      const labels = await getLabels()
      setSuggestions(labels)
    } catch { /* non-critical */ }
  }, [])

  useEffect(() => { loadTodos(mode) }, [loadTodos, mode])
  useEffect(() => {
    setTimeout(() => inputRef.current?.focus(), 100)
  }, [currentIdx])

  const todo = todos[currentIdx] ?? null
  const currentLabels: string[] = (todo ? staged.get(todo.id) : undefined) ?? []

  const addLabel = (label: string) => {
    const trimmed = label.trim()
    if (!trimmed || !todo) return
    setStaged(prev => {
      const next = new Map(prev)
      const existing = next.get(todo.id) ?? []
      if (!existing.includes(trimmed)) next.set(todo.id, [...existing, trimmed])
      return next
    })
    setInput('')
    inputRef.current?.focus()
  }

  const removeLabel = (label: string) => {
    if (!todo) return
    setStaged(prev => {
      const next = new Map(prev)
      const existing = next.get(todo.id) ?? []
      next.set(todo.id, existing.filter(l => l !== label))
      return next
    })
  }

  const saveAndNext = async () => {
    if (!todo) return
    try {
      const labels = staged.get(todo.id) ?? []
      await updateTodo(todo.id, { labels })
      setSavedIds(prev => new Set(prev).add(todo.id))
      onLabeled()
      refreshSuggestions()
      setCurrentIdx(i => i + 1)
      setInput('')
    } catch (err) {
      console.error('Failed to save labels:', err)
    }
  }

  const skip = () => {
    setCurrentIdx(i => i + 1)
    setInput('')
  }

  const prev = () => {
    setCurrentIdx(i => Math.max(0, i - 1))
    setInput('')
  }

  const handleInputKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      e.preventDefault()
      if (input.trim()) addLabel(input)
      else saveAndNext()
    }
    if (e.key === 'Escape') onClose()
  }

  const handleModeChange = (m: Mode) => {
    setMode(m)
    setSavedIds(new Set())
  }

  const labeledCount = savedIds.size
  const total = todos.length

  // Suggestions not already on this todo
  const filteredSuggestions = suggestions.filter(s => !currentLabels.includes(s))

  const isDone = !loading && currentIdx >= todos.length

  return (
    <div className="label-modal-overlay" onClick={e => { if (e.target === e.currentTarget) onClose() }}>
      <div className="label-modal">
        {/* Header */}
        <div className="label-modal-header">
          <span className="label-modal-title">Quick Label</span>
          <div className="label-modal-header-right">
            {total > 0 && (
              <span className="label-modal-progress">
                {Math.min(currentIdx + 1, total)} / {total}
                {labeledCount > 0 && <span className="label-modal-saved"> · {labeledCount} saved</span>}
              </span>
            )}
            <div className="label-modal-mode-toggle">
              <button
                className={`mode-btn ${mode === 'unlabeled' ? 'active' : ''}`}
                onClick={() => handleModeChange('unlabeled')}
              >
                Unlabeled
              </button>
              <button
                className={`mode-btn ${mode === 'all' ? 'active' : ''}`}
                onClick={() => handleModeChange('all')}
              >
                All
              </button>
            </div>
            <button className="label-modal-close" onClick={onClose} title="Close">×</button>
          </div>
        </div>

        {/* Body */}
        <div className="label-modal-body">
          {loading ? (
            <div className="label-modal-empty">Loading…</div>
          ) : isDone ? (
            <div className="label-modal-done">
              <div className="label-modal-done-icon">✓</div>
              <div className="label-modal-done-text">
                {labeledCount > 0
                  ? `Done! Labeled ${labeledCount} todo${labeledCount !== 1 ? 's' : ''}.`
                  : 'All caught up!'}
              </div>
              <button className="label-modal-close-btn" onClick={onClose}>Close</button>
            </div>
          ) : todo ? (
            <>
              {/* Todo card */}
              <div className="label-card">
                <div className="label-card-meta">
                  <span className="label-card-id">#{todo.id}</span>
                  {todo.priority > 0 && (
                    <span className="label-card-priority">{todo.priority === 2 ? '!!' : '!'}</span>
                  )}
                  <button className="label-card-skip" onClick={skip}>Skip →</button>
                </div>
                <div className="label-card-content">{todo.content}</div>
              </div>

              {/* Current labels on this todo */}
              <div className="label-current">
                <span className="label-section-label">Labels:</span>
                <div className="label-chips">
                  {currentLabels.length === 0 && (
                    <span className="label-empty-hint">none yet</span>
                  )}
                  {currentLabels.map(label => (
                    <span
                      key={label}
                      className="label-chip"
                      style={{ background: labelColor(label) }}
                    >
                      {label}
                      <button className="label-chip-remove" onClick={() => removeLabel(label)}>×</button>
                    </span>
                  ))}
                </div>
              </div>

              {/* Add label input */}
              <div className="label-add-row">
                <input
                  ref={inputRef}
                  className="label-input"
                  placeholder="Type a label… (Enter to add)"
                  value={input}
                  onChange={e => setInput(e.target.value)}
                  onKeyDown={handleInputKeyDown}
                />
              </div>

              {/* Suggestion chips */}
              {filteredSuggestions.length > 0 && (
                <div className="label-suggestions">
                  <span className="label-section-label">Suggestions:</span>
                  <div className="label-suggestion-chips">
                    {filteredSuggestions.map(s => (
                      <button
                        key={s}
                        className="label-suggestion-chip"
                        style={{ borderColor: labelColor(s) }}
                        onClick={() => addLabel(s)}
                      >
                        {s}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {/* Navigation */}
              <div className="label-modal-nav">
                <button
                  className="label-nav-btn"
                  onClick={prev}
                  disabled={currentIdx === 0}
                >
                  ← Prev
                </button>
                <button
                  className="label-save-btn"
                  onClick={saveAndNext}
                >
                  Save & Next →
                </button>
              </div>
            </>
          ) : (
            <div className="label-modal-empty">
              {mode === 'unlabeled' ? 'All active todos already have labels.' : 'No active todos found.'}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
