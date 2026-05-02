import { Menu, RefreshCw } from 'lucide-react'
import {
  Outlet,
  useLocation,
  useNavigate,
  useOutletContext,
  useParams,
} from 'react-router-dom'
import { useCallback, useEffect, useMemo, useState } from 'react'

import { isApiError } from '@/api/client'
import { useApiClient, useAuth } from '@/app/auth'
import { AppSidebar } from '@/components/layout/AppSidebar'
import { Button } from '@/components/ui/Button'
import { Spinner } from '@/components/ui/Spinner'
import { formatDateTime } from '@/lib/format'
import type { Chat } from '@/types/chat'
import type { IndexingStatus } from '@/types/indexing'
import type { Project } from '@/types/project'

export interface AppShellContextValue {
  activeChatId: string | null
  activeProjectId: string | null
  chats: Chat[]
  chatsError: string | null
  chatsLoading: boolean
  createChat: (title: string) => Promise<void>
  currentProject: Project | null
  indexReady: boolean
  indexStatusError: string | null
  indexStatusLoading: boolean
  latestIndexStatus: IndexingStatus | null
  projectError: string | null
  projectLoading: boolean
  projects: Project[]
  projectsError: string | null
  projectsLoading: boolean
  refreshChats: () => Promise<void>
  refreshIndexStatus: (options?: { silent?: boolean }) => Promise<void>
  refreshProject: () => Promise<void>
  refreshProjects: () => Promise<void>
}

function extractMessage(error: unknown, fallback: string) {
  return error instanceof Error ? error.message : fallback
}

function shouldIgnoreMissingIndex(error: unknown) {
  return isApiError(error) && error.status === 404
}

function isIndexReady(status: string | undefined | null) {
  const normalized = (status ?? '').toLowerCase()
  return normalized === 'ready' || normalized === 'completed'
}

function isIndexTerminal(status: string | undefined | null) {
  const normalized = (status ?? '').toLowerCase()
  return ['ready', 'completed', 'failed', 'error', 'cancelled', 'canceled'].includes(normalized)
}

export function useAppShell() {
  return useOutletContext<AppShellContextValue>()
}

