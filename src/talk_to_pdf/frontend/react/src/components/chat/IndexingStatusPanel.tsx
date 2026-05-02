import { AlertCircle, CircleStop, FileText, Play } from 'lucide-react'

import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { Panel } from '@/components/ui/Panel'
import { Spinner } from '@/components/ui/Spinner'
import { formatDateTime, formatFileSize } from '@/lib/format'
import type { IndexingStatus } from '@/types/indexing'
import type { Project } from '@/types/project'

interface IndexingStatusPanelProps {
  error: string | null
  loading: boolean
  onCancel: (() => Promise<void>) | null
  onStart: (() => Promise<void>) | null
  project: Project | null
  status: IndexingStatus | null
}

function getStatusTone(status?: string | null) {
  const normalized = (status ?? '').toLowerCase()
  if (normalized === 'ready' || normalized === 'completed') {
    return 'success' as const
  }
  if (normalized === 'failed' || normalized === 'error' || normalized === 'cancelled' || normalized === 'canceled') {
    return 'danger' as const
  }
  if (normalized === 'pending' || normalized === 'running' || normalized === 'queued') {
    return 'warning' as const
  }
  return 'default' as const
}

export function IndexingStatusPanel({
  error,
  loading,
  onCancel,
  onStart,
  project,
  status,
}: IndexingStatusPanelProps) {
  const progress = Math.max(0, Math.min(100, status?.progress ?? 0))

  return (
    <Panel
      title="Project Status"
      description={project ? project.primary_document.original_filename : 'Select a project to inspect indexing.'}
      action={
        <Badge tone={getStatusTone(status?.status)}>{status?.status ?? (project ? 'Not indexed' : 'Idle')}</Badge>
      }
      bodyClassName="space-y-4"
    >
      {project ? (
        <div className="rounded-2xl border border-slate-800 bg-slate-950/60 px-4 py-4">
          <div className="flex items-start gap-3">
            <div className="rounded-2xl bg-slate-900 p-3 text-sky-300">
              <FileText className="h-5 w-5" />
            </div>
            <div className="min-w-0">
              <p className="truncate text-sm font-medium text-slate-100">{project.primary_document.original_filename}</p>
              <p className="mt-1 text-xs text-slate-500">{formatFileSize(project.primary_document.size_bytes)}</p>
              <p className="mt-1 text-xs text-slate-500">Uploaded {formatDateTime(project.primary_document.uploaded_at)}</p>
            </div>
          </div>
        </div>
      ) : null}

      {status ? (
        <>
          <div className="space-y-2">
            <div className="flex items-center justify-between text-xs text-slate-400">
              <span>Progress</span>
              <span>{progress}%</span>
            </div>
            <div className="h-2 rounded-full bg-slate-900">
              <div className="h-2 rounded-full bg-sky-400 transition-all" style={{ width: `${progress}%` }} />
            </div>
          </div>

          {status.message ? (
            <div className="rounded-2xl border border-slate-800 bg-slate-950/60 px-4 py-3 text-sm text-slate-300">
              {status.message}
            </div>
          ) : null}

          {status.cancel_requested ? (
            <div className="rounded-2xl border border-amber-500/20 bg-amber-500/10 px-4 py-3 text-sm text-amber-100">
              Cancellation has been requested.
            </div>
          ) : null}

          {status.error ? (
            <div className="rounded-2xl border border-rose-500/20 bg-rose-500/10 px-4 py-3 text-sm text-rose-100">
              {status.error}
            </div>
          ) : null}
        </>
      ) : loading ? (
        <div className="flex items-center gap-3 rounded-2xl border border-slate-800 bg-slate-950/60 px-4 py-3 text-sm text-slate-400">
          <Spinner />
          Loading project status…
        </div>
      ) : (
        <div className="rounded-2xl border border-dashed border-slate-800 px-4 py-3 text-sm text-slate-500">
          No indexing job has been recorded for this project yet.
        </div>
      )}

      {error ? (
        <div className="flex items-start gap-2 rounded-2xl border border-rose-500/20 bg-rose-500/10 px-4 py-3 text-sm text-rose-100">
          <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
          <span>{error}</span>
        </div>
      ) : null}

      <div className="flex flex-wrap gap-2">
        {onStart ? (
          <Button size="sm" onClick={() => void onStart()}>
            <Play className="h-4 w-4" />
            Start indexing
          </Button>
        ) : null}
        {onCancel ? (
          <Button variant="danger" size="sm" onClick={() => void onCancel()}>
            <CircleStop className="h-4 w-4" />
            Cancel
          </Button>
        ) : null}
      </div>
    </Panel>
  )
}
