import { useEffect, useRef, useState } from 'react'
import { motion, useReducedMotion } from 'motion/react'

import { AttachmentChip } from './AttachmentChip'
import { MarkdownView } from './MarkdownView'
import {
  AudioIcon,
  BrainIcon,
  ChatGlyph,
  DocumentIcon,
  ImageIcon,
  VideoIcon,
} from './icons'
import { formatBytes } from '../lib/format'
import type { ChatMessage } from '../lib/types'

interface Props {
  messages: ChatMessage[]
  busy: boolean
}

export function MessageList({ messages, busy }: Props) {
  const endRef = useRef<HTMLDivElement>(null)
  const reduceMotion = useReducedMotion()

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: reduceMotion ? 'auto' : 'smooth', block: 'end' })
  }, [messages, reduceMotion])

  if (messages.length === 0) return <EmptyState />

  return (
    <div className="fade-top flex-1 overflow-y-auto">
      <div className="mx-auto flex w-full max-w-4xl flex-col gap-6 px-3 py-6 sm:px-5 sm:py-8">
        {messages.map((message, index) => (
          <MessageRow
            key={index}
            message={message}
            streaming={busy && index === messages.length - 1}
          />
        ))}
        <div ref={endRef} />
      </div>
    </div>
  )
}

function MessageRow({ message, streaming }: { message: ChatMessage; streaming: boolean }) {
  const isUser = message.role === 'user'

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div
        className={`flex max-w-[min(42rem,94%)] flex-col gap-2.5 ${isUser ? 'items-end' : 'items-start'}`}
      >
        {message.attachments && message.attachments.length > 0 && (
          <div className="flex flex-wrap justify-end gap-1.5">
            {message.attachments.map((attachment) => (
              <AttachmentChip key={attachment.file_id} attachment={attachment} compact />
            ))}
          </div>
        )}

        {message.content.trim() && (
          <div
            className={`w-full px-4 py-3 ${
              isUser
                ? 'rounded-[1.15rem] rounded-br-md bg-brand text-black'
                : 'glass rounded-[1.15rem] rounded-bl-md'
            }`}
          >
            {isUser ? (
              <p className="t-body whitespace-pre-wrap">{message.content}</p>
            ) : (
              <MarkdownView streaming={streaming}>{message.content}</MarkdownView>
            )}
          </div>
        )}

        {!isUser && message.reasoning && message.reasoning.trim() && (
          <Reasoning text={message.reasoning} />
        )}

        {message.audio && <AudioReply base64={message.audio} />}

        {message.model && !isUser && (
          <p className="t-caption px-1.5 text-ink-faint">
            {message.model.replace(/^nvidia\//, '')}
          </p>
        )}
      </div>
    </div>
  )
}

function Reasoning({ text }: { text: string }) {
  return (
    <details className="glass-thin w-full overflow-hidden rounded-xl">
      <summary className="flex cursor-pointer list-none items-center gap-1.5 px-3 py-2 t-caption font-medium text-ink-dim transition-colors hover:text-ink [&::-webkit-details-marker]:hidden">
        <BrainIcon className="h-3.5 w-3.5 shrink-0" />
        <span className="flex-1">Razonamiento del modelo</span>
        <span className="tabular-nums text-ink-faint">{text.length.toLocaleString('es')}</span>
      </summary>
      <pre className="max-h-72 overflow-y-auto whitespace-pre-wrap border-t border-edge/50 px-3.5 py-3 text-[0.7rem] leading-relaxed text-ink-dim">
        {text}
      </pre>
    </details>
  )
}

function AudioReply({ base64 }: { base64: string }) {
  const [failed, setFailed] = useState(false)

  if (failed) {
    return <p className="t-caption text-ink-dim">No se pudo reproducir el audio de la respuesta.</p>
  }

  return (
    <audio
      controls
      src={`data:audio/wav;base64,${base64}`}
      className="h-9 w-full max-w-xs"
      onError={() => setFailed(true)}
    />
  )
}

function EmptyState() {
  const reduceMotion = useReducedMotion()

  const capabilities = [
    { Glyph: ImageIcon, title: 'Analiza imagenes', body: 'Nemotron 3 Nano Omni describe escenas, lee texto y responde preguntas.' },
    { Glyph: VideoIcon, title: 'Analiza video', body: 'Hasta 2 minutos con audio, linea de tiempo y transcripcion.' },
    { Glyph: DocumentIcon, title: 'Lee documentos', body: 'PDF, Word, Markdown, CSV y texto plano, con OCR cuando hace falta.' },
    { Glyph: AudioIcon, title: 'Escucha y habla', body: 'Dicta con el microfono y escucha la respuesta en voz alta.' },
  ]

  // Un unico momento orquestado al cargar; el resto de la interfaz se queda quieta.
  const reveal = reduceMotion
    ? {}
    : {
        initial: { opacity: 0, y: 14 },
        animate: { opacity: 1, y: 0 },
        transition: { type: 'spring' as const, bounce: 0, duration: 0.55 },
      }

  return (
    <div className="fade-top flex-1 overflow-y-auto">
      <div className="mx-auto flex w-full max-w-4xl flex-col items-center px-5 py-12 sm:py-20">
        <motion.div {...reveal} className="flex w-full flex-col items-center text-center">
          <span className="glass-raised mb-6 flex h-12 w-12 items-center justify-center rounded-2xl text-brand">
            <ChatGlyph className="h-6 w-6" />
          </span>

          <h2 className="t-display max-w-2xl text-balance">
            Preguntale a Nemotron por lo que ve, lo que oye y lo que lees
          </h2>

          <p className="t-body mt-4 max-w-lg text-pretty text-ink-dim">
            Sube una imagen, un video corto, un documento o un audio. Todo lo que analices queda
            indexado, asi que podras consultarlo mas adelante.
          </p>
        </motion.div>

        <div className="mt-12 w-full max-w-2xl border-t border-edge/60">
          {capabilities.map(({ Glyph, title, body }) => (
            <div
              key={title}
              className="flex items-start gap-4 border-b border-edge/40 py-4 last:border-b-0"
            >
              <Glyph className="mt-0.5 h-[1.15rem] w-[1.15rem] shrink-0 text-ink-faint" />
              <div className="min-w-0">
                <p className="t-body font-medium">{title}</p>
                <p className="t-meta mt-0.5 text-ink-dim">{body}</p>
              </div>
            </div>
          ))}
        </div>

        <p className="t-caption mt-10 text-ink-faint">
          Adjunta con el clip o arrastra sobre la ventana · video hasta {formatBytes(100 * 1024 * 1024)}
        </p>
      </div>
    </div>
  )
}
