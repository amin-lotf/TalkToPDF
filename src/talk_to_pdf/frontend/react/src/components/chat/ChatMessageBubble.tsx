import { Bot, Sparkles, User2 } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

import { cn } from '@/lib/cn'
import { formatDateTime } from '@/lib/format'
import type { ChatMessage } from '@/types/chat'

export interface DisplayChatMessage extends ChatMessage {
  optimistic?: boolean
  streaming?: boolean
}

interface ChatMessageBubbleProps {
  message: DisplayChatMessage
  onOpenDetails?: (messageId: string) => void
  selected?: boolean
}

export function ChatMessageBubble({
  message,
  onOpenDetails,
  selected = false,
}: ChatMessageBubbleProps) {
  const isAssistant = message.role === 'assistant'
  const sourceCount = message.citations?.chunks?.length ?? 0
  const hasDetails = isAssistant && Boolean(message.metrics || message.citations)

  return (
    <div className={cn('flex', isAssistant ? 'justify-start' : 'justify-end')}>
      <article
        className={cn(
          'max-w-3xl rounded-3xl border px-5 py-4 text-left transition',
          isAssistant
            ? selected
              ? 'border-sky-500/40 bg-sky-500/10 shadow-panel'
              : 'border-slate-800 bg-slate-900/80 hover:border-slate-700 hover:bg-slate-900'
            : 'border-slate-800/70 bg-slate-950/90',
        )}
      >
        <div className="mb-3 flex items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <div className="rounded-xl bg-slate-950/70 p-2 text-slate-200">
              {isAssistant ? <Bot className="h-4 w-4" /> : <User2 className="h-4 w-4" />}
            </div>
            <div>
              <p className="text-sm font-medium text-slate-100">{isAssistant ? 'Assistant' : 'You'}</p>
              <p className="text-xs text-slate-500">{formatDateTime(message.created_at)}</p>
            </div>
          </div>

          {hasDetails ? (
            <button
              type="button"
              className={cn(
                'inline-flex items-center gap-1 rounded-full border px-2.5 py-1 text-xs font-medium transition',
                selected
                  ? 'border-sky-400/40 bg-sky-500/10 text-sky-100'
                  : 'border-emerald-500/30 bg-emerald-500/10 text-emerald-200 hover:border-emerald-400/40 hover:bg-emerald-500/15',
              )}
              onClick={() => onOpenDetails?.(message.id)}
            >
              <Sparkles className="h-3.5 w-3.5" />
              {sourceCount > 0 ? `${sourceCount} ${sourceCount === 1 ? 'source' : 'sources'}` : 'Details'}
            </button>
          ) : null}
        </div>

        {isAssistant ? (
          <div className="markdown-body prose prose-invert max-w-none prose-p:leading-7 prose-pre:bg-slate-950">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {`${message.content}${message.streaming ? '▌' : ''}`}
            </ReactMarkdown>
          </div>
        ) : (
          <p className="whitespace-pre-wrap text-sm leading-7 text-slate-100">{message.content}</p>
        )}
      </article>
    </div>
  )
}
