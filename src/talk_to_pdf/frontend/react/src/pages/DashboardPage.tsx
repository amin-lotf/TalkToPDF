import { Activity, FolderGit2, MessageSquareMore, ShieldCheck } from 'lucide-react'
import { useEffect, useMemo, useState, type ReactNode } from 'react'
import { useNavigate } from 'react-router-dom'

import { useApiClient, useAuth } from '@/app/auth'
import { useAppShell } from '@/app/shell'
import { Button } from '@/components/ui/Button'
import { EmptyState } from '@/components/ui/EmptyState'
import { Panel } from '@/components/ui/Panel'
import { Spinner } from '@/components/ui/Spinner'
import { formatDateTime } from '@/lib/format'
import type { Chat } from '@/types/chat'
import type { HealthResponse } from '@/types/api'

function StatPanel({
  icon,
  label,
  value,
  detail,
}: {
  detail: string
  icon: ReactNode
  label: string
  value: string
}) {
  return (
    <div className="rounded-3xl border border-slate-800 bg-slate-900/70 px-5 py-5 shadow-panel">
      <div className="flex items-center gap-3">
        <div className="rounded-2xl bg-slate-950 p-3 text-sky-300">{icon}</div>
        <div>
          <p className="text-sm text-slate-400">{label}</p>
          <p className="mt-1 text-2xl font-semibold text-white">{value}</p>
        </div>
      </div>
      <p className="mt-4 text-sm text-slate-500">{detail}</p>
    </div>
  )
}

