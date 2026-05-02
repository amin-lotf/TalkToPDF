import type { PropsWithChildren, ReactNode } from 'react'

import { Badge } from '@/components/ui/Badge'

interface AuthShellProps {
  footer: ReactNode
  subtitle: string
  title: string
}

export function AuthShell({
  children,
  footer,
  subtitle,
  title,
}: PropsWithChildren<AuthShellProps>) {
  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 lg:grid lg:grid-cols-[1.05fr_0.95fr]">
      <div className="hidden border-r border-slate-800/80 bg-slate-950/80 px-12 py-12 lg:flex lg:flex-col lg:justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.28em] text-sky-300">TalkToPDF</p>
          <h1 className="mt-6 max-w-xl text-4xl font-semibold leading-tight text-white">
            Precise answers over private PDFs with retrieval you can inspect.
          </h1>
          <p className="mt-4 max-w-lg text-base leading-7 text-slate-400">
            FastAPI, Grobid extraction, hybrid retrieval, query rewriting, optional reranking, streamed answers, and
            persisted citations.
          </p>
        </div>

        <div className="space-y-3">
          <div className="flex flex-wrap gap-2">
            <Badge tone="success">JWT auth</Badge>
            <Badge tone="default">Async indexing</Badge>
            <Badge tone="default">pgvector + FTS</Badge>
            <Badge tone="warning">Streaming answers</Badge>
          </div>
          <p className="max-w-lg text-sm leading-6 text-slate-500">
            The React frontend mirrors the existing backend behavior and coexists with the Streamlit UI already in the
            repository.
          </p>
        </div>
      </div>

      <div className="flex items-center justify-center px-6 py-10 sm:px-8">
        <div className="w-full max-w-md rounded-[2rem] border border-slate-800 bg-slate-900/80 p-8 shadow-panel backdrop-blur">
          <div>
            <p className="text-sm font-medium uppercase tracking-[0.24em] text-slate-500">Workspace access</p>
            <h2 className="mt-4 text-3xl font-semibold text-white">{title}</h2>
            <p className="mt-3 text-sm leading-6 text-slate-400">{subtitle}</p>
          </div>

          <div className="mt-8">{children}</div>

          <div className="mt-8 border-t border-slate-800 pt-6 text-sm text-slate-400">{footer}</div>
        </div>
      </div>
    </div>
  )
}
