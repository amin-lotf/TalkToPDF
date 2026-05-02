import type { ReactNode } from 'react'

import { cn } from '@/lib/cn'

interface EmptyStateProps {
  icon?: ReactNode
  title: string
  description: string
  action?: ReactNode
  className?: string
}

export function EmptyState({ action, className, description, icon, title }: EmptyStateProps) {
  return (
    <div
      className={cn(
        'flex min-h-[280px] flex-col items-center justify-center rounded-3xl border border-dashed border-slate-800 bg-slate-900/30 px-6 py-10 text-center',
        className,
      )}
    >
      {icon ? <div className="mb-4 rounded-2xl bg-slate-900/80 p-4 text-slate-200">{icon}</div> : null}
      <h3 className="text-lg font-semibold text-slate-100">{title}</h3>
      <p className="mt-2 max-w-md text-sm text-slate-400">{description}</p>
      {action ? <div className="mt-6">{action}</div> : null}
    </div>
  )
}
