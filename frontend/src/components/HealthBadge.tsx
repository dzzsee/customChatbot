import { motion, useReducedMotion } from 'motion/react'

import type { HealthResponse } from '../lib/types'

interface Props {
  health: HealthResponse | null
  online: boolean
}

type Tone = 'ok' | 'warn' | 'bad' | 'pending'

const DOT: Record<Tone, string> = {
  ok: 'bg-brand',
  warn: 'bg-amber-400',
  bad: 'bg-red-400',
  pending: 'bg-ink-faint',
}

const TEXT: Record<Tone, string> = {
  ok: 'text-ink',
  warn: 'text-amber-200',
  bad: 'text-red-300',
  pending: 'text-ink-dim',
}

export function HealthBadge({ health, online }: Props) {
  const reduceMotion = useReducedMotion()

  let tone: Tone = 'pending'
  let label = 'Comprobando'
  let title = 'Consultando el estado de los modelos en NVIDIA NIM.'

  if (!online) {
    tone = 'bad'
    label = 'Sin conexion'
    title = 'No hay respuesta del backend. Arrancalo con: cd backend && uvicorn app.main:app --reload'
  } else if (health && !health.api_key_configured) {
    tone = 'warn'
    label = 'Falta API key'
    title = 'Copia backend/.env.example a backend/.env y anade tu NVIDIA_API_KEY'
  } else if (health) {
    const failed = health.models.filter((model) => !model.ok)
    if (health.status === 'ok') {
      tone = 'ok'
      label = 'Conectado'
      title = `NIM conectado · FFmpeg ${health.ffmpeg_available ? 'ok' : 'no disponible'} · RAG ${health.rag_available ? 'ok' : 'desactivado'}`
    } else {
      tone = 'warn'
      label = 'Degradado'
      title = `Modelos con problemas: ${failed.map((model) => `${model.model} (${model.detail})`).join('; ')}`
    }
  }

  return (
    <span
      className={`glass-thin flex shrink-0 items-center gap-2 rounded-xl px-2.5 py-2 t-caption font-medium ${TEXT[tone]}`}
      title={title}
    >
      <span className="relative flex h-1.5 w-1.5 shrink-0 items-center justify-center">
        <span className={`absolute h-1.5 w-1.5 rounded-full ${DOT[tone]}`} />
        {tone === 'ok' && !reduceMotion && (
          <motion.span
            className="absolute h-1.5 w-1.5 rounded-full bg-brand"
            animate={{ opacity: [0.5, 0], scale: [1, 2.4] }}
            transition={{ duration: 2.2, repeat: Infinity, ease: 'easeOut' }}
          />
        )}
      </span>
      <span className="hidden sm:inline">{label}</span>
    </span>
  )
}