export function DashboardPage() {
  const api = useApiClient()
  const navigate = useNavigate()
  const { token, user } = useAuth()
  const { projects, projectsLoading } = useAppShell()
  const [health, setHealth] = useState<HealthResponse | null>(null)
  const [healthError, setHealthError] = useState<string | null>(null)
  const [recentChats, setRecentChats] = useState<Chat[]>([])
  const [recentChatsLoading, setRecentChatsLoading] = useState(false)

  useEffect(() => {
    const loadHealth = async () => {
      try {
        setHealth(await api.getHealth())
        setHealthError(null)
      } catch (error) {
        setHealth(null)
        setHealthError(error instanceof Error ? error.message : 'Failed to reach backend health endpoint.')
      }
    }

    void loadHealth()
  }, [api])

  useEffect(() => {
    const project = projects[0]
    if (!project) {
      setRecentChats([])
      return
    }

    const loadChats = async () => {
      setRecentChatsLoading(true)
      try {
        const response = await api.listChats(project.id, 5, 0)
        setRecentChats(response.items)
      } catch {
        setRecentChats([])
      } finally {
        setRecentChatsLoading(false)
      }
    }

    void loadChats()
  }, [api, projects])

  const sessionMode = useMemo(() => {
    if (!user) {
      return 'Signed out'
    }
    return token ? 'JWT session' : 'Backend dev session'
  }, [token, user])

  return (
    <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_360px]">
      <div className="space-y-6">
        <section className="grid gap-4 md:grid-cols-3">
          <StatPanel
            icon={<Activity className="h-5 w-5" />}
            label="Backend"
            value={health?.status === 'ok' ? 'Healthy' : healthError ? 'Unavailable' : 'Checking'}
            detail={healthError ?? 'FastAPI root health check at `/health`.'}
          />
          <StatPanel
            icon={<ShieldCheck className="h-5 w-5" />}
            label="Session"
            value={sessionMode}
            detail={user ? `${user.name} · ${user.email}` : 'No active user context.'}
          />
          <StatPanel
            icon={<FolderGit2 className="h-5 w-5" />}
            label="Projects"
            value={projectsLoading ? '…' : String(projects.length)}
            detail="Projects are ordered by newest creation time from the current backend repository."
          />
        </section>

        <Panel
          title="Recent Projects"
          description="Open an existing workspace or create a new PDF-backed project."
          action={
            <Button variant="secondary" size="sm" onClick={() => navigate('/projects')}>
              Open projects
            </Button>
          }
        >
          {projectsLoading ? (
            <div className="flex items-center gap-3 rounded-2xl border border-slate-800 bg-slate-950/60 px-4 py-3 text-sm text-slate-400">
              <Spinner />
              Loading projects…
            </div>
          ) : projects.length ? (
            <div className="space-y-3">
              {projects.slice(0, 4).map((project) => (
                <button
                  key={project.id}
                  className="flex w-full items-center justify-between rounded-2xl border border-slate-800 bg-slate-950/60 px-4 py-4 text-left transition hover:border-slate-700 hover:bg-slate-950"
                  onClick={() => navigate(`/projects/${project.id}`)}
                >
                  <div className="min-w-0">
                    <p className="truncate text-sm font-medium text-slate-100">{project.name}</p>
                    <p className="truncate text-sm text-slate-500">{project.primary_document.original_filename}</p>
                  </div>
                  <p className="shrink-0 text-xs text-slate-500">{formatDateTime(project.created_at)}</p>
                </button>
              ))}
            </div>
          ) : (
            <EmptyState
              icon={<FolderGit2 className="h-6 w-6" />}
              title="No projects yet"
              description="Create your first project to upload a PDF, index it, and start a persistent chat workspace."
              action={
                <Button onClick={() => navigate('/projects')}>
                  Create project
                </Button>
              }
            />
          )}
        </Panel>
      </div>

      <aside className="space-y-6">
        <Panel title="Current User" description="Resolved from `/auth/me` using the existing backend auth rules.">
          {user ? (
            <dl className="space-y-3 text-sm">
              <div className="rounded-2xl border border-slate-800 bg-slate-950/60 px-4 py-3">
                <dt className="text-xs uppercase tracking-[0.2em] text-slate-500">Name</dt>
                <dd className="mt-1 text-slate-200">{user.name}</dd>
              </div>
              <div className="rounded-2xl border border-slate-800 bg-slate-950/60 px-4 py-3">
                <dt className="text-xs uppercase tracking-[0.2em] text-slate-500">Email</dt>
                <dd className="mt-1 text-slate-200">{user.email}</dd>
              </div>
              <div className="rounded-2xl border border-slate-800 bg-slate-950/60 px-4 py-3">
                <dt className="text-xs uppercase tracking-[0.2em] text-slate-500">Mode</dt>
                <dd className="mt-1 text-slate-200">{sessionMode}</dd>
              </div>
            </dl>
          ) : (
            <p className="text-sm text-slate-500">No authenticated user payload is available.</p>
          )}
        </Panel>

        <Panel
          title="Recent Chats"
          description={
            projects[0]
              ? `Latest chats from ${projects[0].name}, using the existing project-scoped chat endpoint.`
              : 'Recent chats appear after a project exists.'
          }
        >
          {recentChatsLoading ? (
            <div className="flex items-center gap-3 rounded-2xl border border-slate-800 bg-slate-950/60 px-4 py-3 text-sm text-slate-400">
              <Spinner />
              Loading chats…
            </div>
          ) : recentChats.length ? (
            <div className="space-y-3">
              {recentChats.map((chat) => (
                <button
                  key={chat.id}
                  className="w-full rounded-2xl border border-slate-800 bg-slate-950/60 px-4 py-4 text-left transition hover:border-slate-700 hover:bg-slate-950"
                  onClick={() => navigate(`/projects/${chat.project_id}/chats/${chat.id}`)}
                >
                  <div className="flex items-start gap-3">
                    <div className="rounded-2xl bg-slate-900 p-3 text-sky-300">
                      <MessageSquareMore className="h-4 w-4" />
                    </div>
                    <div className="min-w-0">
                      <p className="truncate text-sm font-medium text-slate-100">{chat.title}</p>
                      <p className="mt-1 text-xs text-slate-500">{formatDateTime(chat.updated_at)}</p>
                    </div>
                  </div>
                </button>
              ))}
            </div>
          ) : (
            <p className="text-sm text-slate-500">No chats available from the latest project.</p>
          )}
        </Panel>
      </aside>
    </div>
  )
}
