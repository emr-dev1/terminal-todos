import { useState, useEffect, useRef, useCallback } from 'react'
import type { Todo } from '../types'
import { listTodos, getFocusedTodos, updateTodo, completeTodo } from '../api/todos'
import { createNote } from '../api/notes'
import './ReviewModal.css'

// Deterministic label colors (must match LabelModal / TodoItem)
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

const PRIORITY_OPTIONS = [
  { value: 0, label: 'Normal', short: '—' },
  { value: 1, label: 'High',   short: '!' },
  { value: 2, label: 'Urgent', short: '!!' },
]

interface StagedChange {
  priority?: number
  note?: string
}

interface Props {
  onClose: () => void
  onReviewed: () => void
}

type Mode = 'active' | 'focus'

export default function ReviewModal({ onClose, onReviewed }: Props) {
  const [todos, setTodos] = useState<Todo[]>([])
  const [currentIdx, setCurrentIdx] = useState(0)
  const [mode, setMode] = useState<Mode>('active')
  const [staged, setStaged] = useState<Map<number, StagedChange>>(new Map())
  const [doneIds, setDoneIds] = useState<Set<number>>(new Set())
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const noteRef = useRef<HTMLTextAreaElement>(null)

  const loadTodos = useCallback(async (m: Mode) => {
    setLoading(true)
    try {
      const data = m === 'focus' ? await getFocusedTodos() : await listTodos('active')
      setTodos(data)
      // Pre-populate staged priority from current todos
      const map = new Map<number, StagedChange>()
      data.forEach(t => map.set(t.id, { priority: t.priority }))
      setStaged(map)
      setCurrentIdx(0)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { loadTodos(mode) }, [loadTodos, mode])
  useEffect(() => {
    setTimeout(() => noteRef.current?.focus(), 80)
  }, [currentIdx])

  const todo = todos[currentIdx] ?? null
  const stagedChange = (todo ? staged.get(todo.id) : undefined) ?? {}
  const stagedPriority = stagedChange.priority ?? todo?.priority ?? 0
  const stagedNote = stagedChange.note ?? ''

  const setNote = (note: string) => {
    if (!todo) return
    setStaged(prev => {
      const next = new Map(prev)
      next.set(todo.id, { ...next.get(todo.id), note })
      return next
    })
  }

  const setPriority = (priority: number) => {
    if (!todo) return
    setStaged(prev => {
      const next = new Map(prev)
      next.set(todo.id, { ...next.get(todo.id), priority })
      return next
    })
  }

  const advance = () => setCurrentIdx(i => i + 1)

  const saveChanges = async (todoToSave: Todo, change: StagedChange) => {
    const tasks: Promise<unknown>[] = []

    // Save priority if changed
    if (change.priority !== undefined && change.priority !== todoToSave.priority) {
      tasks.push(updateTodo(todoToSave.id, { priority: change.priority }))
    }

    // Create note if text was entered
    const noteText = (change.note ?? '').trim()
    if (noteText) {
      const title = `[Todo #${todoToSave.id}] ${todoToSave.content.slice(0, 60)}`
      tasks.push(createNote(noteText, title))
    }

    await Promise.all(tasks)
  }

  const handleSaveAndNext = async () => {
    if (!todo || saving) return
    setSaving(true)
    try {
      const change = staged.get(todo.id) ?? {}
      await saveChanges(todo, change)
      onReviewed()
      advance()
    } catch (err) {
      console.error('Review save failed:', err)
    } finally {
      setSaving(false)
    }
  }

  const handleDone = async () => {
    if (!todo || saving) return
    setSaving(true)
    try {
      const change = staged.get(todo.id) ?? {}
      // Save any staged changes first, then complete
      await saveChanges(todo, change)
      await completeTodo(todo.id)
      setDoneIds(prev => new Set(prev).add(todo.id))
      onReviewed()
      advance()
    } catch (err) {
      console.error('Complete failed:', err)
    } finally {
      setSaving(false)
    }
  }

  const handleSkip = () => advance()

  const handlePrev = () => setCurrentIdx(i => Math.max(0, i - 1))

  const handleModeChange = (m: Mode) => {
    setMode(m)
    setDoneIds(new Set())
  }

  const isDone = !loading && currentIdx >= todos.length
  const total = todos.length
  const reviewedCount = doneIds.size

  return (
    <div className="review-overlay" onClick={e => { if (e.target === e.currentTarget) onClose() }}>
      <div className="review-modal">

        {/* Header */}
        <div className="review-header">
          <span className="review-title">Review Todos</span>
          <div className="review-header-right">
            {total > 0 && (
              <span className="review-progress">
                {Math.min(currentIdx + 1, total)} / {total}
                {reviewedCount > 0 && (
                  <span className="review-done-count"> · {reviewedCount} done</span>
                )}
              </span>
            )}
            <div className="review-mode-toggle">
              <button
                className={`mode-btn ${mode === 'active' ? 'active' : ''}`}
                onClick={() => handleModeChange('active')}
              >
                Active
              </button>
              <button
                className={`mode-btn ${mode === 'focus' ? 'active' : ''}`}
                onClick={() => handleModeChange('focus')}
              >
                Focus
              </button>
            </div>
            <button className="review-close" onClick={onClose} title="Close">×</button>
          </div>
        </div>

        {/* Body */}
        <div className="review-body">
          {loading ? (
            <div className="review-empty">Loading…</div>
          ) : isDone ? (
            <div className="review-done-state">
              <div className="review-done-icon">✓</div>
              <div className="review-done-text">
                {reviewedCount > 0
                  ? `Done! Completed ${reviewedCount} todo${reviewedCount !== 1 ? 's' : ''}.`
                  : 'All reviewed!'}
              </div>
              <button className="review-close-btn" onClick={onClose}>Close</button>
            </div>
          ) : todo ? (
            <>
              {/* Todo card */}
              <div className="review-card">
                <div className="review-card-meta">
                  <span className="review-card-id">#{todo.id}</span>
                  {todo.priority > 0 && (
                    <span className="review-card-priority">
                      {todo.priority === 2 ? '!!' : '!'}
                    </span>
                  )}
                  {todo.due_date && (
                    <span className="review-card-due">
                      {new Date(todo.due_date.slice(0, 10) + 'T00:00:00').toLocaleDateString(undefined, { month: 'short', day: 'numeric' })}
                    </span>
                  )}
                  {todo.labels && todo.labels.length > 0 && (
                    <span className="review-card-labels">
                      {todo.labels.map(l => (
                        <span key={l} className="review-card-label-chip" style={{ background: labelColor(l) }}>{l}</span>
                      ))}
                    </span>
                  )}
                  <button className="review-card-skip" onClick={handleSkip}>Skip →</button>
                </div>
                <div className="review-card-content">{todo.content}</div>
              </div>

              {/* Note textarea */}
              <div className="review-section">
                <label className="review-section-label">Note</label>
                <textarea
                  ref={noteRef}
                  className="review-note"
                  placeholder="Add a note, context, or follow-up…"
                  value={stagedNote}
                  onChange={e => setNote(e.target.value)}
                  rows={3}
                  onKeyDown={e => {
                    if (e.key === 'Escape') onClose()
                    // Ctrl/Cmd+Enter → Save & Next
                    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
                      e.preventDefault()
                      handleSaveAndNext()
                    }
                  }}
                />
              </div>

              {/* Priority */}
              <div className="review-section review-section--row">
                <span className="review-section-label">Priority</span>
                <div className="review-priority-btns">
                  {PRIORITY_OPTIONS.map(opt => (
                    <button
                      key={opt.value}
                      className={`review-priority-btn ${stagedPriority === opt.value ? 'active' : ''} priority-${opt.value}`}
                      onClick={() => setPriority(opt.value)}
                    >
                      {opt.label}
                    </button>
                  ))}
                </div>
              </div>

              {/* Navigation */}
              <div className="review-nav">
                <button
                  className="review-nav-btn"
                  onClick={handlePrev}
                  disabled={currentIdx === 0}
                >
                  ← Prev
                </button>
                <div className="review-nav-right">
                  <button
                    className="review-done-btn"
                    onClick={handleDone}
                    disabled={saving}
                    title="Mark complete and advance"
                  >
                    Done ✓
                  </button>
                  <button
                    className="review-save-btn"
                    onClick={handleSaveAndNext}
                    disabled={saving}
                    title="Save changes and advance (⌘↵)"
                  >
                    {saving ? '…' : 'Save & Next →'}
                  </button>
                </div>
              </div>
            </>
          ) : (
            <div className="review-empty">
              {mode === 'focus' ? 'No focused todos.' : 'No active todos.'}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
