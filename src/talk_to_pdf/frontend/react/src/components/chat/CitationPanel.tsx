import { ArrowLeft, Bot, FileSearch, Link2, Timer, Waypoints } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

import { Button } from '@/components/ui/Button'
import { EmptyState } from '@/components/ui/EmptyState'
import { Panel } from '@/components/ui/Panel'
import { cn } from '@/lib/cn'
import { formatDateTime, formatDuration, formatNumber, titleCase } from '@/lib/format'
import type { ChatMessage } from '@/types/chat'

interface CitationPanelProps {
  message: ChatMessage | null
  onBack?: () => void
}

function isScalarValue(value: unknown): value is string | number | boolean {
  return typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean'
}

function isRecordValue(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === 'object' && !Array.isArray(value)
}

function formatScalarValue(value: string | number | boolean) {
  if (typeof value === 'boolean') {
    return value ? 'Yes' : 'No'
  }

  return String(value)
}

function formatScore(value: number | null | undefined) {
  return value != null ? value.toFixed(3) : 'N/A'
}

function summarizeMetadataValue(value: unknown) {
  if (value == null) {
    return 'Unavailable'
  }

  if (isScalarValue(value)) {
    return formatScalarValue(value)
  }

  if (Array.isArray(value)) {
    if (!value.length) {
      return 'Empty list'
    }

    if (value.every(isScalarValue)) {
      return `${value.length} ${value.length === 1 ? 'value' : 'values'}`
    }

    return `${value.length} ${value.length === 1 ? 'item' : 'items'}`
  }

  if (isRecordValue(value)) {
    const entries = Object.keys(value).length
    return `${entries} ${entries === 1 ? 'field' : 'fields'}`
  }

  return String(value)
}

function MetadataValue({ value }: { value: unknown }) {
  if (value == null) {
    return <span className="text-xs text-slate-500">Unavailable</span>
  }

  if (isScalarValue(value)) {
    return <p className="whitespace-pre-wrap break-words text-sm leading-5 text-slate-200">{formatScalarValue(value)}</p>
  }

  if (Array.isArray(value)) {
    if (!value.length) {
      return <span className="text-xs text-slate-500">None</span>
    }

    if (value.every(isScalarValue)) {
      return (
        <div className="flex flex-wrap gap-1.5">
          {value.map((entry, index) => (
            <span
              key={`${formatScalarValue(entry)}-${index}`}
              className="inline-flex items-center rounded-full border border-slate-700/80 bg-slate-950/80 px-2 py-0.5 text-xs text-slate-300"
            >
              {formatScalarValue(entry)}
            </span>
          ))}
        </div>
      )
    }

    return (
      <details className="group rounded-lg border border-slate-800/80 bg-slate-950/70 px-2.5 py-2">
        <summary className="flex cursor-pointer list-none items-center justify-between gap-3 text-xs text-slate-300">
          <span>{summarizeMetadataValue(value)}</span>
          <span className="text-slate-500 group-open:hidden">Expand</span>
          <span className="hidden text-slate-500 group-open:inline">Hide</span>
        </summary>
        <div className="mt-2 space-y-1.5">
          {value.map((entry, index) => (
            <div key={index} className="rounded-lg border border-slate-800/70 bg-slate-950/70 px-2 py-1.5">
              <p className="text-[10px] font-medium uppercase tracking-[0.16em] text-slate-500">Item {index + 1}</p>
              <div className="mt-1">
                <MetadataValue value={entry} />
              </div>
            </div>
          ))}
        </div>
      </details>
    )
  }

  if (isRecordValue(value)) {
    const entries = Object.entries(value)

    if (!entries.length) {
      return <span className="text-xs text-slate-500">None</span>
    }

    if (entries.every(([, entryValue]) => entryValue == null || isScalarValue(entryValue))) {
      return (
        <div className="flex flex-wrap gap-1.5">
          {entries.map(([entryKey, entryValue]) => (
            <span
              key={entryKey}
              className="inline-flex items-center gap-1 rounded-full border border-slate-700/80 bg-slate-950/80 px-2 py-0.5 text-xs text-slate-300"
            >
              <span className="text-slate-500">{titleCase(entryKey)}</span>
              <span>
                {entryValue == null
                  ? 'Unavailable'
                  : isScalarValue(entryValue)
                    ? formatScalarValue(entryValue)
                    : 'Unavailable'}
              </span>
            </span>
          ))}
        </div>
      )
    }

    return (
      <details className="group rounded-lg border border-slate-800/80 bg-slate-950/70 px-2.5 py-2">
        <summary className="flex cursor-pointer list-none items-center justify-between gap-3 text-xs text-slate-300">
          <span>{summarizeMetadataValue(value)}</span>
          <span className="text-slate-500 group-open:hidden">Expand</span>
          <span className="hidden text-slate-500 group-open:inline">Hide</span>
        </summary>
        <dl className="mt-2 space-y-1.5">
          {entries.map(([entryKey, entryValue]) => (
            <div key={entryKey} className="rounded-lg border border-slate-800/70 bg-slate-950/70 px-2 py-1.5">
              <dt className="text-[10px] font-medium uppercase tracking-[0.16em] text-slate-500">
                {titleCase(entryKey)}
              </dt>
              <dd className="mt-1">
                <MetadataValue value={entryValue} />
              </dd>
            </div>
          ))}
        </dl>
      </details>
    )
  }

  return <p className="whitespace-pre-wrap break-words text-sm leading-5 text-slate-200">{String(value)}</p>
}