export function AppLayout() {
  const api = useApiClient()
  const { logout, user } = useAuth()
  const location = useLocation()
  const navigate = useNavigate()
  const params = useParams()
  const activeProjectId = params.projectId ?? null
  const activeChatId = params.chatId ?? null

  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [projects, setProjects] = useState<Project[]>([])
  const [projectsLoading, setProjectsLoading] = useState(true)
  const [projectsError, setProjectsError] = useState<string | null>(null)
  const [currentProject, setCurrentProject] = useState<Project | null>(null)
  const [projectLoading, setProjectLoading] = useState(false)
  const [projectError, setProjectError] = useState<string | null>(null)
  const [chats, setChats] = useState<Chat[]>([])
  const [chatsLoading, setChatsLoading] = useState(false)
  const [chatsError, setChatsError] = useState<string | null>(null)
  const [latestIndexStatus, setLatestIndexStatus] = useState<IndexingStatus | null>(null)
  const [indexStatusLoading, setIndexStatusLoading] = useState(false)
  const [indexStatusError, setIndexStatusError] = useState<string | null>(null)

  const refreshProjects = useCallback(async () => {
    setProjectsLoading(true)
    setProjectsError(null)

    try {
      const response = await api.listProjects()
      setProjects(response.items)
    } catch (error) {
      setProjectsError(extractMessage(error, 'Failed to load projects.'))
      setProjects([])
    } finally {
      setProjectsLoading(false)
    }
  }, [api])

  const refreshProject = useCallback(async () => {
    if (!activeProjectId) {
      setCurrentProject(null)
      setProjectError(null)
      setProjectLoading(false)
      return
    }

    setProjectLoading(true)
    setProjectError(null)

    try {
      const project = await api.getProject(activeProjectId)
      setCurrentProject(project)
    } catch (error) {
      setCurrentProject(null)
      setProjectError(extractMessage(error, 'Failed to load project.'))
    } finally {
      setProjectLoading(false)
    }
  }, [activeProjectId, api])

  const refreshChats = useCallback(async () => {
    if (!activeProjectId) {
      setChats([])
      setChatsError(null)
      setChatsLoading(false)
      return
    }

    setChatsLoading(true)
    setChatsError(null)

    try {
      const response = await api.listChats(activeProjectId)
      setChats(response.items)
    } catch (error) {
      setChats([])
      setChatsError(extractMessage(error, 'Failed to load chats.'))
    } finally {
      setChatsLoading(false)
    }
  }, [activeProjectId, api])

  const refreshIndexStatus = useCallback(
    async (options?: { silent?: boolean }) => {
      if (!activeProjectId) {
        setLatestIndexStatus(null)
        setIndexStatusError(null)
        setIndexStatusLoading(false)
        return
      }

      if (!options?.silent) {
        setIndexStatusLoading(true)
      }
      setIndexStatusError(null)

      try {
        const status = await api.getLatestIndexStatus(activeProjectId)
        setLatestIndexStatus(status)
      } catch (error) {
        if (shouldIgnoreMissingIndex(error)) {
          setLatestIndexStatus(null)
          setIndexStatusError(null)
        } else {
          setLatestIndexStatus(null)
          setIndexStatusError(extractMessage(error, 'Failed to load indexing status.'))
        }
      } finally {
        if (!options?.silent) {
          setIndexStatusLoading(false)
        }
      }
    },
    [activeProjectId, api],
  )

  useEffect(() => {
    void refreshProjects()
  }, [refreshProjects])

  useEffect(() => {
    void refreshProject()
    void refreshChats()
    void refreshIndexStatus()
  }, [refreshChats, refreshIndexStatus, refreshProject])

  useEffect(() => {
    if (!activeProjectId || !latestIndexStatus || isIndexTerminal(latestIndexStatus.status)) {
      return
    }

    const timer = window.setInterval(() => {
      void refreshIndexStatus({ silent: true })
    }, 5000)

    return () => {
      window.clearInterval(timer)
    }
  }, [activeProjectId, latestIndexStatus, refreshIndexStatus])

  const handleCreateChat = useCallback(
    async (title: string) => {
      if (!activeProjectId) {
        return
      }

      const created = await api.createChat({
        project_id: activeProjectId,
        title,
      })
      await refreshChats()
      navigate(`/projects/${activeProjectId}/chats/${created.id}`)
    },
    [activeProjectId, api, navigate, refreshChats],
  )

  const handleDeleteChat = useCallback(
    async (chatId: string) => {
      if (!activeProjectId) {
        return
      }

      await api.deleteChat(chatId)
      await refreshChats()

      if (activeChatId === chatId) {
        navigate(`/projects/${activeProjectId}`)
      }
    },
    [activeChatId, activeProjectId, api, navigate, refreshChats],
  )

  const handleOpenProject = useCallback(
    (projectId: string) => {
      navigate(`/projects/${projectId}`)
      setSidebarOpen(false)
    },
    [navigate],
  )

  const handleNavigate = useCallback(
    (href: string) => {
      navigate(href)
      setSidebarOpen(false)
    },
    [navigate],
  )

  const handleLogout = useCallback(() => {
    logout()
    navigate('/login')
  }, [logout, navigate])

  const shellTitle = useMemo(() => {
    if (location.pathname.startsWith('/projects/') && currentProject) {
      return currentProject.name
    }
    if (location.pathname.startsWith('/projects')) {
      return 'Projects'
    }
    return 'Dashboard'
  }, [currentProject, location.pathname])

  const shellSubtitle = useMemo(() => {
    if (currentProject) {
      return `${currentProject.primary_document.original_filename} · ${formatDateTime(
        currentProject.created_at,
      )}`
    }
    return 'Self-hosted PDF retrieval workspace'
  }, [currentProject])

  const value = useMemo<AppShellContextValue>(
    () => ({
      activeChatId,
      activeProjectId,
      chats,
      chatsError,
      chatsLoading,
      createChat: handleCreateChat,
      currentProject,
      indexReady: isIndexReady(latestIndexStatus?.status),
      indexStatusError,
      indexStatusLoading,
      latestIndexStatus,
      projectError,
      projectLoading,
      projects,
      projectsError,
      projectsLoading,
      refreshChats,
      refreshIndexStatus,
      refreshProject,
      refreshProjects,
    }),
    [
      activeChatId,
      activeProjectId,
      chats,
      chatsError,
      chatsLoading,
      handleCreateChat,
      currentProject,
      indexStatusError,
      indexStatusLoading,
      latestIndexStatus,
      projectError,
      projectLoading,
      projects,
      projectsError,
      projectsLoading,
      refreshChats,
      refreshIndexStatus,
      refreshProject,
      refreshProjects,
    ],
  )

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      <div className="flex min-h-screen">
        <AppSidebar
          activeChatId={activeChatId}
          activeProjectId={activeProjectId}
          chats={chats}
          chatsError={chatsError}
          chatsLoading={chatsLoading}
          currentProject={currentProject}
          indexReady={isIndexReady(latestIndexStatus?.status)}
          latestIndexStatus={latestIndexStatus}
          onClose={() => setSidebarOpen(false)}
          onCreateChat={handleCreateChat}
          onDeleteChat={handleDeleteChat}
          onLogout={handleLogout}
          onNavigate={handleNavigate}
          onOpenProject={handleOpenProject}
          open={sidebarOpen}
          projects={projects}
          projectsLoading={projectsLoading}
          userName={user?.name ?? user?.email ?? 'User'}
        />

        <div className="flex min-h-screen min-w-0 flex-1 flex-col">
          <header className="sticky top-0 z-20 border-b border-slate-800/80 bg-slate-950/90 backdrop-blur">
            <div className="flex items-center justify-between gap-4 px-4 py-4 sm:px-6 lg:px-8">
              <div className="flex min-w-0 items-center gap-3">
                <Button
                  variant="ghost"
                  size="icon"
                  className="lg:hidden"
                  onClick={() => setSidebarOpen(true)}
                  aria-label="Open navigation"
                >
                  <Menu className="h-5 w-5" />
                </Button>
                <div className="min-w-0">
                  <p className="truncate text-lg font-semibold text-white">{shellTitle}</p>
                  <p className="truncate text-sm text-slate-400">{shellSubtitle}</p>
                </div>
              </div>

              <div className="flex items-center gap-2">
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={() => {
                    void refreshProjects()
                    if (activeProjectId) {
                      void refreshProject()
                      void refreshChats()
                      void refreshIndexStatus()
                    }
                  }}
                >
                  {projectsLoading || projectLoading || chatsLoading || indexStatusLoading ? (
                    <Spinner />
                  ) : (
                    <RefreshCw className="h-4 w-4" />
                  )}
                  Refresh
                </Button>
                <div className="hidden rounded-2xl border border-slate-800 bg-slate-900/80 px-3 py-2 text-right sm:block">
                  <p className="text-sm font-medium text-slate-100">{user?.name ?? 'Signed in'}</p>
                  <p className="text-xs text-slate-400">{user?.email}</p>
                </div>
              </div>
            </div>
          </header>

          <main className="flex-1 px-4 py-4 sm:px-6 lg:px-8">
            <Outlet context={value} />
          </main>
        </div>
      </div>
    </div>
  )
}
