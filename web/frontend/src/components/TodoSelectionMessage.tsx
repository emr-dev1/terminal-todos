import { useState } from 'react'
import type { ExtractedTodoItem } from '../types'
import './TodoSelectionMessage.css'

const PRIORITY_LABEL: Record<number, string> = { 1: '!', 2: '!!' }
const PRIORITY_CLASS: Record<number, string> = { 1: 'priority-medium', 2: 'priority-high' }
const NOTE_TYPE_ICON: Record<string, string> = {
  meeting: '🗓',
  brainstorm: '💡',
  project: '📁',
  general: '📝',
}

interface Props {
  todos: ExtractedTodoItem[]
  title: string
  noteType: string
  submitted: boolean
  addedCount: number
  submittedLabel?: string
  availableLabels: string[]
  onSubmit: (selected: ExtractedTodoItem[], label: string) => void
}

export default function TodoSelectionMessage({
  todos,
  title,
  noteType,
  submitted,
  addedCount,
  submittedLabel,
  availableLabels,
  onSubmit,
}: Props) {
  const [checked, setChecked] = useState<Set<number>>(() => new Set(todos.map((_, i) => i)))
  const [submitting, setSubmitting] = useState(false)
  const [label, setLabel] = useState('')
  const [dropdownOpen, setDropdownOpen] = useState(false)

  const selectedCount = checked.size

  const filteredLabels = label.trim()
    ? availableLabels.filter(l => l.toLowerCase().includes(label.toLowerCase()))
    : availableLabels

  const showCreate =
    label.trim() !== '' &&
    !availableLabels.some(l => l.toLowerCase() === label.trim().toLowerCase())

  const pickLabel = (l: string) => {
    setLabel(l)
    setDropdownOpen(false)
  }

  const toggle = (idx: number) => {
    setChecked(prev => {
      const next = new Set(prev)
      next.has(idx) ? next.delete(idx) : next.add(idx)
      return next
    })
  }

  const selectAll = () => setChecked(new Set(todos.map((_, i) => i)))
  const selectNone = () => setChecked(new Set())

  const handleSubmit = async () => {
    if (selectedCount === 0 || submitting) return
    setSubmitting(true)
    const selected = todos.filter((_, i) => checked.has(i))
    onSubmit(selected, label.trim())
  }

  const icon = NOTE_TYPE_ICON[noteType] ?? '📝'

  // ---- Submitted state ----
  if (submitted) {
    return (
      <div className="tsm tsm--submitted">
        <span className="tsm-submitted-icon">✓</span>
        <span className="tsm-submitted-text">
          Added <strong>{addedCount}</strong> todo{addedCount !== 1 ? 's' : ''} to your list
          {submittedLabel && <span className="tsm-submitted-label"> · labeled <strong>{submittedLabel}</strong></span>}
        </span>
      </div>
    )
  }

  // ---- No todos found ----
  if (todos.length === 0) {
    return (
      <div className="tsm tsm--empty">
        <span className="tsm-empty-icon">🔍</span>
        <span className="tsm-empty-text">No action items found in these notes.</span>
        <span className="tsm-empty-hint">Try the "Summarize &amp; discuss" option instead.</span>
      </div>
    )
  }

  return (
    <div className="tsm">
      {/* Header */}
      <div className="tsm-header">
        <span className="tsm-icon">{icon}</span>
        <div className="tsm-header-text">
          <span className="tsm-title">{title}</span>
          <span className="tsm-subtitle">Found {todos.length} action item{todos.length !== 1 ? 's' : ''} — select the ones you want to add</span>
        </div>
      </div>

      {/* Select all / none */}
      <div className="tsm-controls">
        <button className="tsm-control-btn" onClick={selectAll} disabled={selectedCount === todos.length}>
          Select all
        </button>
        <span className="tsm-control-sep">·</span>
        <button className="tsm-control-btn" onClick={selectNone} disabled={selectedCount === 0}>
          Select none
        </button>
        <span className="tsm-control-count">{selectedCount} of {todos.length} selected</span>
      </div>

      {/* Todo rows */}
      <div className="tsm-list">
        {todos.map((todo, idx) => (
          <label key={idx} className={`tsm-row ${checked.has(idx) ? 'tsm-row--checked' : ''}`}>
            <input
              type="checkbox"
              className="tsm-checkbox"
              checked={checked.has(idx)}
              onChange={() => toggle(idx)}
            />
            <span className="tsm-row-content">{todo.content}</span>
            {todo.priority > 0 && (
              <span className={`tsm-priority ${PRIORITY_CLASS[todo.priority] ?? ''}`}>
                {PRIORITY_LABEL[todo.priority]}
              </span>
            )}
          </label>
        ))}
      </div>

      {/* Label picker */}
      {selectedCount > 0 && (
        <div className="tsm-label-section">
          <span className="tsm-label-heading">Label todos <span className="tsm-label-optional">(optional)</span></span>
          <div className="tsm-label-combobox">
            <input
              className="tsm-label-input"
              placeholder="Search or create a label…"
              value={label}
              onChange={e => { setLabel(e.target.value); setDropdownOpen(e.target.value.length > 0) }}
              onBlur={() => setTimeout(() => setDropdownOpen(false), 150)}
              onKeyDown={e => {
                if (e.key === 'Escape') { setDropdownOpen(false) }
                if (e.key === 'Enter') {
                  e.preventDefault()
                  if (dropdownOpen && filteredLabels.length > 0) pickLabel(filteredLabels[0])
                  else setDropdownOpen(false)
                }
              }}
            />
            {dropdownOpen && (filteredLabels.length > 0 || showCreate) && (
              <div className="tsm-label-dropdown">
                {filteredLabels.map(l => (
                  <button
                    key={l}
                    className={`tsm-label-dropdown-item${label === l ? ' tsm-label-dropdown-item--selected' : ''}`}
                    onMouseDown={() => pickLabel(l)}
                    type="button"
                  >
                    {l}
                  </button>
                ))}
                {showCreate && (
                  <button
                    className="tsm-label-dropdown-item tsm-label-dropdown-create"
                    onMouseDown={() => setDropdownOpen(false)}
                    type="button"
                  >
                    + Create &ldquo;{label.trim()}&rdquo;
                  </button>
                )}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Submit */}
      {selectedCount > 0 && (
        <div className="tsm-footer">
          <button
            className="tsm-submit-btn"
            onClick={handleSubmit}
            disabled={submitting}
          >
            {submitting
              ? 'Adding…'
              : `Add ${selectedCount} todo${selectedCount !== 1 ? 's' : ''}${label.trim() ? ` · ${label.trim()}` : ''} →`}
          </button>
        </div>
      )}
    </div>
  )
}
