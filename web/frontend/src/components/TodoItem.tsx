import { useState } from 'react'
import type { Todo } from '../types'
import './TodoItem.css'

// Deterministic color palette for labels
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
  todo: Todo
  isNew?: boolean
  onComplete: (id: number) => void
  onUncomplete: (id: number) => void
  onDelete: (id: number) => void
  onToggleFocus: (todo: Todo) => void
  onSendToChat: (todo: Todo) => void
}

const PRIORITY_LABELS = ['', '!', '!!']
const PRIORITY_CLASSES = ['', 'priority-medium', 'priority-high']

export default function TodoItem({ todo, isNew, onComplete, onUncomplete, onDelete, onToggleFocus, onSendToChat }: Props) {
  const [confirming, setConfirming] = useState(false)

  const handleDelete = () => {
    if (confirming) {
      onDelete(todo.id)
      setConfirming(false)
    } else {
      setConfirming(true)
      setTimeout(() => setConfirming(false), 2500)
    }
  }

  // due_date arrives as an ISO string that may already contain a time component
  // (e.g. "2025-01-15T00:00:00"). Strip to the date part before parsing so we
  // never produce "…T00:00:00T00:00:00" → Invalid Date.
  const dueDateObj = todo.due_date
    ? new Date(todo.due_date.slice(0, 10) + 'T00:00:00')
    : null

  const dueDateStr = dueDateObj
    ? dueDateObj.toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
    : null

  const isOverdue = dueDateObj && !todo.completed
    ? dueDateObj < new Date(new Date().toDateString())
    : false

  return (
    <div className={`todo-item ${todo.completed ? 'todo-completed' : ''} ${todo.focus_order !== null ? 'todo-focused' : ''} ${isNew ? 'todo-item--new' : ''}`}>
      <button
        className={`todo-check ${todo.completed ? 'checked' : ''}`}
        onClick={() => todo.completed ? onUncomplete(todo.id) : onComplete(todo.id)}
        title={todo.completed ? 'Mark active' : 'Mark complete'}
      >
        {todo.completed ? '✓' : '○'}
      </button>

      <div className="todo-body">
        <span className="todo-content">{todo.content}</span>
        <div className="todo-meta">
          {todo.priority > 0 && (
            <span className={`todo-priority ${PRIORITY_CLASSES[todo.priority]}`}>
              {PRIORITY_LABELS[todo.priority]}
            </span>
          )}
          {dueDateStr && (
            <span className={`todo-due ${isOverdue ? 'overdue' : ''}`}>
              {isOverdue ? '⚠ ' : ''}{dueDateStr}
            </span>
          )}
          {todo.focus_order !== null && (
            <span className="todo-focus-badge">focus</span>
          )}
          {todo.labels && todo.labels.length > 0 && (
            <span className="todo-labels-inline">
              {todo.labels.map(label => (
                <span
                  key={label}
                  className="todo-label-chip"
                  style={{ background: labelColor(label) }}
                >
                  {label}
                </span>
              ))}
            </span>
          )}
        </div>
      </div>

      <div className="todo-actions">
        <button
          className="todo-action-btn chat-btn"
          onClick={() => onSendToChat(todo)}
          title="Bring into chat context"
        >
          ↗
        </button>
        <button
          className={`todo-action-btn ${todo.focus_order !== null ? 'active' : ''}`}
          onClick={() => onToggleFocus(todo)}
          title={todo.focus_order !== null ? 'Remove from focus' : 'Add to focus'}
        >
          ⊕
        </button>
        <button
          className={`todo-action-btn danger ${confirming ? 'confirming' : ''}`}
          onClick={handleDelete}
          title={confirming ? 'Click again to confirm delete' : 'Delete todo'}
        >
          {confirming ? '?' : '×'}
        </button>
      </div>
    </div>
  )
}
