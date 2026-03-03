const BASE = '/api'

export interface AppSettings {
  openai_api_key_set: boolean
  openai_api_key_preview: string
  data_dir: string
  db_path: string
  embedding_model: string
  llm_model: string
  user_name: string
  max_todos_display: number
  search_results_limit: number
  verbose_logging: boolean
  enable_arize_tracing: boolean
  arize_space_id: string | null
  arize_api_key_set: boolean
  arize_api_key_preview: string
  arize_project_name: string
  env_path: string
}

export interface UpdateSettingsPayload {
  openai_api_key?: string
  llm_model?: string
  embedding_model?: string
  user_name?: string
  max_todos_display?: number
  search_results_limit?: number
  verbose_logging?: boolean
  enable_arize_tracing?: boolean
  arize_space_id?: string | null
  arize_api_key?: string
  arize_project_name?: string
}

export async function getSettings(): Promise<AppSettings> {
  const res = await fetch(`${BASE}/settings`)
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function updateSettings(payload: UpdateSettingsPayload): Promise<void> {
  const res = await fetch(`${BASE}/settings`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  if (!res.ok) throw new Error(await res.text())
}

export async function getSettingsLabels(): Promise<string[]> {
  const res = await fetch(`${BASE}/settings/labels`)
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function createLabel(label: string): Promise<void> {
  const res = await fetch(`${BASE}/settings/labels`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ label }),
  })
  if (!res.ok) throw new Error(await res.text())
}

export async function renameLabel(old_label: string, new_label: string): Promise<{ updated: number }> {
  const res = await fetch(`${BASE}/settings/labels/rename`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ old_label, new_label }),
  })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function deleteLabel(label: string): Promise<{ updated: number }> {
  const res = await fetch(`${BASE}/settings/labels/${encodeURIComponent(label)}`, {
    method: 'DELETE',
  })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}
