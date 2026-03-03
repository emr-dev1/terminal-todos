import type React from 'react'
import type { ChatMessage as ChatMessageType, ExtractedTodoItem } from '../types'
import TodoSelectionMessage from './TodoSelectionMessage'
import './ChatMessage.css'

interface Props {
  message: ChatMessageType
  availableLabels: string[]
  onExtractionSubmit: (id: string, selected: ExtractedTodoItem[], label: string) => void
}

// Simple inline markdown renderer — no external deps needed
function renderMarkdown(text: string): React.ReactNode {
  const lines = text.split('\n')
  const output: React.ReactNode[] = []
  let listBuffer: string[] = []
  let keyIdx = 0
  const k = () => keyIdx++

  const flushList = () => {
    if (listBuffer.length === 0) return
    output.push(
      <ul key={k()} className="md-list">
        {listBuffer.map((item, i) => (
          <li key={i}>{renderInline(item)}</li>
        ))}
      </ul>
    )
    listBuffer = []
  }

  const renderInline = (str: string): React.ReactNode => {
    const parts = str.split(/(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`)/g)
    return parts.map((part, i) => {
      if (part.startsWith('**') && part.endsWith('**')) return <strong key={i}>{part.slice(2, -2)}</strong>
      if (part.startsWith('*') && part.endsWith('*') && part.length > 2) return <em key={i}>{part.slice(1, -1)}</em>
      if (part.startsWith('`') && part.endsWith('`')) return <code key={i} className="md-code">{part.slice(1, -1)}</code>
      return part
    })
  }

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i]
    if (line.startsWith('### ')) { flushList(); output.push(<h4 key={k()} className="md-h4">{renderInline(line.slice(4))}</h4>); continue }
    if (line.startsWith('## '))  { flushList(); output.push(<h3 key={k()} className="md-h3">{renderInline(line.slice(3))}</h3>); continue }
    if (line.startsWith('# '))   { flushList(); output.push(<h2 key={k()} className="md-h2">{renderInline(line.slice(2))}</h2>); continue }
    if (line === '---' || line === '***') { flushList(); output.push(<hr key={k()} className="md-hr" />); continue }
    const listMatch = line.match(/^(\s*[-*•]|\s*\d+\.)\s+(.*)$/)
    if (listMatch) { listBuffer.push(listMatch[2]); continue }
    flushList()
    if (line.trim() === '') { if (output.length > 0) output.push(<div key={k()} className="md-spacer" />); continue }
    output.push(<p key={k()} className="md-p">{renderInline(line)}</p>)
  }
  flushList()
  return output
}

export default function ChatMessage({ message, availableLabels, onExtractionSubmit }: Props) {
  // ---- Tool activity ----
  if (message.role === 'tool') {
    return (
      <div className="chat-tool-activity">
        <span className="tool-icon">⚙</span>
        <span className="tool-name">{message.toolName}</span>
        <span className="tool-sep">·</span>
        <span className="tool-status">{message.content}</span>
      </div>
    )
  }

  // ---- Extraction selection card ----
  if (message.role === 'extraction') {
    return (
      <TodoSelectionMessage
        todos={message.extractedTodos ?? []}
        title={message.extractionTitle ?? 'Extracted from notes'}
        noteType={message.extractionNoteType ?? 'general'}
        submitted={message.extractionSubmitted ?? false}
        addedCount={message.extractionAddedCount ?? 0}
        submittedLabel={message.extractionLabel}
        availableLabels={availableLabels}
        onSubmit={(selected, label) => onExtractionSubmit(message.id, selected, label)}
      />
    )
  }

  // ---- Normal user / assistant message ----
  return (
    <div className={`chat-message chat-message-${message.role}`}>
      <div className="chat-message-bubble">
        <span className="chat-message-role">
          {message.role === 'user' ? 'you' : 'assistant'}
        </span>
        <div className="chat-message-content">
          {message.role === 'assistant'
            ? renderMarkdown(message.content)
            : message.content}
          {message.isStreaming && <span className="cursor-blink">▋</span>}
        </div>
      </div>
    </div>
  )
}
