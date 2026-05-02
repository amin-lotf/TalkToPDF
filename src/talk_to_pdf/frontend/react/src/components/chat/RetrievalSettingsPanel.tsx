import { SlidersHorizontal } from 'lucide-react'

import { Input } from '@/components/ui/Input'
import { Panel } from '@/components/ui/Panel'

export interface RetrievalSettings {
  topK: number
  topN: number
  rerankTimeoutS: number
}

interface RetrievalSettingsPanelProps {
  disabled?: boolean
  onChange: (next: RetrievalSettings) => void
  value: RetrievalSettings
}

export function RetrievalSettingsPanel({
  disabled = false,
  onChange,
  value,
}: RetrievalSettingsPanelProps) {
  return (
    <Panel
      title="Retrieval Settings"
      description="These map directly to the current `/query` request contract."
      action={<SlidersHorizontal className="h-4 w-4 text-slate-500" />}
    >
      <div className="grid gap-4 sm:grid-cols-3">
        <label className="space-y-2 text-sm">
          <span className="text-slate-400">Top-k</span>
          <Input
            type="number"
            min={1}
            max={50}
            value={value.topK}
            disabled={disabled}
            onChange={(event) =>
              onChange({
                ...value,
                topK: Math.max(1, Math.min(50, Number(event.target.value) || 1)),
                topN: Math.min(value.topN, Math.max(1, Math.min(50, Number(event.target.value) || 1))),
              })
            }
          />
        </label>
        <label className="space-y-2 text-sm">
          <span className="text-slate-400">Top-n</span>
          <Input
            type="number"
            min={1}
            max={Math.max(1, value.topK)}
            value={value.topN}
            disabled={disabled}
            onChange={(event) =>
              onChange({
                ...value,
                topN: Math.max(1, Math.min(value.topK, Number(event.target.value) || 1)),
              })
            }
          />
        </label>
        <label className="space-y-2 text-sm">
          <span className="text-slate-400">Rerank timeout (s)</span>
          <Input
            type="number"
            min={0}
            max={20}
            step="0.1"
            value={value.rerankTimeoutS}
            disabled={disabled}
            onChange={(event) =>
              onChange({
                ...value,
                rerankTimeoutS: Math.max(0, Math.min(20, Number(event.target.value) || 0)),
              })
            }
          />
        </label>
      </div>
    </Panel>
  )
}
