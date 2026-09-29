import { useEffect, useRef, useState } from 'react'

import { transcribe } from '../lib/api'
import { errorMessage } from '../lib/format'
import { MicIcon } from './icons'

interface Props {
  onTranscript: (text: string) => void
  disabled?: boolean
}

type RecorderState = 'idle' | 'recording' | 'working'

function pickMimeType(): string {
  const candidates = ['audio/webm;codecs=opus', 'audio/webm', 'audio/ogg;codecs=opus', 'audio/mp4']
  for (const type of candidates) {
    if (typeof MediaRecorder !== 'undefined' && MediaRecorder.isTypeSupported(type)) return type
  }
  return ''
}

export function VoiceRecorder({ onTranscript, disabled = false }: Props) {
  const [state, setState] = useState<RecorderState>('idle')
  const [seconds, setSeconds] = useState(0)
  const [error, setError] = useState<string | null>(null)
  const recorderRef = useRef<MediaRecorder | null>(null)
  const chunksRef = useRef<Blob[]>([])
  const timerRef = useRef<number | null>(null)

  useEffect(() => {
    return () => {
      if (timerRef.current !== null) window.clearInterval(timerRef.current)
      recorderRef.current?.stream.getTracks().forEach((track) => track.stop())
    }
  }, [])

  const stopTimer = () => {
    if (timerRef.current !== null) {
      window.clearInterval(timerRef.current)
      timerRef.current = null
    }
  }

  const start = async () => {
    setError(null)
    if (typeof MediaRecorder === 'undefined' || !navigator.mediaDevices?.getUserMedia) {
      setError('Este navegador no soporta grabacion de audio.')
      return
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const recorder = new MediaRecorder(stream, { mimeType: pickMimeType() })
      chunksRef.current = []

      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) chunksRef.current.push(event.data)
      }
      recorder.onstop = async () => {
        stream.getTracks().forEach((track) => track.stop())
        setSeconds(0)
        setState('working')
        const mime = recorder.mimeType || 'audio/webm'
        const blob = new Blob(chunksRef.current, { type: mime })
        try {
          const result = await transcribe(blob, 'grabacion.webm')
          if (result.text.trim()) onTranscript(result.text.trim())
          else setError('No se detecto voz en la grabacion.')
        } catch (caught) {
          setError(errorMessage(caught))
        } finally {
          setState('idle')
        }
      }

      recorder.start()
      recorderRef.current = recorder
      setState('recording')
      setSeconds(0)
      timerRef.current = window.setInterval(() => setSeconds((value) => value + 1), 1000)
    } catch (caught) {
      setError(
        caught instanceof DOMException && caught.name === 'NotAllowedError'
          ? 'Permiso de microfono denegado.'
          : errorMessage(caught),
      )
      setState('idle')
    }
  }

  const stop = () => {
    stopTimer()
    recorderRef.current?.stop()
    recorderRef.current = null
  }

  const recording = state === 'recording'
  const label = recording
    ? `Grabando ${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, '0')}`
    : state === 'working'
      ? 'Transcribiendo'
      : 'Grabar voz'

  return (
    <div className="flex flex-col items-end">
      <button
        type="button"
        onClick={recording ? stop : start}
        disabled={disabled || state === 'working'}
        title={label}
        aria-label={label}
        className={`pressable relative flex h-9 w-9 shrink-0 items-center justify-center rounded-xl disabled:opacity-40 ${
          recording ? 'recording-halo text-red-400' : 'text-ink-dim hover:bg-white/8 hover:text-ink'
        }`}
      >
        {state === 'working' ? (
          <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-ink-faint border-t-brand" />
        ) : (
          <MicIcon className="relative h-[1.15rem] w-[1.15rem]" />
        )}
      </button>

      {recording && (
        <span className="t-caption mt-1 tabular-nums text-red-300">
          {Math.floor(seconds / 60)}:{String(seconds % 60).padStart(2, '0')}
        </span>
      )}
      {error && <p className="mt-1 max-w-52 text-right t-caption text-red-300">{error}</p>}
    </div>
  )
}