export function CitationPanel({ message, onBack }: CitationPanelProps) {
  if (!message || (!message.citations && !message.metrics)) {
    return (
      <EmptyState
        icon={<FileSearch className="h-6 w-6" />}
        title="Answer details"
        description="Open the source badge on an assistant response to inspect the answer, citations, and timing."
        className="min-h-[360px]"
      />
    )
  }

  const citations = message.citations
  const metrics = message.metrics
  const sourceCount = citations?.chunks.length ?? 0

  return (
    <div className="space-y-6">
      <Panel
        title="Answer"
        description={formatDateTime(message.created_at)}
        action={
          onBack ? (
            <Button variant="secondary" size="sm" onClick={onBack}>
              <ArrowLeft className="h-4 w-4" />
              Back to chat
            </Button>
          ) : undefined
        }
      >
        <div className="rounded-2xl border border-slate-800 bg-slate-950/60 px-5 py-5">
          <div className="flex items-center gap-3">
            <div className="rounded-2xl bg-slate-900 p-3 text-slate-200">
              <Bot className="h-5 w-5" />
            </div>
            <div>
              <p className="text-sm font-medium text-slate-100">Assistant answer</p>
              <p className="text-xs text-slate-500">
                {sourceCount > 0
                  ? `${sourceCount} ${sourceCount === 1 ? 'source' : 'sources'} attached`
                  : 'No citation sources were stored for this answer.'}
              </p>
            </div>
          </div>

          <div className="mt-5 markdown-body prose prose-invert max-w-none prose-p:leading-7 prose-pre:bg-slate-950">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{message.content}</ReactMarkdown>
          </div>
        </div>
      </Panel>

      <Panel
        title="Details"
        description="Retrieval evidence and backend metrics for this answer."
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
              <p className="mt-1 text-xs text-slate-400">
                Generation {formatDuration(metrics.latency.reply_generation)}
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
                <p className="mt-2 text-sm text-slate-200">
                  {citations.rewritten_query ?? citations.original_query ?? 'N/A'}
                </p>
                <p className="mt-1 text-sm text-slate-400">
                  {citations.rewrite_strategy ?? 'No strategy metadata'}
                </p>
              </div>
            </div>

            {citations.rewritten_queries?.length ? (
              <div className="space-y-2">
                <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Retrieval queries</p>
                <div className="space-y-2">
                  {citations.rewritten_queries.map((query, index) => (
                    <div
                      key={`${query}-${index}`}
                      className="rounded-2xl border border-slate-800 bg-slate-950/60 px-4 py-3 text-sm text-slate-200"
                    >
                      {index + 1}. {query}
                    </div>
                  ))}
                </div>
              </div>
            ) : null}

            <div className="space-y-3">
              <div className="flex items-center justify-between gap-3">
                <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Sources</p>
                <p className="text-sm text-slate-400">
                  {sourceCount} {sourceCount === 1 ? 'source' : 'sources'}
                </p>
              </div>

              <div className="space-y-2.5">
                {citations.chunks.length ? (
                  citations.chunks.map((chunk, index) => (
                    <div key={chunk.chunk_id} className="rounded-2xl border border-slate-800 bg-slate-950/60 px-4 py-3.5">
                      <div className="flex flex-wrap items-start justify-between gap-2.5">
                        <div className="space-y-2">
                          <p className="text-sm font-semibold text-slate-100">Source {index + 1}</p>
                          <div className="flex flex-wrap gap-2">
                            {chunk.matched_by?.length ? (
                              <span className="inline-flex items-center gap-1 rounded-full border border-slate-700/80 bg-slate-900/70 px-2.5 py-1 text-xs text-slate-300">
                                <Link2 className="h-3 w-3" />
                                Queries {chunk.matched_by.map((value) => value + 1).join(', ')}
                              </span>
                            ) : null}
                            <span className="inline-flex items-center rounded-full border border-slate-800 bg-slate-900/70 px-2.5 py-1 text-xs text-slate-500">
                              {chunk.chunk_id.slice(0, 8)}
                            </span>
                          </div>
                        </div>

                        <div className="min-w-[88px] rounded-xl border border-cyan-500/30 bg-cyan-500/10 px-3 py-2 text-right">
                          <p className="text-[11px] font-medium uppercase tracking-[0.16em] text-cyan-200/80">Score</p>
                          <p className="mt-1 text-lg font-semibold leading-none text-cyan-100">
                            {formatScore(chunk.score)}
                          </p>
                        </div>
                      </div>

                      {chunk.content ? (
                        <div className="mt-2.5 rounded-xl border border-slate-800/80 bg-slate-900/40 px-3 py-2.5">
                          <p className="whitespace-pre-wrap text-sm leading-5 text-slate-200">{chunk.content}</p>
                        </div>
                      ) : null}

                      {chunk.citation ? (
                        <dl className="mt-2.5 grid gap-2 md:grid-cols-2 xl:grid-cols-3">
                          {Object.entries(chunk.citation).map(([key, value]) => (
                            <div
                              key={key}
                              className={cn('rounded-xl border border-slate-800/80 bg-slate-900/55 px-3 py-2')}
                            >
                              <dt className="text-[10px] font-medium uppercase tracking-[0.16em] text-slate-500">
                                {titleCase(key)}
                              </dt>
                              <dd className="mt-1">
                                <MetadataValue value={value} />
                              </dd>
                            </div>
                          ))}
                        </dl>
                      ) : (
                        <div className="mt-2.5 rounded-xl border border-dashed border-slate-800 px-3 py-2 text-sm text-slate-500">
                          No citation metadata was stored for this source.
                        </div>
                      )}
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
        ) : (
          <div className="rounded-2xl border border-dashed border-slate-800 px-4 py-3 text-sm text-slate-500">
            No citation metadata was stored for this answer.
          </div>
        )}
      </Panel>
    </div>
  )
}
