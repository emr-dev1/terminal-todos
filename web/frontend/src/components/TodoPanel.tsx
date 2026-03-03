import { useState, useEffect, useCallback, useMemo, useRef } from 'react'
import type { Todo, TodoStats } from '../types'
import * as api from '../api/todos'
import TodoItem from './TodoItem'
import LabelModal from './LabelModal'
import ReviewModal from './ReviewModal'
import CreateTodoModal from './CreateTodoModal'
import './TodoPanel.css'

// Deterministic color for label chips (must match TodoItem.tsx)
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

type FilterTab = 'active' | 'completed' | 'all' | 'focus'

interface Props {
  onRegisterRefresh: (fn: () => void) => void
  collapsed: boolean
  onToggleCollapse: () => void
  onSendToChat: (todo: Todo) => void
}

function parseTags(content: string): string[] {
  return (content.match(/#[\w-]+/g) ?? []).map(t => t.slice(1).toLowerCase())
}

export default function TodoPanel({ onRegisterRefresh, collapsed, onToggleCollapse, onSendToChat }: Props) {
  const [todos, setTodos] = useState<Todo[]>([])
  const [stats, setStats] = useState<TodoStats>({ active: 0, completed: 0, total: 0 })
  const [tab, setTab] = useState<FilterTab>('active')
  const [loading, setLoading] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [activeTags, setActiveTags] = useState<Set<string>>(new Set())
  const [activeLabels, setActiveLabels] = useState<Set<string>>(new Set())
  const [availableLabels, setAvailableLabels] = useState<string[]>([])
  const [showLabelModal, setShowLabelModal] = useState(false)
  const [showReviewModal, setShowReviewModal] = useState(false)
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [newestTodoId, setNewestTodoId] = useState<number | null>(null)
  const newestTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  // Tracks IDs seen during active-tab fetches so we can detect chat-created todos
  const seenActiveIdsRef = useRef<Set<number>>(new Set())
  const activeFetchCountRef = useRef(0)

  const fetchLabels = useCallback(async () => {
    try {
      const labels = await api.getLabels()
      setAvailableLabels(labels)
    } catch { /* non-critical */ }
  }, [])

  const highlightNew = useCallback((id: number) => {
    setNewestTodoId(id)
    setTab('active')
    if (newestTimerRef.current) clearTimeout(newestTimerRef.current)
    newestTimerRef.current = setTimeout(() => setNewestTodoId(null), 4000)
  }, [])

  const fetchTodos = useCallback(async () => {
    setLoading(true)
    try {
      let data: Todo[]
      if (tab === 'focus') {
        data = await api.getFocusedTodos()
      } else {
        data = await api.listTodos(tab === 'all' ? 'all' : tab)
      }

      // Detect chat-created todos: find an ID in the new active list we haven't seen before
      if (tab === 'active') {
        activeFetchCountRef.current += 1
        if (activeFetchCountRef.current > 1) {
          const newTodo = data.find(t => !seenActiveIdsRef.current.has(t.id))
          if (newTodo) highlightNew(newTodo.id)
        }
        data.forEach(t => seenActiveIdsRef.current.add(t.id))
      }

      setTodos(data)
      const s = await api.getTodoStats()
      setStats(s)
      // Refresh available labels too so filter chips stay current
      fetchLabels()
    } catch (err) {
      console.error('Failed to fetch todos:', err)
    } finally {
      setLoading(false)
    }
  }, [tab, fetchLabels, highlightNew])

  useEffect(() => { fetchTodos() }, [fetchTodos])
  useEffect(() => { onRegisterRefresh(fetchTodos) }, [fetchTodos, onRegisterRefresh])

  // Derive all unique hashtags from the current todo list
  const allTags = useMemo(() => {
    const tagSet = new Set<string>()
    todos.forEach(t => parseTags(t.content).forEach(tag => tagSet.add(tag)))
    return [...tagSet].sort()
  }, [todos])

  // Client-side filter: search query + selected hashtags + selected labels
  const filteredTodos = useMemo(() => {
    const filtered = todos.filter(todo => {
      const q = searchQuery.trim().toLowerCase()
      const matchesSearch = !q || todo.content.toLowerCase().includes(q)
      const todoTags = parseTags(todo.content)
      const matchesTags = activeTags.size === 0 || [...activeTags].every(t => todoTags.includes(t))
      // Label filter: OR logic — show todo if it has ANY selected label
      const todoLabels = todo.labels ?? []
      const matchesLabels = activeLabels.size === 0 || [...activeLabels].some(l => todoLabels.includes(l))
      return matchesSearch && matchesTags && matchesLabels
    })
    // Sort by creation date descending so newest todos always appear at the top
    filtered.sort((a, b) => {
      const aTime = a.created_at ? new Date(a.created_at).getTime() : 0
      const bTime = b.created_at ? new Date(b.created_at).getTime() : 0
      return bTime - aTime
    })
    return filtered
  }, [todos, searchQuery, activeTags, activeLabels])

  const toggleTag = (tag: string) => {
    setActiveTags(prev => {
      const next = new Set(prev)
      next.has(tag) ? next.delete(tag) : next.add(tag)
      return next
    })
  }

  const toggleLabel = (label: string) => {
    setActiveLabels(prev => {
      const next = new Set(prev)
      next.has(label) ? next.delete(label) : next.add(label)
      return next
    })
  }

  const handleComplete = async (id: number) => {
    try { await api.completeTodo(id); await fetchTodos() } catch (err) { console.error(err) }
  }
  const handleUncomplete = async (id: number) => {
    try { await api.uncompleteTodo(id); await fetchTodos() } catch (err) { console.error(err) }
  }
  const handleDelete = async (id: number) => {
    try { await api.deleteTodo(id); await fetchTodos() } catch (err) { console.error(err) }
  }
  const handleToggleFocus = async (todo: Todo) => {
    try {
      todo.focus_order !== null ? await api.removeFromFocus(todo.id) : await api.addToFocus(todo.id)
      await fetchTodos()
    } catch (err) { console.error(err) }
  }

  const TABS: { key: FilterTab; label: string }[] = [
    { key: 'active', label: 'Active' },
    { key: 'completed', label: 'Done' },
    { key: 'focus', label: 'Focus' },
    { key: 'all', label: 'All' },
  ]

  const isFiltering = searchQuery || activeTags.size > 0 || activeLabels.size > 0

  // ---- Collapsed state: just show a vertical strip ----
  if (collapsed) {
    return (
      <div className="todo-panel todo-panel--collapsed">
        <button className="collapse-toggle collapse-toggle--closed" onClick={onToggleCollapse} title="Expand todos panel">
          <span className="collapse-icon">›</span>
          <span className="collapse-label">Todos</span>
          {stats.active > 0 && <span className="collapse-badge">{stats.active}</span>}
        </button>
      </div>
    )
  }

  return (
    <div className="todo-panel">
      {/* Header row: tabs + collapse + new + quick-label */}
      <div className="todo-panel-header">
        <button className="collapse-btn" onClick={onToggleCollapse} title="Collapse panel">‹</button>
        <div className="todo-tabs">
          {TABS.map(t => (
            <button
              key={t.key}
              className={`todo-tab ${tab === t.key ? 'active' : ''}`}
              onClick={() => setTab(t.key)}
            >
              {t.label}
              {t.key === 'active' && stats.active > 0 && (
                <span className="tab-badge">{stats.active}</span>
              )}
            </button>
          ))}
        </div>
        <div className="header-actions">
          <button
            className="review-todos-btn"
            onClick={() => setShowReviewModal(true)}
            title="Review todos"
          >
            ▷
          </button>
          <button
            className="quick-label-btn"
            onClick={() => setShowLabelModal(true)}
            title="Quick label todos"
          >
            ⊞
          </button>
          <button
            className="new-todo-btn"
            onClick={() => setShowCreateModal(true)}
            title="New todo"
          >
            +
          </button>
        </div>
      </div>

      {/* Search bar */}
      <div className="search-bar">
        <span className="search-icon">⌕</span>
        <input
          className="search-input"
          placeholder="Search todos…"
          value={searchQuery}
          onChange={e => setSearchQuery(e.target.value)}
        />
        {searchQuery && (
          <button className="search-clear" onClick={() => setSearchQuery('')} title="Clear search">×</button>
        )}
      </div>

      {/* Label filter chips */}
      {availableLabels.length > 0 && (
        <div className="label-filter">
          {activeLabels.size > 0 && (
            <button className="tag-clear-all" onClick={() => setActiveLabels(new Set())}>
              clear
            </button>
          )}
          {availableLabels.map(label => (
            <button
              key={label}
              className={`label-filter-chip ${activeLabels.has(label) ? 'active' : ''}`}
              style={activeLabels.has(label) ? { background: labelColor(label), borderColor: labelColor(label) } : {}}
              onClick={() => toggleLabel(label)}
            >
              {label}
            </button>
          ))}
        </div>
      )}

      {/* Hashtag cloud */}
      {allTags.length > 0 && (
        <div className="tag-cloud">
          {activeTags.size > 0 && (
            <button className="tag-clear-all" onClick={() => setActiveTags(new Set())}>
              clear
            </button>
          )}
          {allTags.map(tag => (
            <button
              key={tag}
              className={`tag-chip ${activeTags.has(tag) ? 'active' : ''}`}
              onClick={() => toggleTag(tag)}
            >
              #{tag}
            </button>
          ))}
        </div>
      )}

      {/* Todo list */}
      <div className="todo-list-scroll">
        {loading && todos.length === 0 ? (
          <div className="todo-list-empty">Loading…</div>
        ) : filteredTodos.length === 0 ? (
          <div className="todo-list-empty">
            {isFiltering
              ? 'No todos match your filter'
              : tab === 'focus' ? 'No focused todos'
              : tab === 'completed' ? 'Nothing completed yet'
              : 'All clear!'}
          </div>
        ) : (
          <div className="todo-list">
            {filteredTodos.map(todo => (
              <TodoItem
                key={todo.id}
                todo={todo}
                isNew={todo.id === newestTodoId}
                onComplete={handleComplete}
                onUncomplete={handleUncomplete}
                onDelete={handleDelete}
                onToggleFocus={handleToggleFocus}
                onSendToChat={onSendToChat}
              />
            ))}
          </div>
        )}
      </div>

      {/* Stats footer */}
      <div className="todo-stats">
        {isFiltering && (
          <span className="stats-filtered">{filteredTodos.length} shown ·&nbsp;</span>
        )}
        <span>{stats.active} active</span>
        <span className="stats-sep">·</span>
        <span>{stats.completed} done</span>
        <span className="stats-sep">·</span>
        <span>{stats.total} total</span>
      </div>

      {/* Create todo modal */}
      {showCreateModal && (
        <CreateTodoModal
          onClose={() => setShowCreateModal(false)}
          onCreated={(id) => { highlightNew(id); fetchTodos() }}
        />
      )}

      {/* Review modal */}
      {showReviewModal && (
        <ReviewModal
          onClose={() => setShowReviewModal(false)}
          onReviewed={fetchTodos}
        />
      )}

      {/* Quick label modal */}
      {showLabelModal && (
        <LabelModal
          availableLabels={availableLabels}
          onClose={() => setShowLabelModal(false)}
          onLabeled={fetchTodos}
        />
      )}
    </div>
  )
}
