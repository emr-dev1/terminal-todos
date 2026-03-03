export interface Todo {
  id: number
  content: string
  completed: boolean
  priority: number
  created_at: string | null
  completed_at: string | null
  due_date: string | null
  note_id: number | null
  focus_order: number | null
  labels: string[]
}

export interface Note {
  id: number
  content: string
  title: string | null
  note_type: string | null
  created_at: string | null
  updated_at: string | null
  category: string | null
  summary: string | null
  keywords: string[]
  tags: string[]
}

export interface TodoStats {
  active: number
  completed: number
  total: number
}

export interface ExtractedTodoItem {
  content: string
  priority: number
}

export interface ExtractionResult {
  title: string
  note_type: string
  todos: ExtractedTodoItem[]
}

export type ChatRole = 'user' | 'assistant' | 'tool' | 'extraction'

export interface ChatMessage {
  id: string
  role: ChatRole
  content: string
  toolName?: string
  isStreaming?: boolean
  // extraction messages
  extractedTodos?: ExtractedTodoItem[]
  extractionTitle?: string
  extractionNoteType?: string
  extractionSubmitted?: boolean
  extractionAddedCount?: number
  extractionLabel?: string
}

export type WsMessageType = 'token' | 'tool_start' | 'tool_end' | 'refresh_todos' | 'done' | 'error'

export interface WsMessage {
  type: WsMessageType
  content?: string
  tool?: string
  message?: string
}
