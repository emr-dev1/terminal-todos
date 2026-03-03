import type { Note } from '../types'

const BASE = '/api'

export async function listNotes(limit = 50): Promise<Note[]> {
  const res = await fetch(`${BASE}/notes?limit=${limit}`)
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function createNote(content: string, title?: string): Promise<Note> {
  const res = await fetch(`${BASE}/notes`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ content, title }),
  })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function deleteNote(id: number): Promise<void> {
  const res = await fetch(`${BASE}/notes/${id}`, { method: 'DELETE' })
  if (!res.ok) throw new Error(await res.text())
}

export async function searchNotes(q: string, limit = 10): Promise<Note[]> {
  const res = await fetch(`${BASE}/notes/search?q=${encodeURIComponent(q)}&limit=${limit}`)
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}
