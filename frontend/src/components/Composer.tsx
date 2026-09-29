import { useEffect, useRef, useState } from 'react'
import { AnimatePresence, motion, useReducedMotion } from 'motion/react'

import { AttachmentChip } from './AttachmentChip'
import { VoiceRecorder } from './VoiceRecorder'
import { ClipIcon, SendIcon, SpeakerIcon, StopIcon } from './icons'
import type { Attachment } from '../lib/types'

export interface UploadTask {
  id: string
  name: string
  size: number
  progress: number
  status: 'uploading' | 'analyzing' | 'done' | 'error'
  error?: string
}

interface Props {
  value: string
  onChange: (value: string) => void
  attachments: Attachment[]
  onRemoveAttachment: (fileId: string) => void
  uploads: UploadTask[]
  onPickFiles: (files: FileList | File[]) => void
  onStop: () => void
  onSubmit: (options: { speak: boolean }) => void
  busy: boolean
  disabled: boolean
}

const SPRING = { type: 'spring', bounce: 0, duration: 0.35 } as const

export function Composer({
  value,
  onChange,
  attachments,
  onRemoveAttachment,
  uploads,
  onPickFiles,
  onStop,
  onSubmit,
  busy,
  disabled,
}: Props) {
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const [speak, setSpeak] = useState(false)
  const [dragging, setDragging] = useState(false)
  const [focused, setFocused] = useState(false)
  const reduceMotion = useReducedMotion()

  useEffect(() => {
    const node = textareaRef.current
    if (!node) return
    node.style.height = 'auto'
    node.style.height = `${Math.min(node.scrollHeight, 200)}px`
  }, [value])

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && dragging) setDragging(false)
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [dragging])

  const canSend = (value.trim().length > 0 || attachments.length > 0) && !busy && !disabled

  const submit = () => {
    if (!canSend) return
    onSubmit({ speak })
  }

  return (
    <div
      className="relative mx-auto max-w-4xl"
      onDragOver={(event) => {
        event.preventDefault()
        setDragging(true)
      }}
      onDragLeave={(event) => {
        if (event.currentTarget === event.target) setDragging(false)
      }}
      onDrop={(event) => {
        event.preventDefault()
        setDragging(false)
        if (event.dataTransfer.files.length > 0) onPickFiles(event.dataTransfer.files)
      }}
    >
      <AnimatePresence>
        {dragging && (
          <motion.div
            initial={{ opacity: 0, scale: 0.98 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.98 }}
            transition={reduceMotion ? { duration: 0.12 } : SPRING}
            className="glass-raised pointer-events-none absolute inset-0 z-20 flex flex-col items-center justify-center gap-1.5 rounded-[1.4rem] border-2 border-dashed border-brand/60"
          >
            <ClipIcon className="h-6 w-6 text-brand" />
            <p className="t-body font-medium text-brand">Suelta el archivo para analizarlo</p>
          </motion.div>
        )}
      </AnimatePresence>

      {uploads.length > 0 && (
        <div className="mb-2 flex flex-col gap-1.5">
          {uploads.map((task) => (
            <div key={task.id} className="glass-thin rounded-xl px-3.5 py-2.5 t-meta">
              <div className="flex items-center justify-between gap-3">
                <span className="truncate font-medium">{task.name}</span>
                <span
                  className={
                    task.status === 'error'
                      ? 'text-red-300'
                      : task.status === 'done'
                        ? 'text-brand'
                        : 'text-ink-dim'
                  }
                >
                  {task.status === 'uploading'
                    ? `Subiendo ${Math.round(task.progress * 100)}%`
                    : task.status === 'analyzing'
                      ? 'Analizando con Nemotron…'
                      : task.status === 'done'
                        ? 'Listo'
                        : (task.error ?? 'Error')}
                </span>
              </div>
              {task.status === 'uploading' && (
                <div className="mt-2 h-[3px] overflow-hidden rounded-full bg-white/8">
                  <div
                    className="h-full rounded-full bg-brand"
                    style={{ width: `${Math.round(task.progress * 100)}%` }}
                  />
                </div>
              )}
              {task.status === 'analyzing' && (
                <div className="mt-2 h-[3px] overflow-hidden rounded-full bg-white/8">
                  <div className="bar-indeterminate h-full w-full rounded-full bg-brand/70" />
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {attachments.length > 0 && (
        <div className="mb-2 flex flex-wrap gap-1.5">
          <AnimatePresence initial={false}>
            {attachments.map((attachment) => (
              <motion.div
                key={attachment.file_id}
                layout={!reduceMotion}
                initial={reduceMotion ? false : { opacity: 0, scale: 0.92, y: 4 }}
                animate={{ opacity: 1, scale: 1, y: 0 }}
                exit={reduceMotion ? { opacity: 0 } : { opacity: 0, scale: 0.92, y: -4 }}
                transition={SPRING}
              >
                <AttachmentChip
                  attachment={attachment}
                  compact
                  onRemove={() => onRemoveAttachment(attachment.file_id)}
                />
              </motion.div>
            ))}
          </AnimatePresence>
        </div>
      )}

      {/* Material grueso: la superficie mas grande de la pantalla, la mas difusa. */}
      <div
        className={`glass-raised flex items-end gap-1 rounded-[1.4rem] px-2 py-2 transition-shadow duration-300 sm:gap-2 sm:px-2.5 ${
          focused ? 'ring-1 ring-brand/45' : 'ring-0'
        }`}
      >
        <button
          type="button"
          onClick={() => inputRef.current?.click()}
          disabled={disabled}
          title="Adjuntar archivo"
          aria-label="Adjuntar archivo"
          className="pressable flex h-9 w-9 shrink-0 items-center justify-center rounded-xl text-ink-dim hover:bg-white/8 hover:text-ink disabled:opacity-40"
        >
          <ClipIcon className="h-[1.15rem] w-[1.15rem]" />
        </button>
        <input
          ref={inputRef}
          type="file"
          multiple
          className="hidden"
          accept="image/*,video/*,audio/*,.pdf,.txt,.md,.csv,.docx,.json"
          onChange={(event) => {
            if (event.target.files?.length) onPickFiles(event.target.files)
            event.target.value = ''
          }}
        />

        <textarea
          ref={textareaRef}
          rows={1}
          value={value}
          disabled={disabled}
          placeholder={disabled ? 'Configura NVIDIA_API_KEY en el backend para empezar' : 'Escribe tu mensaje…'}
          onFocus={() => setFocused(true)}
          onBlur={() => setFocused(false)}
          onChange={(event) => onChange(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === 'Enter' && !event.shiftKey) {
              event.preventDefault()
              submit()
            }
          }}
          className="t-body max-h-[200px] flex-1 resize-none bg-transparent py-2.5 text-ink outline-none placeholder:text-ink-faint disabled:opacity-50"
        />

        <button
          type="button"
          onClick={() => setSpeak((current) => !current)}
          title={speak ? 'Respuestas habladas: activado' : 'Respuestas habladas: desactivado'}
          aria-pressed={speak}
          className={`pressable flex h-9 w-9 shrink-0 items-center justify-center rounded-xl ${
            speak ? 'bg-brand/18 text-brand' : 'text-ink-dim hover:bg-white/8 hover:text-ink'
          }`}
        >
          <SpeakerIcon className="h-[1.15rem] w-[1.15rem]" />
        </button>

        <VoiceRecorder onTranscript={onChange} disabled={disabled || busy} />

        {busy ? (
          <button
            type="button"
            onClick={onStop}
            title="Detener"
            aria-label="Detener"
            className="pressable flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-red-500/18 text-red-300 hover:bg-red-500/26"
          >
            <StopIcon className="h-4 w-4" />
          </button>
        ) : (
          <motion.button
            type="button"
            onClick={submit}
            disabled={!canSend}
            title="Enviar"
            aria-label="Enviar"
            whileTap={reduceMotion ? undefined : { scale: 0.9 }}
            className="pressable flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-brand text-black transition-colors hover:bg-brand-dim disabled:bg-white/8 disabled:text-ink-faint"
          >
            <SendIcon className="h-4 w-4" />
          </motion.button>
        )}
      </div>

      <p className="t-caption mt-2 px-2 text-ink-faint">
        Enter envia · Shift+Enter salto de linea · arrastra archivos aqui
      </p>
    </div>
  )
}
