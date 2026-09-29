import { useCallback, useEffect, useRef, useState } from 'react'

import { analyzeFile, deleteFile, getHealth, getModels, listFiles, searchKnowledge } from '../lib/api'
import { errorMessage } from '../lib/format'
import { streamChat } from '../lib/sse'
import type {
  Attachment,
  ChatMessage,
  HealthResponse,
  KnowledgeHit,
  ModelInfo,
} from '../lib/types'

export interface UploadTask {
  id: string
  name: string
  size: number
  progress: number
  status: 'uploading' | 'analyzing' | 'done' | 'error'
  error?: string
}

const CLIENT_LIMITS: { extensions: string[]; maxMb: number; label: string }[] = [
  { extensions: ['.png', '.jpg', '.jpeg', '.webp', '.gif', '.bmp'], maxMb: 20, label: 'imagen' },
  { extensions: ['.mp4', '.m4v', '.webm', '.mov', '.mkv', '.avi'], maxMb: 100, label: 'video' },
  { extensions: ['.mp3', '.wav', '.m4a', '.ogg', '.flac', '.aac'], maxMb: 50, label: 'audio' },
  {
    extensions: ['.pdf', '.txt', '.md', '.csv', '.tsv', '.json', '.docx', '.log'],
    maxMb: 50,
    label: 'documento',
  },
]

function preValidate(file: File): string | null {
  const name = file.name.toLowerCase()
  const rule = CLIENT_LIMITS.find((item) => item.extensions.some((ext) => name.endsWith(ext)))
  if (!rule) {
    return `Formato no admitido: ${file.name}. Se aceptan imagenes, video, audio, PDF, TXT, MD, CSV y DOCX.`
  }
  if (file.size > rule.maxMb * 1024 * 1024) {
    const actual = (file.size / 1024 / 1024).toFixed(1)
    return `${file.name} pesa ${actual} MB y el limite para ${rule.label} es ${rule.maxMb} MB.`
  }
  return null
}

