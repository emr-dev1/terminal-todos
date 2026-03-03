import type { Todo, TodoStats } from '../types'

const BASE = '/api'

export async function listTodos(status: 'active' | 'completed' | 'all' = 'active'): Promise<Todo[]> {
  const res = await fetch(`${BASE}/todos?status=${status}`)
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function createTodo(content: string, priority = 0, due_date?: string): Promise<Todo> {
  const res = await fetch(`${BASE}/todos`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ content, priority, due_date }),
  })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function updateTodo(
  id: number,
  fields: { content?: string; priority?: number; due_date?: string | null; labels?: string[] },
): Promise<Todo> {
  const res = await fetch(`${BASE}/todos/${id}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(fields),
  })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function deleteTodo(id: number): Promise<void> {
  const res = await fetch(`${BASE}/todos/${id}`, { method: 'DELETE' })
  if (!res.ok) throw new Error(await res.text())
}

export async function completeTodo(id: number): Promise<Todo> {
  const res = await fetch(`${BASE}/todos/${id}/complete`, { method: 'POST' })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function uncompleteTodo(id: number): Promise<Todo> {
  const res = await fetch(`${BASE}/todos/${id}/uncomplete`, { method: 'POST' })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function getTodoStats(): Promise<TodoStats> {
  const res = await fetch(`${BASE}/todos/stats`)
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function getFocusedTodos(): Promise<Todo[]> {
  const res = await fetch(`${BASE}/todos/focus`)
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function addToFocus(id: number): Promise<Todo> {
  const res = await fetch(`${BASE}/todos/${id}/focus`, { method: 'POST' })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function removeFromFocus(id: number): Promise<void> {
  const res = await fetch(`${BASE}/todos/${id}/focus`, { method: 'DELETE' })
  if (!res.ok) throw new Error(await res.text())
}

export async function getLabels(): Promise<string[]> {
  const res = await fetch(`${BASE}/todos/labels`)
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}
