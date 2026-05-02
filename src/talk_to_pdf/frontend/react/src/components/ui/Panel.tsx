import type { PropsWithChildren, ReactNode } from 'react'

import { cn } from '@/lib/cn'

interface PanelProps {
  title?: ReactNode
  description?: ReactNode
  action?: ReactNode
  className?: string
  bodyClassName?: string
}

export function Panel({
  action,
  bodyClassName,
  children,
  className,
  description,
  title,
}: PropsWithChildren<PanelProps>) {
  return (
    <section
      className={cn(
        'rounded-3xl border border-slate-800/90 bg-slate-900/70 shadow-panel backdrop-blur',
        className,
      )}
    >
      {title || description || action ? (
        <header className="flex items-start justify-between gap-4 border-b border-slate-800/80 px-5 py-4">
          <div className="space-y-1">
            {title ? <h2 className="text-sm font-semibold text-slate-100">{title}</h2> : null}
            {description ? <p className="text-sm text-slate-400">{description}</p> : null}
          </div>
          {action}
        </header>
      ) : null}
      <div className={cn('px-5 py-4', bodyClassName)}>{children}</div>
    </section>
  )
}
