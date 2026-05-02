import { forwardRef, type TextareaHTMLAttributes } from 'react'

import { cn } from '@/lib/cn'

export const Textarea = forwardRef<HTMLTextAreaElement, TextareaHTMLAttributes<HTMLTextAreaElement>>(
  ({ className, ...props }, ref) => {
    return (
      <textarea
        ref={ref}
        className={cn(
          'w-full rounded-2xl border border-slate-800 bg-slate-950/70 px-3 py-3 text-sm text-slate-100 outline-none transition placeholder:text-slate-500 focus:border-slate-600 focus:ring-2 focus:ring-sky-500/30',
          className,
        )}
        {...props}
      />
    )
  },
)

Textarea.displayName = 'Textarea'
