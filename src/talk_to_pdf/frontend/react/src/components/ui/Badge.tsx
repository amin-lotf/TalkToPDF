import type { PropsWithChildren } from 'react'

import { cn } from '@/lib/cn'

interface BadgeProps {
  tone?: 'default' | 'success' | 'warning' | 'danger'
  className?: string
}

const toneClasses = {
  default: 'border-slate-800 bg-slate-900 text-slate-300',
  success: 'border-emerald-500/30 bg-emerald-500/10 text-emerald-200',
  warning: 'border-amber-500/30 bg-amber-500/10 text-amber-100',
  danger: 'border-rose-500/30 bg-rose-500/10 text-rose-100',
}

export function Badge({ children, className, tone = 'default' }: PropsWithChildren<BadgeProps>) {
  return (
    <span
      className={cn(
        'inline-flex items-center rounded-full border px-2.5 py-1 text-xs font-medium',
        toneClasses[tone],
        className,
      )}
    >
      {children}
    </span>
  )
}
