export type FileKind = 'image' | 'video' | 'audio' | 'document'

export type MessageRole = 'user' | 'assistant' | 'system'

export interface Attachment {
  file_id: string
  name: string
  mime: string
  kind: FileKind
  size_bytes: number
  duration_s: number | null
  width: number | null
  height: number | null
  page_count: number | null
  url: string
  analysis: string
  created_at: string
}

export interface AnalyzeResponse {
  attachment: Attachment
  analysis: string
  warnings: string[]
}

export interface ChatMessage {
  role: MessageRole
  content: string
  attachment_ids: string[]
  attachments?: Attachment[]
  reasoning?: string
  audio?: string
  model?: string
}

export interface ModelInfo {
  id: string
  label: string
  role: string
  description: string
}

export interface ModelListResponse {
  models: ModelInfo[]
  default: string
}

export interface HealthResponse {
  status: string
  api_key_configured: boolean
  base_url: string
  ffmpeg_available: boolean
  rag_available: boolean
  models: { model: string; role: string; ok: boolean; detail: string }[]
  limits: Record<string, number>
}

export interface KnowledgeHit {
  file_id: string | null
  name: string | null
  kind: string | null
  text: string
  score: number | null
}

export interface TranscribeResponse {
  text: string
  model: string
  language: string
  used_fallback: boolean
}
