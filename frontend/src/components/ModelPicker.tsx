import type { ModelInfo } from '../lib/types'

interface Props {
  models: ModelInfo[]
  value: string
  onChange: (model: string) => void
}

const SHORT: Record<string, string> = {
  'nvidia/nemotron-3-super-120b-a12b': 'Super 120B',
  'nvidia/nemotron-3-ultra-550b-a55b': 'Ultra 550B',
  'nvidia/nemotron-3.5-lightning-30b-a3b': 'Lightning 30B',
}

export function ModelPicker({ models, value, onChange }: Props) {
  const textModels = models.filter((model) => model.role === 'text')
  if (textModels.length === 0) return null

  const active = textModels.find((model) => model.id === value)

  return (
    <div className="relative">
      <select
        id="model-picker"
        value={value}
        onChange={(event) => onChange(event.target.value)}
        title={active?.description}
        aria-label="Modelo de texto"
        className="pressable cursor-pointer appearance-none rounded-xl border-0 bg-white/6 py-2 pl-3 pr-8 t-meta font-medium text-ink outline-none hover:bg-white/10 focus:ring-1 focus:ring-brand/45"
      >
        {textModels.map((model) => (
          <option key={model.id} value={model.id} title={model.description} className="bg-panel text-ink">
            {SHORT[model.id] ?? model.label}
          </option>
        ))}
      </select>
      <svg
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth={2.2}
        strokeLinecap="round"
        aria-hidden="true"
        className="pointer-events-none absolute right-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-ink-faint"
      >
        <path d="m6.5 9.5 5.5 5.5 5.5-5.5" />
      </svg>
    </div>
  )
}
