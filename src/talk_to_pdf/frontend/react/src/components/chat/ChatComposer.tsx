import { ArrowUp } from 'lucide-react'
import { useEffect, useRef } from 'react'

import { Button } from '@/components/ui/Button'
import { Textarea } from '@/components/ui/Textarea'

interface ChatComposerProps {
  disabled?: boolean
  loading?: boolean
  onChange: (value: string) => void
  onSubmit: () => void
  placeholder?: string
  value: string
}

export function ChatComposer({
  disabled = false,
  loading = false,
  onChange,
  onSubmit,
  placeholder = 'Ask a question about the document',
  value,
}: ChatComposerProps) {
  const textareaRef = useRef<HTMLTextAreaElement | null>(null)

  useEffect(() => {
    const textarea = textareaRef.current
    if (!textarea) {
      return
    }

    textarea.style.height = '0px'
    textarea.style.height = `${Math.min(textarea.scrollHeight, 200)}px`
  }, [value])

  return (
    <div className="rounded-3xl border border-slate-800 bg-slate-900/80 p-3 shadow-panel">
      <div className="flex items-end gap-3">
        <Textarea
          ref={textareaRef}
          rows={1}
          className="min-h-[52px] resize-none border-0 bg-transparent px-1 py-2 text-sm focus:ring-0"
          value={value}
          disabled={disabled || loading}
          placeholder={placeholder}
          onChange={(event) => onChange(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === 'Enter' && !event.shiftKey) {
              event.preventDefault()
              onSubmit()
            }
          }}
        />
        <Button
          size="icon"
          className="h-11 w-11 shrink-0 rounded-2xl"
          loading={loading}
          disabled={disabled || !value.trim()}
          onClick={onSubmit}
          aria-label="Send message"
        >
          {!loading ? <ArrowUp className="h-4 w-4" /> : null}
        </Button>
      </div>
    </div>
  )
}
