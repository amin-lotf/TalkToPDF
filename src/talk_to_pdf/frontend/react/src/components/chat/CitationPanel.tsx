import { FileSearch, Link2, Timer, Waypoints } from 'lucide-react'

import { EmptyState } from '@/components/ui/EmptyState'
import { Panel } from '@/components/ui/Panel'
import { formatDuration, formatNumber, titleCase } from '@/lib/format'
import type { ChatMessage } from '@/types/chat'

interface CitationPanelProps {
  message: ChatMessage | null
}

function formatValue(value: unknown) {
  if (value == null) {
    return 'Unavailable'
  }
  if (Array.isArray(value)) {
    return value.join(', ')
  }
  if (typeof value === 'object') {
    return JSON.stringify(value)
  }
  return String(value)
}

export function CitationPanel({ message }: CitationPanelProps) {
  if (!message || (!message.citations && !message.metrics)) {
    return (
      <EmptyState
        icon={<FileSearch className="h-6 w-6" />}
        title="Answer details"
        description="Select an assistant response to inspect retrieval chunks, citations, and timing."
        className="min-h-[360px]"
      />
    )
  }

  const citations = message.citations
  const metrics = message.metrics

  return (
    <Panel
      title="Answer Details"
      description="Retrieval evidence and backend metrics from the persisted assistant message."
      bodyClassName="space-y-6"
    >
      {metrics ? (
        <div className="grid gap-3 sm:grid-cols-2">
          <div className="rounded-2xl border border-slate-800 bg-slate-950/60 px-4 py-3">
            <p className="text-xs uppercase tracking-[0.2em] text-slate-500">Tokens</p>
            <p className="mt-2 text-lg font-semibold text-slate-100">{formatNumber(metrics.tokens.total)}</p>
            <p className="mt-1 text-xs text-slate-400">
              Prompt {formatNumber(metrics.tokens.prompt.total)} · Completion {formatNumber(metrics.tokens.completion)}
            </p>
          </div>
          <div className="rounded-2xl border border-slate-800 bg-slate-950/60 px-4 py-3">
            <p className="text-xs uppercase tracking-[0.2em] text-slate-500">Latency</p>
            <p className="mt-2 text-lg font-semibold text-slate-100">{formatDuration(metrics.latency.total)}</p>
            <p className="mt-1 text-xs text-slate-400">
              Rewrite {formatDuration(metrics.latency.query_rewriting)} · Retrieval{' '}
              {formatDuration(metrics.latency.retrieval)}
            </p>
          </div>
        </div>
      ) : null}

      {citations ? (
        <>
          <div className="grid gap-3 sm:grid-cols-2">
            <div className="rounded-2xl border border-slate-800 bg-slate-950/60 px-4 py-3">
              <p className="flex items-center gap-2 text-xs uppercase tracking-[0.2em] text-slate-500">
                <Waypoints className="h-3.5 w-3.5" />
                Retrieval
              </p>
              <p className="mt-2 text-sm text-slate-200">Metric: {citations.metric ?? 'Unavailable'}</p>
              <p className="mt-1 text-sm text-slate-200">Top-k: {formatNumber(citations.top_k)}</p>
              <p className="mt-1 text-sm text-slate-400">Model: {citations.model ?? 'Unavailable'}</p>
            </div>
            <div className="rounded-2xl border border-slate-800 bg-slate-950/60 px-4 py-3">
              <p className="flex items-center gap-2 text-xs uppercase tracking-[0.2em] text-slate-500">
                <Timer className="h-3.5 w-3.5" />
                Rewrite
              </p>
              <p className="mt-2 text-sm text-slate-200">{citations.rewritten_query ?? citations.original_query ?? 'N/A'}</p>
              <p className="mt-1 text-sm text-slate-400">{citations.rewrite_strategy ?? 'No strategy metadata'}</p>
            </div>
          </div>

          {citations.rewritten_queries?.length ? (
            <div className="space-y-2">
              <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Retrieval queries</p>
              <div className="space-y-2">
                {citations.rewritten_queries.map((query, index) => (
                  <div key={`${query}-${index}`} className="rounded-2xl border border-slate-800 bg-slate-950/60 px-4 py-3 text-sm text-slate-200">
                    {index + 1}. {query}
                  </div>
                ))}
              </div>
            </div>
          ) : null}

          <div className="space-y-3">
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Sources</p>
            <div className="space-y-3">
              {citations.chunks.length ? (
                citations.chunks.map((chunk, index) => (
                  <div key={chunk.chunk_id} className="rounded-2xl border border-slate-800 bg-slate-950/60 px-4 py-4">
                    <div className="flex flex-wrap items-center justify-between gap-3">
                      <p className="text-sm font-medium text-slate-100">Source {index + 1}</p>
                      <p className="text-xs text-slate-400">
                        Score {chunk.score != null ? chunk.score.toFixed(3) : 'Unavailable'}
                      </p>
                    </div>

                    <p className="mt-3 whitespace-pre-wrap text-sm leading-6 text-slate-200">
                      {chunk.content || 'Chunk text was not persisted by the backend.'}
                    </p>

                    <div className="mt-4 flex flex-wrap gap-2">
                      {chunk.matched_by?.length ? (
                        <span className="inline-flex items-center gap-1 rounded-full border border-slate-700 px-2.5 py-1 text-xs text-slate-300">
                          <Link2 className="h-3 w-3" />
                          Queries {chunk.matched_by.map((value) => value + 1).join(', ')}
                        </span>
                      ) : null}
                    </div>

                    {chunk.citation ? (
                      <dl className="mt-4 grid gap-3 sm:grid-cols-2">
                        {Object.entries(chunk.citation).map(([key, value]) => (
                          <div key={key} className="rounded-2xl border border-slate-800/80 bg-slate-900/70 px-3 py-3">
                            <dt className="text-xs uppercase tracking-[0.18em] text-slate-500">{titleCase(key)}</dt>
                            <dd className="mt-1 text-sm text-slate-200">{formatValue(value)}</dd>
                          </div>
                        ))}
                      </dl>
                    ) : null}
                  </div>
                ))
              ) : (
                <div className="rounded-2xl border border-dashed border-slate-800 px-4 py-3 text-sm text-slate-500">
                  No citation chunks were returned with this answer.
                </div>
              )}
            </div>
          </div>
        </>
      ) : null}
    </Panel>
  )
}
