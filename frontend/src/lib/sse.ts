import { assetUrl } from './api'

export interface ChatStreamBody {
  messages: { role: string; content: string; attachment_ids: string[] }[]
  model: string | null
  attachment_ids: string[]
  use_rag: boolean
  reasoning: boolean | null
  speak: boolean
}

export interface StreamHandlers {
  onEvent: (event: string, data: Record<string, unknown>) => void
  onNetworkError: (message: string) => void
}

/** Lee la respuesta SSE del backend y reparte los eventos por nombre. */
export async function streamChat(
  body: ChatStreamBody,
  handlers: StreamHandlers,
  signal: AbortSignal,
): Promise<void> {
  let response: Response
  try {
    response = await fetch(assetUrl('/api/chat/stream'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
      signal,
    })
  } catch (error) {
    if ((error as Error).name === 'AbortError') return
    handlers.onNetworkError('No se pudo conectar con el backend. Esta el servidor arrancado?')
    return
  }

  if (!response.ok || !response.body) {
    let message = `${response.status} ${response.statusText}`
    try {
      const parsed = await response.json()
      if (typeof parsed.detail === 'string') message = parsed.detail
    } catch {
      /* respuesta no JSON */
    }
    handlers.onNetworkError(message)
    return
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  const dispatch = (raw: string) => {
    let event = 'message'
    const dataLines: string[] = []
    for (const line of raw.split('\n')) {
      if (line.startsWith('event:')) event = line.slice(6).trim()
      else if (line.startsWith('data:')) dataLines.push(line.slice(5).trim())
    }
    if (dataLines.length === 0) return
    try {
      handlers.onEvent(event, JSON.parse(dataLines.join('\n')) as Record<string, unknown>)
    } catch {
      /* payload incompleto entre chunks */
    }
  }

  try {
    for (;;) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true }).replace(/\r\n/g, '\n')
      let index = buffer.indexOf('\n\n')
      while (index !== -1) {
        const chunk = buffer.slice(0, index)
        buffer = buffer.slice(index + 2)
        if (chunk.trim()) dispatch(chunk)
        index = buffer.indexOf('\n\n')
      }
    }
    if (buffer.trim()) dispatch(buffer)
  } catch (error) {
    if ((error as Error).name === 'AbortError') return
    handlers.onNetworkError(`Se corto la conexion: ${(error as Error).message}`)
  } finally {
    reader.releaseLock()
  }
}
