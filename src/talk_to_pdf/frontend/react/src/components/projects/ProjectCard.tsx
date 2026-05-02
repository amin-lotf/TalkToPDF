import { ArrowUpRight, Pencil, Save, Trash2, X } from 'lucide-react'
import { useEffect, useState } from 'react'

import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { Panel } from '@/components/ui/Panel'
import { formatDateTime, formatFileSize } from '@/lib/format'
import type { Project } from '@/types/project'

interface ProjectCardProps {
  project: Project
  onDelete: (projectId: string, projectName: string) => Promise<void>
  onOpen: (projectId: string) => void
  onRename: (projectId: string, newName: string) => Promise<void>
}

export function ProjectCard({ project, onDelete, onOpen, onRename }: ProjectCardProps) {
  const [editing, setEditing] = useState(false)
  const [name, setName] = useState(project.name)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    setName(project.name)
  }, [project.name])

  return (
    <Panel
      title={
        editing ? (
          <Input value={name} onChange={(event) => setName(event.target.value)} disabled={busy} />
        ) : (
          project.name
        )
      }
      description={`${project.primary_document.original_filename} · ${formatFileSize(
        project.primary_document.size_bytes,
      )}`}
      action={
        <div className="flex items-center gap-2">
          <Button variant="ghost" size="icon" onClick={() => onOpen(project.id)} aria-label={`Open ${project.name}`}>
            <ArrowUpRight className="h-4 w-4" />
          </Button>
          {editing ? (
            <>
              <Button
                variant="ghost"
                size="icon"
                onClick={async () => {
                  if (!name.trim()) {
                    setError('Name is required.')
                    return
                  }

                  setBusy(true)
                  setError(null)
                  try {
                    await onRename(project.id, name.trim())
                    setEditing(false)
                  } catch (renameError) {
                    setError(renameError instanceof Error ? renameError.message : 'Failed to rename project.')
                  } finally {
                    setBusy(false)
                  }
                }}
                aria-label={`Save ${project.name}`}
              >
                <Save className="h-4 w-4" />
              </Button>
              <Button
                variant="ghost"
                size="icon"
                onClick={() => {
                  setEditing(false)
                  setName(project.name)
                  setError(null)
                }}
                aria-label="Cancel rename"
              >
                <X className="h-4 w-4" />
              </Button>
            </>
          ) : (
            <>
              <Button variant="ghost" size="icon" onClick={() => setEditing(true)} aria-label={`Rename ${project.name}`}>
                <Pencil className="h-4 w-4" />
              </Button>
              <Button
                variant="ghost"
                size="icon"
                onClick={async () => {
                  if (window.confirm(`Delete project "${project.name}"?`)) {
                    setBusy(true)
                    setError(null)
                    try {
                      await onDelete(project.id, project.name)
                    } catch (deleteError) {
                      setError(deleteError instanceof Error ? deleteError.message : 'Failed to delete project.')
                    } finally {
                      setBusy(false)
                    }
                  }
                }}
                aria-label={`Delete ${project.name}`}
              >
                <Trash2 className="h-4 w-4" />
              </Button>
            </>
          )}
        </div>
      }
    >
      <div className="grid gap-3 text-sm text-slate-400 sm:grid-cols-2">
        <div>
          <p className="text-xs uppercase tracking-[0.2em] text-slate-500">Uploaded</p>
          <p className="mt-1 text-slate-200">{formatDateTime(project.primary_document.uploaded_at)}</p>
        </div>
        <div>
          <p className="text-xs uppercase tracking-[0.2em] text-slate-500">Created</p>
          <p className="mt-1 text-slate-200">{formatDateTime(project.created_at)}</p>
        </div>
      </div>
      {error ? <p className="mt-4 text-sm text-rose-300">{error}</p> : null}
    </Panel>
  )
}
