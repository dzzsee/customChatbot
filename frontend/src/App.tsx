import { useState } from 'react'

import { Composer } from './components/Composer'
import { Drawer } from './components/Drawer'
import { FileSidebar } from './components/FileSidebar'
import { HealthBadge } from './components/HealthBadge'
import { MessageList } from './components/MessageList'
import { ModelPicker } from './components/ModelPicker'
import { PlusIcon, SidebarIcon } from './components/icons'
import { useChatbot } from './hooks/useChatbot'

export default function App() {
  const chat = useChatbot()
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const apiKeyMissing = chat.health !== null && !chat.health.api_key_configured
  const activeIds = chat.attachments.map((item) => item.file_id)

  return (
    <div className="app-canvas flex h-full overflow-hidden">
      <Drawer open={sidebarOpen} onClose={() => setSidebarOpen(false)}>
        <FileSidebar
          files={chat.files}
          activeIds={activeIds}
          onAttach={chat.attachExisting}
          onDelete={(id) => void chat.removeFile(id)}
          onSearch={chat.runSearch}
          searchResults={chat.searchHits}
          searching={chat.searching}
          onClose={() => setSidebarOpen(false)}
        />
      </Drawer>

      <div className="flex min-w-0 flex-1 flex-col">
        {/* Barra de vidrio flotante: no toca los bordes, la conversacion pasa por debajo. */}
        <div className="chrome z-20 shrink-0 px-3 pt-3 sm:px-5 sm:pt-4">
          <header className="glass mx-auto flex max-w-4xl items-center gap-2.5 rounded-2xl px-3 py-2.5 sm:gap-3 sm:px-4">
            <button
              type="button"
              onClick={() => setSidebarOpen(true)}
              aria-label="Abrir panel de archivos"
              className="pressable flex h-9 w-9 shrink-0 items-center justify-center rounded-xl text-ink-dim hover:bg-white/8 hover:text-ink lg:hidden"
            >
              <SidebarIcon className="h-[1.15rem] w-[1.15rem]" />
            </button>

            <div className="min-w-0 flex-1">
              <h1 className="t-title truncate">Nemotron Chat</h1>
              <p className="t-caption truncate text-ink-faint">NVIDIA NIM · texto, imagen, video y voz</p>
            </div>

            <HealthBadge health={chat.health} online={chat.online} />
            <ModelPicker models={chat.models} value={chat.model} onChange={chat.setModel} />

            <button
              type="button"
              onClick={chat.clearChat}
              title="Nueva conversacion"
              aria-label="Nueva conversacion"
              className="pressable flex h-9 w-9 shrink-0 items-center justify-center rounded-xl text-ink-dim hover:bg-white/8 hover:text-ink sm:w-auto sm:gap-1.5 sm:px-3"
            >
              <PlusIcon className="h-[1.15rem] w-[1.15rem]" />
              <span className="t-caption hidden sm:inline">Nueva</span>
            </button>
          </header>
        </div>

        {chat.notice && (
          <div className="chrome z-20 shrink-0 px-3 pt-2.5 sm:px-5">
            <div
              role="status"
              className="glass mx-auto flex max-w-4xl items-start gap-2 rounded-xl border border-amber-400/25 px-3.5 py-2.5 t-meta text-amber-200"
            >
              <span className="flex-1">{chat.notice}</span>
              <button
                type="button"
                onClick={() => chat.setNotice(null)}
                aria-label="Cerrar aviso"
                className="pressable -mr-1 -mt-0.5 rounded-lg p-1 text-amber-300 hover:bg-white/10"
              >
                <svg viewBox="0 0 24 24" className="h-3.5 w-3.5" stroke="currentColor" strokeWidth={2.2} strokeLinecap="round" aria-hidden="true">
                  <path d="m6.5 6.5 11 11M17.5 6.5l-11 11" />
                </svg>
              </button>
            </div>
          </div>
        )}

        <MessageList messages={chat.messages} busy={chat.busy} />

        <div className="chrome z-20 shrink-0 px-3 pb-3 pt-1 sm:px-5 sm:pb-4">
          <Composer
            value={chat.input}
            onChange={chat.setInput}
            attachments={chat.attachments}
            onRemoveAttachment={chat.removeAttachment}
            uploads={chat.uploads}
            onPickFiles={(files) => void chat.uploadFiles(files)}
            onStop={chat.stop}
            onSubmit={chat.send}
            busy={chat.busy}
            disabled={apiKeyMissing}
          />
        </div>
      </div>
    </div>
  )
}
