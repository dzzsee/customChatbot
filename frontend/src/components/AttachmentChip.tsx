import { assetUrl } from '../lib/api'
import { formatBytes, formatDuration, KIND_LABEL } from '../lib/format'
import { CloseIcon } from './icons'
import { KIND_GLYPH } from './kinds'
import type { Attachment } from '../lib/types'

interface Props {
  attachment: Attachment
  onRemove?: () => void
  compact?: boolean
}

export function AttachmentChip({ attachment, onRemove, compact = false }: Props) {
  const duration = formatDuration(attachment.duration_s)
  const isVisual = attachment.kind === 'image' || attachment.kind === 'video'
  const Glyph = KIND_GLYPH[attachment.kind]

  return (
    <div
      className={`glass-thin inline-flex items-center gap-2.5 rounded-xl ${
        compact ? 'max-w-[17rem] py-1.5 pl-1.5 pr-1' : 'py-2.5 pl-2.5 pr-2.5'
      }`}
    >
      {isVisual ? (
        <img
          src={assetUrl(`/api/files/${attachment.file_id}/thumb`)}
          alt=""
          className={`shrink-0 rounded-lg object-cover ${compact ? 'h-8 w-8' : 'h-11 w-11'}`}
          onError={(event) => {
            event.currentTarget.style.visibility = 'hidden'
          }}
        />
      ) : (
        <span
          className={`flex shrink-0 items-center justify-center rounded-lg bg-white/6 text-ink-dim ${
            compact ? 'h-8 w-8' : 'h-11 w-11'
          }`}
        >
          {Glyph ? <Glyph className={compact ? 'h-4 w-4' : 'h-[1.35rem] w-[1.35rem]'} /> : null}
        </span>
      )}

      <div className="min-w-0 flex-1">
        <p className={`truncate font-medium ${compact ? 't-caption' : 't-meta'}`}>
          {attachment.name}
        </p>
        {!compact && (
          <p className="t-caption text-ink-faint">
            {KIND_LABEL[attachment.kind] ?? attachment.kind} · {formatBytes(attachment.size_bytes)}
            {duration ? ` · ${duration}` : ''}
            {attachment.page_count ? ` · ${attachment.page_count} pags` : ''}
          </p>
        )}
      </div>

      {!compact && (
        <a
          href={assetUrl(`/api/files/${attachment.file_id}/raw`)}
          target="_blank"
          rel="noreferrer noopener"
          className="pressable shrink-0 rounded-lg px-2 py-1 t-caption text-ink-dim hover:bg-white/8 hover:text-ink"
        >
          Abrir
        </a>
      )}

      {onRemove && (
        <button
          type="button"
          onClick={onRemove}
          aria-label={`Quitar ${attachment.name}`}
          className="pressable flex h-7 w-7 shrink-0 items-center justify-center rounded-lg text-ink-faint hover:bg-white/8 hover:text-red-300"
        >
          <CloseIcon className="h-3.5 w-3.5" />
        </button>
      )}
    </div>
  )
}