export function useChatbot() {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [busy, setBusy] = useState(false)
  const [input, setInput] = useState('')
  const [attachments, setAttachments] = useState<Attachment[]>([])
  const [uploads, setUploads] = useState<UploadTask[]>([])
  const [files, setFiles] = useState<Attachment[]>([])
  const [models, setModels] = useState<ModelInfo[]>([])
  const [model, setModel] = useState('')
  const [health, setHealth] = useState<HealthResponse | null>(null)
  const [online, setOnline] = useState(true)
  const [notice, setNotice] = useState<string | null>(null)
  const [searchHits, setSearchHits] = useState<KnowledgeHit[]>([])
  const [searching, setSearching] = useState(false)

  const abortRef = useRef<AbortController | null>(null)
  const searchTimer = useRef<number | null>(null)

  const refreshFiles = useCallback(async () => {
    try {
      const result = await listFiles()
      setFiles(result.files)
    } catch {
      /* el badge de salud ya informa del estado */
    }
  }, [])

  useEffect(() => {
    let active = true
    const bootstrap = async () => {
      try {
        const [healthResult, modelResult] = await Promise.all([getHealth(), getModels()])
        if (!active) return
        setHealth(healthResult)
        setOnline(true)
        setModels(modelResult.models)
        setModel((current) => current || modelResult.default)
      } catch {
        if (active) setOnline(false)
      }
      await refreshFiles()
    }
    void bootstrap()

    const timer = window.setInterval(async () => {
      try {
        const result = await getHealth()
        setHealth(result)
        setOnline(true)
      } catch {
        setOnline(false)
      }
    }, 60000)

    return () => {
      active = false
      window.clearInterval(timer)
    }
  }, [refreshFiles])

  useEffect(() => {
    return () => abortRef.current?.abort()
  }, [])

  useEffect(() => {
    if (notice === null) return
    const timer = window.setTimeout(() => setNotice(null), 6000)
    return () => window.clearTimeout(timer)
  }, [notice])

  // ------------------------------------------------------------- archivos

  const updateUpload = (id: string, patch: Partial<UploadTask>) => {
    setUploads((current) => current.map((task) => (task.id === id ? { ...task, ...patch } : task)))
  }

  const uploadFiles = useCallback(
    async (incoming: FileList | File[]) => {
      const list = Array.from(incoming)
      for (const file of list) {
        const id = `${Date.now()}-${file.name}`
        const problem = preValidate(file)

        if (problem) {
          setUploads((current) => [
            ...current,
            { id, name: file.name, size: file.size, progress: 0, status: 'error', error: problem },
          ])
          continue
        }

        setUploads((current) => [
          ...current,
          { id, name: file.name, size: file.size, progress: 0, status: 'uploading' },
        ])

        try {
          updateUpload(id, { status: 'analyzing', progress: 1 })
          const result = await analyzeFile(file)
          setAttachments((current) => [...current, result.attachment])
          setFiles((current) => [result.attachment, ...current.filter((f) => f.file_id !== result.attachment.file_id)])
          updateUpload(id, { status: 'done' })
          if (result.warnings.length > 0) setNotice(result.warnings.join(' '))
        } catch (error) {
          updateUpload(id, { status: 'error', error: errorMessage(error) })
        }
      }

      window.setTimeout(() => {
        setUploads((current) => current.filter((task) => task.status !== 'done'))
      }, 2500)
    },
    [],
  )

  const removeAttachment = (fileId: string) => {
    setAttachments((current) => current.filter((item) => item.file_id !== fileId))
  }

  const attachExisting = (fileId: string) => {
    setAttachments((current) =>
      current.some((item) => item.file_id === fileId)
        ? current
        : [...current, files.find((file) => file.file_id === fileId)].filter((f): f is Attachment => Boolean(f)),
    )
  }

  const removeFile = async (fileId: string) => {
    try {
      await deleteFile(fileId)
      setFiles((current) => current.filter((file) => file.file_id !== fileId))
      setAttachments((current) => current.filter((file) => file.file_id !== fileId))
    } catch (error) {
      setNotice(errorMessage(error))
    }
  }

  const runSearch = (query: string) => {
    if (searchTimer.current !== null) window.clearTimeout(searchTimer.current)
    if (query.trim().length < 2) {
      setSearchHits([])
      return
    }
    searchTimer.current = window.setTimeout(async () => {
      setSearching(true)
      try {
        const result = await searchKnowledge(query)
        setSearchHits(result.hits)
      } catch {
        setSearchHits([])
      } finally {
        setSearching(false)
      }
    }, 350)
  }

  // ----------------------------------------------------------------- chat

  const patchLastAssistant = (patch: (message: ChatMessage) => ChatMessage) => {
    setMessages((current) => {
      if (current.length === 0) return current
      const next = [...current]
      const last = next[next.length - 1]
      if (!last || last.role !== 'assistant') return current
      next[next.length - 1] = patch(last)
      return next
    })
  }

  const appendToLastAssistant = (field: 'content' | 'reasoning', delta: string) => {
    patchLastAssistant((message) => ({ ...message, [field]: (message[field] ?? '') + delta }))
  }

  const send = ({ speak }: { speak: boolean }) => {
    const text = input.trim()
    if ((!text && attachments.length === 0) || busy) return

    const sent: Attachment[] = attachments
    const userMessage: ChatMessage = {
      role: 'user',
      content: text || 'Analiza este archivo.',
      attachment_ids: sent.map((item) => item.file_id),
      attachments: sent,
    }
    const history = [...messages, userMessage]

    setMessages([...history, { role: 'assistant', content: '', attachment_ids: [], model }])
    setInput('')
    setAttachments([])
    setBusy(true)

    const controller = new AbortController()
    abortRef.current = controller

    void streamChat(
      {
        messages: history.map((message) => ({
          role: message.role,
          content: message.content,
          attachment_ids: message.attachment_ids,
        })),
        model: model || null,
        attachment_ids: sent.map((item) => item.file_id),
        use_rag: true,
        reasoning: null,
        speak,
      },
      {
        onEvent: (event, data) => {
          if (event === 'meta') {
            patchLastAssistant((message) => ({ ...message, model: String(data.model ?? '') }))
          } else if (event === 'reasoning') {
            appendToLastAssistant('reasoning', String(data.delta ?? ''))
          } else if (event === 'delta') {
            appendToLastAssistant('content', String(data.delta ?? ''))
          } else if (event === 'audio') {
            patchLastAssistant((message) => ({ ...message, audio: String(data.audio_base64 ?? '') }))
          } else if (event === 'warning') {
            setNotice(String(data.message ?? ''))
          } else if (event === 'blocked') {
            patchLastAssistant((message) => ({
              ...message,
              content: `⛔ ${String(data.message ?? 'Mensaje bloqueado por la moderacion.')}`,
            }))
          } else if (event === 'error') {
            patchLastAssistant((message) => ({
              ...message,
              content: `⚠️ ${String(data.message ?? 'Error desconocido.')}`,
            }))
          }
        },
        onNetworkError: (message) => {
          patchLastAssistant((existing) => ({
            ...existing,
            content: existing.content || `⚠️ ${message}`,
          }))
        },
      },
      controller.signal,
    ).finally(() => {
      setBusy(false)
      abortRef.current = null
    })
  }

  const stop = () => {
    abortRef.current?.abort()
    abortRef.current = null
    setBusy(false)
    patchLastAssistant((message) => ({ ...message, reasoning: message.reasoning }))
  }

  const clearChat = () => {
    abortRef.current?.abort()
    abortRef.current = null
    setMessages([])
    setBusy(false)
  }

  return {
    messages,
    busy,
    input,
    setInput,
    attachments,
    uploads,
    files,
    models,
    model,
    setModel,
    health,
    online,
    notice,
    setNotice,
    searchHits,
    searching,
    send,
    stop,
    clearChat,
    uploadFiles,
    removeAttachment,
    attachExisting,
    removeFile,
    runSearch,
    refreshFiles,
  }
}
