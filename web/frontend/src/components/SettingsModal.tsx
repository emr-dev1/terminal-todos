import { useState, useEffect, useCallback } from 'react'
import {
  getSettings, updateSettings, getSettingsLabels, createLabel, renameLabel, deleteLabel,
  type AppSettings, type UpdateSettingsPayload,
} from '../api/settings'
import './SettingsModal.css'

type Tab = 'general' | 'model' | 'labels' | 'observability'

const LLM_MODELS = [
  'gpt-4o',
  'gpt-4o-mini',
  'gpt-4-turbo',
  'gpt-4',
  'gpt-3.5-turbo',
]

interface Props {
  onClose: () => void
}

export default function SettingsModal({ onClose }: Props) {
  const [tab, setTab] = useState<Tab>('general')
  const [settings, setSettings] = useState<AppSettings | null>(null)
  const [labels, setLabels] = useState<string[]>([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Editable form state
  const [userName, setUserName] = useState('')
  const [maxTodos, setMaxTodos] = useState(100)
  const [searchLimit, setSearchLimit] = useState(10)
  const [verboseLogging, setVerboseLogging] = useState(false)
  const [llmModel, setLlmModel] = useState('gpt-4o')
  const [customModel, setCustomModel] = useState('')
  const [embeddingModel, setEmbeddingModel] = useState('')
  const [openaiKey, setOpenaiKey] = useState('')
  const [changeOpenaiKey, setChangeOpenaiKey] = useState(false)
  const [enableArize, setEnableArize] = useState(false)
  const [arizeSpaceId, setArizeSpaceId] = useState('')
  const [arizeKey, setArizeKey] = useState('')
  const [changeArizeKey, setChangeArizeKey] = useState(false)
  const [arizeProject, setArizeProject] = useState('')

  // Label editing state
  const [renamingLabel, setRenamingLabel] = useState<string | null>(null)
  const [renameValue, setRenameValue] = useState('')
  const [labelBusy, setLabelBusy] = useState(false)
  const [newLabelValue, setNewLabelValue] = useState('')

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const [s, l] = await Promise.all([getSettings(), getSettingsLabels()])
      setSettings(s)
      setLabels(l)
      setUserName(s.user_name)
      setMaxTodos(s.max_todos_display)
      setSearchLimit(s.search_results_limit)
      setVerboseLogging(s.verbose_logging)
      setEmbeddingModel(s.embedding_model)
      setEnableArize(s.enable_arize_tracing)
      setArizeSpaceId(s.arize_space_id ?? '')
      setArizeProject(s.arize_project_name)
      if (LLM_MODELS.includes(s.llm_model)) {
        setLlmModel(s.llm_model)
        setCustomModel('')
      } else {
        setLlmModel('__custom__')
        setCustomModel(s.llm_model)
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load settings')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  const handleSave = async () => {
    setSaving(true)
    setError(null)
    try {
      const payload: UpdateSettingsPayload = {
        user_name: userName,
        max_todos_display: maxTodos,
        search_results_limit: searchLimit,
        verbose_logging: verboseLogging,
        llm_model: llmModel === '__custom__' ? customModel : llmModel,
        embedding_model: embeddingModel,
        enable_arize_tracing: enableArize,
        arize_space_id: arizeSpaceId || null,
        arize_project_name: arizeProject,
      }
      if (changeOpenaiKey && openaiKey.trim()) {
        payload.openai_api_key = openaiKey.trim()
      }
      if (changeArizeKey && arizeKey.trim()) {
        payload.arize_api_key = arizeKey.trim()
      }
      await updateSettings(payload)
      setSaved(true)
      setChangeOpenaiKey(false)
      setOpenaiKey('')
      setChangeArizeKey(false)
      setArizeKey('')
      await load()
      setTimeout(() => setSaved(false), 2500)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Save failed')
    } finally {
      setSaving(false)
    }
  }

  const handleRenameStart = (label: string) => {
    setRenamingLabel(label)
    setRenameValue(label)
  }

  const handleRenameConfirm = async () => {
    if (!renamingLabel || !renameValue.trim() || renameValue === renamingLabel) {
      setRenamingLabel(null)
      return
    }
    setLabelBusy(true)
    try {
      await renameLabel(renamingLabel, renameValue.trim())
      await load()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Rename failed')
    } finally {
      setLabelBusy(false)
      setRenamingLabel(null)
    }
  }

  const handleDelete = async (label: string) => {
    if (!window.confirm(`Remove label "${label}" from all todos?`)) return
    setLabelBusy(true)
    try {
      await deleteLabel(label)
      await load()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Delete failed')
    } finally {
      setLabelBusy(false)
    }
  }

  const handleCreateLabel = async () => {
    const val = newLabelValue.trim()
    if (!val) return
    setLabelBusy(true)
    try {
      await createLabel(val)
      setNewLabelValue('')
      await load()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Create failed')
    } finally {
      setLabelBusy(false)
    }
  }

  const TABS: { key: Tab; label: string }[] = [
    { key: 'general', label: 'General' },
    { key: 'model', label: 'API & Model' },
    { key: 'labels', label: 'Labels' },
    { key: 'observability', label: 'Observability' },
  ]

  return (
    <div className="settings-overlay" onClick={e => { if (e.target === e.currentTarget) onClose() }}>
      <div className="settings-modal">

        {/* Header */}
        <div className="settings-header">
          <span className="settings-title">⚙ Settings</span>
          <button className="settings-close" onClick={onClose} title="Close">×</button>
        </div>

        {loading ? (
          <div className="settings-loading">Loading…</div>
        ) : (
          <div className="settings-body">

            {/* Sidebar tabs */}
            <nav className="settings-nav">
              {TABS.map(t => (
                <button
                  key={t.key}
                  className={`settings-nav-btn ${tab === t.key ? 'active' : ''}`}
                  onClick={() => setTab(t.key)}
                >
                  {t.label}
                </button>
              ))}
            </nav>

            {/* Content pane */}
            <div className="settings-pane">

              {error && (
                <div className="settings-error">{error}</div>
              )}

              {/* ---- General ---- */}
              {tab === 'general' && (
                <div className="settings-section">
                  <h3 className="settings-section-title">General</h3>

                  <label className="settings-field">
                    <span className="settings-label">Your name</span>
                    <span className="settings-hint">Used to filter your own name from captured notes</span>
                    <input
                      className="settings-input"
                      value={userName}
                      onChange={e => setUserName(e.target.value)}
                    />
                  </label>

                  <label className="settings-field">
                    <span className="settings-label">Max todos displayed</span>
                    <input
                      type="number"
                      className="settings-input settings-input--short"
                      value={maxTodos}
                      min={10}
                      max={1000}
                      onChange={e => setMaxTodos(Number(e.target.value))}
                    />
                  </label>

                  <label className="settings-field">
                    <span className="settings-label">Search results limit</span>
                    <input
                      type="number"
                      className="settings-input settings-input--short"
                      value={searchLimit}
                      min={1}
                      max={100}
                      onChange={e => setSearchLimit(Number(e.target.value))}
                    />
                  </label>

                  <label className="settings-field settings-field--row">
                    <input
                      type="checkbox"
                      checked={verboseLogging}
                      onChange={e => setVerboseLogging(e.target.checked)}
                    />
                    <span className="settings-label">Verbose logging</span>
                  </label>

                  <div className="settings-field">
                    <span className="settings-label">Data directory</span>
                    <span className="settings-hint">Read-only — change via DATA_DIR env var and restart</span>
                    <code className="settings-code">{settings?.data_dir}</code>
                  </div>

                  <div className="settings-field">
                    <span className="settings-label">Database</span>
                    <code className="settings-code">{settings?.db_path}</code>
                  </div>

                  <div className="settings-field">
                    <span className="settings-label">Config file</span>
                    <code className="settings-code">{settings?.env_path}</code>
                  </div>

                  <div className="settings-actions">
                    <button className="settings-save-btn" onClick={handleSave} disabled={saving}>
                      {saving ? 'Saving…' : saved ? '✓ Saved' : 'Save Settings'}
                    </button>
                  </div>
                </div>
              )}

              {/* ---- API & Model ---- */}
              {tab === 'model' && (
                <div className="settings-section">
                  <h3 className="settings-section-title">API Keys & Model</h3>

                  <div className="settings-field">
                    <span className="settings-label">OpenAI API Key</span>
                    {!changeOpenaiKey ? (
                      <div className="settings-key-row">
                        <code className="settings-code settings-code--key">
                          {settings?.openai_api_key_set
                            ? settings.openai_api_key_preview
                            : <span className="settings-unset">Not set</span>}
                        </code>
                        <button
                          className="settings-change-btn"
                          onClick={() => setChangeOpenaiKey(true)}
                        >
                          {settings?.openai_api_key_set ? 'Change' : 'Set key'}
                        </button>
                      </div>
                    ) : (
                      <div className="settings-key-row">
                        <input
                          type="password"
                          className="settings-input settings-input--key"
                          placeholder="sk-..."
                          value={openaiKey}
                          onChange={e => setOpenaiKey(e.target.value)}
                          autoFocus
                        />
                        <button className="settings-change-btn" onClick={() => { setChangeOpenaiKey(false); setOpenaiKey('') }}>
                          Cancel
                        </button>
                      </div>
                    )}
                    <span className="settings-hint">Required for AI features. Changes take effect after server restart.</span>
                  </div>

                  <div className="settings-field">
                    <span className="settings-label">LLM Model</span>
                    <span className="settings-hint">Model used for the AI agent and todo extraction</span>
                    <select
                      className="settings-select"
                      value={llmModel}
                      onChange={e => setLlmModel(e.target.value)}
                    >
                      {LLM_MODELS.map(m => (
                        <option key={m} value={m}>{m}</option>
                      ))}
                      <option value="__custom__">Custom…</option>
                    </select>
                    {llmModel === '__custom__' && (
                      <input
                        className="settings-input"
                        placeholder="e.g. gpt-4o-2024-11-20"
                        value={customModel}
                        onChange={e => setCustomModel(e.target.value)}
                        style={{ marginTop: 6 }}
                      />
                    )}
                  </div>

                  <div className="settings-field">
                    <span className="settings-label">Embedding Model</span>
                    <span className="settings-hint">Sentence-transformers model used for semantic search</span>
                    <input
                      className="settings-input"
                      value={embeddingModel}
                      onChange={e => setEmbeddingModel(e.target.value)}
                    />
                  </div>

                  <div className="settings-actions">
                    <button className="settings-save-btn" onClick={handleSave} disabled={saving}>
                      {saving ? 'Saving…' : saved ? '✓ Saved' : 'Save Settings'}
                    </button>
                  </div>
                </div>
              )}

              {/* ---- Labels ---- */}
              {tab === 'labels' && (
                <div className="settings-section">
                  <h3 className="settings-section-title">Label Management</h3>
                  <p className="settings-desc">
                    Labels are applied to todos. Rename or delete a label to update all todos that use it.
                  </p>

                  {labels.length === 0 ? (
                    <div className="settings-empty">No labels yet. Add one below.</div>
                  ) : (
                    <div className="settings-label-list">
                      {labels.map(label => (
                        <div key={label} className="settings-label-row">
                          {renamingLabel === label ? (
                            <>
                              <input
                                className="settings-input settings-label-rename-input"
                                value={renameValue}
                                onChange={e => setRenameValue(e.target.value)}
                                onKeyDown={e => {
                                  if (e.key === 'Enter') handleRenameConfirm()
                                  if (e.key === 'Escape') setRenamingLabel(null)
                                }}
                                autoFocus
                              />
                              <button
                                className="settings-label-action settings-label-action--save"
                                onClick={handleRenameConfirm}
                                disabled={labelBusy}
                              >
                                Save
                              </button>
                              <button
                                className="settings-label-action"
                                onClick={() => setRenamingLabel(null)}
                              >
                                Cancel
                              </button>
                            </>
                          ) : (
                            <>
                              <span className="settings-label-chip">{label}</span>
                              <div className="settings-label-actions">
                                <button
                                  className="settings-label-action"
                                  onClick={() => handleRenameStart(label)}
                                  disabled={labelBusy}
                                >
                                  Rename
                                </button>
                                <button
                                  className="settings-label-action settings-label-action--danger"
                                  onClick={() => handleDelete(label)}
                                  disabled={labelBusy}
                                >
                                  Delete
                                </button>
                              </div>
                            </>
                          )}
                        </div>
                      ))}
                    </div>
                  )}

                  <div className="settings-label-add-row">
                    <input
                      className="settings-input settings-label-add-input"
                      placeholder="New label name…"
                      value={newLabelValue}
                      onChange={e => setNewLabelValue(e.target.value)}
                      onKeyDown={e => { if (e.key === 'Enter') handleCreateLabel() }}
                      disabled={labelBusy}
                    />
                    <button
                      className="settings-label-add-btn"
                      onClick={handleCreateLabel}
                      disabled={labelBusy || !newLabelValue.trim()}
                    >
                      Add
                    </button>
                  </div>
                </div>
              )}

              {/* ---- Observability ---- */}
              {tab === 'observability' && (
                <div className="settings-section">
                  <h3 className="settings-section-title">Observability (Arize)</h3>
                  <p className="settings-desc">
                    Enable Arize tracing to monitor and debug AI agent behaviour.
                    Changes take effect after server restart.
                  </p>

                  <label className="settings-field settings-field--row">
                    <input
                      type="checkbox"
                      checked={enableArize}
                      onChange={e => setEnableArize(e.target.checked)}
                    />
                    <span className="settings-label">Enable Arize tracing</span>
                  </label>

                  {enableArize && (
                    <>
                      <label className="settings-field">
                        <span className="settings-label">Project name</span>
                        <input
                          className="settings-input"
                          value={arizeProject}
                          onChange={e => setArizeProject(e.target.value)}
                        />
                      </label>

                      <label className="settings-field">
                        <span className="settings-label">Space ID</span>
                        <input
                          className="settings-input"
                          value={arizeSpaceId}
                          onChange={e => setArizeSpaceId(e.target.value)}
                        />
                      </label>

                      <div className="settings-field">
                        <span className="settings-label">Arize API Key</span>
                        {!changeArizeKey ? (
                          <div className="settings-key-row">
                            <code className="settings-code settings-code--key">
                              {settings?.arize_api_key_set
                                ? settings.arize_api_key_preview
                                : <span className="settings-unset">Not set</span>}
                            </code>
                            <button
                              className="settings-change-btn"
                              onClick={() => setChangeArizeKey(true)}
                            >
                              {settings?.arize_api_key_set ? 'Change' : 'Set key'}
                            </button>
                          </div>
                        ) : (
                          <div className="settings-key-row">
                            <input
                              type="password"
                              className="settings-input settings-input--key"
                              placeholder="ak-..."
                              value={arizeKey}
                              onChange={e => setArizeKey(e.target.value)}
                              autoFocus
                            />
                            <button className="settings-change-btn" onClick={() => { setChangeArizeKey(false); setArizeKey('') }}>
                              Cancel
                            </button>
                          </div>
                        )}
                      </div>
                    </>
                  )}

                  <div className="settings-actions">
                    <button className="settings-save-btn" onClick={handleSave} disabled={saving}>
                      {saving ? 'Saving…' : saved ? '✓ Saved' : 'Save Settings'}
                    </button>
                  </div>
                </div>
              )}

            </div>
          </div>
        )}
      </div>
    </div>
  )
}
