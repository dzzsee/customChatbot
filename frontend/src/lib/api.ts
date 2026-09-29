import type {
  AnalyzeResponse,
  Attachment,
  HealthResponse,
  KnowledgeHit,
  ModelListResponse,
  TranscribeResponse,
} from './types'

/**
 * URL base del backend.
 *
 * - En desarrollo queda vacia y el proxy de Vite (/api -> 127.0.0.1:8000) resuelve.
 * - En GitHub Pages hay que definir VITE_API_BASE_URL con la URL publica del
 *   backend, porque las paginas estaticas no pueden hacer proxy.
 */
export const API_BASE = (import.meta.env.VITE_API_BASE_URL ?? '').replace(/\/$/, '')

export function assetUrl(path: string): string {
  if (/^https?:\/\//.test(path)) return path
  return `${API_BASE}${path}`
}

export class ApiError extends Error {
  readonly status: number
  constructor(message: string, status: number) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

async function errorFrom(response: Response): Promise<string> {
  try {
    const body = await response.json()
    const detail = body?.detail
    if (typeof detail === 'string') return detail
    if (Array.isArray(detail) && detail[0]?.msg) return String(detail[0].msg)
    return JSON.stringify(body).slice(0, 300)
  } catch {
    return `${response.status} ${response.statusText}`
  }
}

async function json<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(assetUrl(path), init)
  if (!response.ok) throw new ApiError(await errorFrom(response), response.status)
  return (await response.json()) as T
}

export function getHealth(): Promise<HealthResponse> {
  return json<HealthResponse>('/api/health')
}

export function getModels(): Promise<ModelListResponse> {
  return json<ModelListResponse>('/api/models')
}

export function listFiles(): Promise<{ files: Attachment[] }> {
  return json<{ files: Attachment[] }>('/api/files')
}

export function deleteFile(fileId: string): Promise<{ deleted: boolean }> {
  return json<{ deleted: boolean }>(`/api/files/${fileId}`, { method: 'DELETE' })
}

export function searchKnowledge(query: string): Promise<{ query: string; hits: KnowledgeHit[] }> {
  return json(`/api/knowledge/search?q=${encodeURIComponent(query)}`)
}

export async function analyzeFile(
  file: File,
  onProgress?: (fraction: number) => void,
): Promise<AnalyzeResponse> {
  const form = new FormData()
  form.append('file', file)

  // XHR en lugar de fetch: permite informar del progreso de subida, que en
  // videos de hasta 100 MB tarda lo suyo.
  return new Promise<AnalyzeResponse>((resolve, reject) => {
    const xhr = new XMLHttpRequest()
    xhr.open('POST', assetUrl('/api/files/analyze'))
    xhr.upload.onprogress = (event) => {
      if (event.lengthComputable && onProgress) onProgress(event.loaded / event.total)
    }
    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        resolve(JSON.parse(xhr.responseText) as AnalyzeResponse)
      } else {
        let message = `${xhr.status} ${xhr.statusText}`
        try {
          const parsed = JSON.parse(xhr.responseText)
          if (typeof parsed.detail === 'string') message = parsed.detail
        } catch {
          /* respuesta no JSON */
        }
        reject(new ApiError(message, xhr.status))
      }
    }
    xhr.onerror = () => reject(new ApiError('No se pudo conectar con el backend.', 0))
    xhr.send(form)
  })
}

export async function transcribe(blob: Blob, filename = 'grabacion.webm'): Promise<TranscribeResponse> {
  const form = new FormData()
  form.append('file', new File([blob], filename, { type: blob.type || 'audio/webm' }))
  return json<TranscribeResponse>('/api/voice/transcribe', { method: 'POST', body: form })
}
