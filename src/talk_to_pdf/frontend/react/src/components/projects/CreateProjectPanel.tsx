import { FileUp, UploadCloud, X } from 'lucide-react'
import { useRef, useState } from 'react'

import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { Panel } from '@/components/ui/Panel'
import { cn } from '@/lib/cn'
import { formatFileSize } from '@/lib/format'

interface CreateProjectPanelProps {
  className?: string
  onCreate: (params: { name: string; file: File }) => Promise<void>
}

export function CreateProjectPanel({ className, onCreate }: CreateProjectPanelProps) {
  const fileInputRef = useRef<HTMLInputElement | null>(null)
  const [name, setName] = useState('')
  const [file, setFile] = useState<File | null>(null)
  const [isDragging, setIsDragging] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const reset = () => {
    setName('')
    setFile(null)
    setError(null)
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }

  const handleFile = (candidate: File | null) => {
    if (!candidate) {
      return
    }

    if (candidate.type !== 'application/pdf' && !candidate.name.toLowerCase().endsWith('.pdf')) {
      setError('Only PDF files are supported.')
      return
    }

    setFile(candidate)
    setError(null)
  }

  return (
    <Panel
      title="New Project"
      description="Upload a PDF to create a new project."
      className={cn(className)}
    >
      <form
        className="space-y-4"
        onSubmit={async (event) => {
          event.preventDefault()

          if (!name.trim()) {
            setError('Project name is required.')
            return
          }

          if (!file) {
            setError('Select a PDF to continue.')
            return
          }

          setSubmitting(true)
          setError(null)

          try {
            await onCreate({
              name: name.trim(),
              file,
            })
            reset()
          } catch (submissionError) {
            setError(submissionError instanceof Error ? submissionError.message : 'Failed to create project.')
          } finally {
            setSubmitting(false)
          }
        }}
      >
        <div className="space-y-2">
          <label className="text-sm font-medium text-slate-200" htmlFor="project-name">
            Project name
          </label>
          <Input
            id="project-name"
            value={name}
            onChange={(event) => setName(event.target.value)}
            placeholder="Quarterly report QA"
            disabled={submitting}
          />
        </div>

        <div className="space-y-2">
          <label className="text-sm font-medium text-slate-200">PDF</label>
          <button
            type="button"
            className={`w-full rounded-3xl border border-dashed px-4 py-8 text-left transition ${
              isDragging
                ? 'border-sky-400 bg-sky-500/10'
                : 'border-slate-800 bg-slate-950/60 hover:border-slate-700'
            }`}
            onDragEnter={(event) => {
              event.preventDefault()
              setIsDragging(true)
            }}
            onDragLeave={(event) => {
              event.preventDefault()
              setIsDragging(false)
            }}
            onDragOver={(event) => {
              event.preventDefault()
              setIsDragging(true)
            }}
            onDrop={(event) => {
              event.preventDefault()
              setIsDragging(false)
              handleFile(event.dataTransfer.files.item(0))
            }}
            onClick={() => fileInputRef.current?.click()}
          >
            <div className="flex flex-col items-center justify-center text-center">
              <div className="rounded-2xl bg-slate-900 p-3 text-sky-300">
                <UploadCloud className="h-6 w-6" />
              </div>
              <p className="mt-4 text-sm font-medium text-slate-100">Drop a PDF or browse</p>
              <p className="mt-1 text-sm text-slate-500">PDF files only.</p>
            </div>
          </button>
          <input
            ref={fileInputRef}
            type="file"
            accept="application/pdf,.pdf"
            className="hidden"
            onChange={(event) => handleFile(event.target.files?.item(0) ?? null)}
          />
        </div>

        {file ? (
          <div className="rounded-2xl border border-slate-800 bg-slate-950/70 px-4 py-3">
            <div className="flex items-start justify-between gap-3">
              <div className="flex items-start gap-3">
                <div className="rounded-xl bg-slate-900 p-2 text-sky-300">
                  <FileUp className="h-4 w-4" />
                </div>
                <div className="min-w-0">
                  <p className="truncate text-sm font-medium text-slate-100">{file.name}</p>
                  <p className="text-xs text-slate-500">{formatFileSize(file.size)}</p>
                </div>
              </div>
              <Button
                variant="ghost"
                size="icon"
                className="h-8 w-8"
                onClick={() => setFile(null)}
                aria-label="Remove selected file"
              >
                <X className="h-4 w-4" />
              </Button>
            </div>
          </div>
        ) : null}

        {error ? <p className="text-sm text-rose-300">{error}</p> : null}

        <Button type="submit" className="w-full" loading={submitting}>
          Create project
        </Button>
      </form>
    </Panel>
  )
}
