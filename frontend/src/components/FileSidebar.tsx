import type { SVGProps } from 'react'

import { CloseIcon, SearchIcon, TrashIcon } from './icons'
import { KIND_GLYPH } from './kinds'
import { KIND_LABEL, formatBytes, formatDuration } from '../lib/format'
import type { Attachment } from '../lib/types'

interface Props {
  files: Attachment[]
  activeIds: string[]
  onAttach: (fileId: string) => void
  onDelete: (fileId: string) => void
  onSearch: (query: string) => void
  searchResults: { text: string; name: string | null; score: number | null }[]
  searching: boolean
  onClose: () => void
}

export function FileSidebar({
  files,
  activeIds,
  onAttach,
  onDelete,
  onSearch,
  searchResults,
  searching,
  onClose,
}: Props) {
  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center justify-between px-5 pb-1 pt-5">
        <h2 className="t-title">Archivos analizados</h2>
        <button
          type="button"
          onClick={onClose}
          aria-label="Cerrar panel"
          className="pressable -mr-1.5 flex h-8 w-8 items-center justify-center rounded-lg text-ink-dim hover:bg-white/8 hover:text-ink lg:hidden"
        >
          <CloseIcon className="h-4 w-4" />
        </button>
      </div>

      <div className="px-5 pb-4 pt-3">
        <div className="relative">
          <SearchIcon className="pointer-events-none absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-ink-faint" />
          <input
            type="search"
            placeholder="Buscar en lo analizado"
            onChange={(event) => onSearch(event.target.value)}
            className="glass-thin w-full rounded-xl py-2 pl-9 pr-3 t-meta text-ink outline-none transition-shadow placeholder:text-ink-faint focus:ring-1 focus:ring-brand/45 [&::-webkit-search-cancel-button]:appearance-none"
          />
        </div>

        {searching && <p className="t-caption mt-2.5 text-ink-faint">Buscando…</p>}

        {searchResults.length > 0 && (
          <div className="mt-2.5 flex max-h-64 flex-col gap-1 overflow-y-auto">
            {searchResults.map((hit, index) => (
              <div key={index} className="glass-thin rounded-lg px-2.5 py-2">
                <p className="truncate t-caption font-medium text-brand">
                  {hit.name ?? 'archivo'}
                  {hit.score !== null && ` · ${Math.round(hit.score * 100)}%`}
                </p>
                <p className="mt-0.5 line-clamp-3 t-caption leading-relaxed text-ink-dim">{hit.text}</p>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="flex-1 overflow-y-auto px-3 pb-5">
        {files.length === 0 ? (
          <p className="px-2 py-8 text-center t-meta text-ink-faint">
            Todavia no has subido nada.
            <br />
            Los archivos aparecen aqui y quedan indexados para consultas posteriores.
          </p>
        ) : (
          files.map((file) => {
            const active = activeIds.includes(file.file_id)
            const Glyph = KIND_GLYPH[file.kind] ?? DocumentFallback
            const duration = formatDuration(file.duration_s)
            return (
              <div
                key={file.file_id}
                className={`group mb-0.5 rounded-xl px-2.5 py-2.5 transition-colors ${
                  active ? 'bg-brand/12' : 'hover:bg-white/6'
                }`}
              >
                <div className="flex items-start gap-2.5">
                  <Glyph
                    className={`mt-0.5 h-4 w-4 shrink-0 ${active ? 'text-brand' : 'text-ink-faint'}`}
                  />
                  <div className="min-w-0 flex-1">
                    <p className="truncate t-meta font-medium">{file.name}</p>
                    <p className="t-caption text-ink-faint">
                      {KIND_LABEL[file.kind] ?? file.kind} · {formatBytes(file.size_bytes)}
                      {duration ? ` · ${duration}` : ''}
                    </p>
                  </div>
                </div>

                <div className="mt-1.5 flex gap-1 opacity-0 transition-opacity duration-150 group-hover:opacity-100 focus-within:opacity-100">
                  <button
                    type="button"
                    onClick={() => onAttach(file.file_id)}
                    className={`pressable rounded-lg px-2 py-1 t-caption font-medium transition-colors ${
                      active
                        ? 'text-brand'
                        : 'text-ink-dim hover:bg-white/8 hover:text-ink'
                    }`}
                  >
                    {active ? 'Añadido' : 'Adjuntar'}
                  </button>
                  <button
                    type="button"
                    onClick={() => onDelete(file.file_id)}
                    aria-label={`Borrar ${file.name}`}
                    className="pressable ml-auto flex items-center gap-1 rounded-lg px-2 py-1 t-caption text-ink-faint transition-colors hover:bg-red-500/14 hover:text-red-300"
                  >
                    <TrashIcon className="h-3 w-3" />
                    Borrar
                  </button>
                </div>
              </div>
            )
          })
        )}
      </div>
    </div>
  )
}

function DocumentFallback(props: SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.7} aria-hidden="true" {...props}>
      <path d="M13.5 3H7a2.5 2.5 0 0 0-2.5 2.5v13A2.5 2.5 0 0 0 7 21h10a2.5 2.5 0 0 0 2.5-2.5V9z" />
      <path d="M13.5 3v6H19.5" />
    </svg>
  )
}
