import { useState, useRef, useEffect } from 'react'
import { createTodo } from '../api/todos'
import './CreateTodoModal.css'

interface Props {
  onClose: () => void
  onCreated: (id: number) => void
}

export default function CreateTodoModal({ onClose, onCreated }: Props) {
  const [content, setContent] = useState('')
  const [priority, setPriority] = useState(0)
  const [dueDate, setDueDate] = useState('')
  const [saving, setSaving] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    setTimeout(() => inputRef.current?.focus(), 50)
  }, [])

  const handleCreate = async () => {
    const trimmed = content.trim()
    if (!trimmed || saving) return
    setSaving(true)
    try {
      const todo = await createTodo(trimmed, priority, dueDate || undefined)
      onCreated(todo.id)
      onClose()
    } catch (err) {
      console.error('Failed to create todo:', err)
      setSaving(false)
    }
  }

  return (
    <div className="create-todo-overlay" onClick={e => { if (e.target === e.currentTarget) onClose() }}>
      <div className="create-todo-modal">
        <div className="create-todo-header">
          <span className="create-todo-title">New Todo</span>
          <button className="create-todo-close" onClick={onClose} title="Close">×</button>
        </div>

        <div className="create-todo-body">
          <input
            ref={inputRef}
            className="create-todo-input"
            placeholder="What needs to be done? Use #tags to label"
            value={content}
            onChange={e => setContent(e.target.value)}
            onKeyDown={e => {
              if (e.key === 'Enter') handleCreate()
              if (e.key === 'Escape') onClose()
            }}
          />

          <div className="create-todo-row">
            <div className="create-todo-field">
              <label className="create-todo-label">Priority</label>
              <select
                className="create-todo-select"
                value={priority}
                onChange={e => setPriority(Number(e.target.value))}
              >
                <option value={0}>Normal</option>
                <option value={1}>Medium !</option>
                <option value={2}>High !!</option>
              </select>
            </div>

            <div className="create-todo-field create-todo-field--grow">
              <label className="create-todo-label">Due date</label>
              <input
                type="date"
                className="create-todo-date"
                value={dueDate}
                onChange={e => setDueDate(e.target.value)}
              />
            </div>
          </div>
        </div>

        <div className="create-todo-footer">
          <button className="create-todo-cancel" onClick={onClose}>Cancel</button>
          <button
            className="create-todo-submit"
            onClick={handleCreate}
            disabled={!content.trim() || saving}
          >
            {saving ? '…' : 'Add Todo'}
          </button>
        </div>
      </div>
    </div>
  )
}
