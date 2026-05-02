import type { ButtonHTMLAttributes, PropsWithChildren } from 'react'

import { Spinner } from '@/components/ui/Spinner'
import { cn } from '@/lib/cn'

type ButtonVariant = 'primary' | 'secondary' | 'ghost' | 'danger'
type ButtonSize = 'default' | 'sm' | 'icon'

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant
  size?: ButtonSize
  loading?: boolean
}

const variantClasses: Record<ButtonVariant, string> = {
  primary:
    'bg-sky-500 text-slate-950 hover:bg-sky-400 focus-visible:outline-sky-300 disabled:bg-slate-700 disabled:text-slate-300',
  secondary:
    'bg-slate-800 text-slate-50 hover:bg-slate-700 focus-visible:outline-slate-400 disabled:bg-slate-900 disabled:text-slate-500',
  ghost:
    'bg-transparent text-slate-300 hover:bg-slate-900 hover:text-white focus-visible:outline-slate-500 disabled:text-slate-600',
  danger:
    'bg-rose-500/90 text-white hover:bg-rose-400 focus-visible:outline-rose-300 disabled:bg-slate-700 disabled:text-slate-300',
}

const sizeClasses: Record<ButtonSize, string> = {
  default: 'h-11 px-4 text-sm',
  sm: 'h-9 px-3 text-sm',
  icon: 'h-10 w-10 justify-center p-0',
}

export function Button({
  children,
  className,
  disabled,
  loading = false,
  size = 'default',
  type = 'button',
  variant = 'primary',
  ...props
}: PropsWithChildren<ButtonProps>) {
  return (
    <button
      type={type}
      className={cn(
        'inline-flex items-center justify-center gap-2 rounded-xl border border-transparent font-medium transition focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 disabled:cursor-not-allowed',
        variantClasses[variant],
        sizeClasses[size],
        className,
      )}
      disabled={disabled || loading}
      {...props}
    >
      {loading ? <Spinner className="h-4 w-4" /> : null}
      {children}
    </button>
  )
}
