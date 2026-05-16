import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import remarkMath from 'remark-math'
import rehypeKatex from 'rehype-katex'

import { cn } from '@/lib/cn'

interface MarkdownMessageProps {
  content: string
  className?: string
  streaming?: boolean
}

export function MarkdownMessage({ content, className, streaming = false }: MarkdownMessageProps) {
  return (
    <div className={cn('markdown-body text-sm leading-7 text-slate-100', className)}>
      <ReactMarkdown remarkPlugins={[remarkGfm, remarkMath]} rehypePlugins={[rehypeKatex]}>
        {content}
      </ReactMarkdown>
      {streaming ? (
        <span aria-hidden="true" className="markdown-cursor">
          ▌
        </span>
      ) : null}
    </div>
  )
}
