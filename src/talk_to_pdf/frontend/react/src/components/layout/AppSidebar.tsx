import {
  FileText,
  Folders,
  LayoutDashboard,
  MessageSquareMore,
  MessageSquarePlus,
  Trash2,
  X,
} from 'lucide-react'
import { useState } from 'react'
import { useLocation } from 'react-router-dom'

import { CreateProjectPanel } from '@/components/projects/CreateProjectPanel'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { Spinner } from '@/components/ui/Spinner'
import { cn } from '@/lib/cn'
import { formatDateTime } from '@/lib/format'
import type { Chat } from '@/types/chat'
import type { Project } from '@/types/project'

interface AppSidebarProps {
  activeChatId: string | null
  activeProjectId: string | null
  chats: Chat[]
  chatsError: string | null
  chatsLoading: boolean
  indexReady: boolean
  onClose: () => void
  onCreateChat: (title: string) => Promise<void>
  onCreateProject: (params: { name: string; file: File }) => Promise<void>
  onDeleteChat: (chatId: string) => Promise<void>
  onNavigate: (href: string) => void
  onOpenProject: (projectId: string) => void
  open: boolean
  projects: Project[]
  projectsLoading: boolean
}

export function AppSidebar({
  activeChatId,
  activeProjectId,
  chats,
  chatsError,
  chatsLoading,
  indexReady,
  onClose,
  onCreateChat,
  onCreateProject,
  onDeleteChat,
  onNavigate,
  onOpenProject,
  open,
  projects,
  projectsLoading,
}: AppSidebarProps) {
  const location = useLocation()
  const [newChatTitle, setNewChatTitle] = useState('')
  const [creatingChat, setCreatingChat] = useState(false)
  const [chatActionError, setChatActionError] = useState<string | null>(null)

  const onProjectsPage = location.pathname === '/projects'
  const inProjectWorkspace = Boolean(activeProjectId) && location.pathname.startsWith('/projects/')
  const showProjectLibrary = !onProjectsPage && !inProjectWorkspace
  const showCreateProjectPanel = onProjectsPage
  const showQuestionLibrary = inProjectWorkspace

  const submitChat = async () => {
    if (!newChatTitle.trim()) {
      setChatActionError('Chat title is required.')
      return
    }

    setCreatingChat(true)
    setChatActionError(null)

    try {
      await onCreateChat(newChatTitle.trim())
      setNewChatTitle('')
      onClose()
    } catch (error) {
      setChatActionError(error instanceof Error ? error.message : 'Failed to create chat.')
    } finally {
      setCreatingChat(false)
    }
  }

  const navButtonClassName = (active: boolean) =>
    cn(
      'flex w-full items-center gap-3 rounded-2xl border px-4 py-3 text-left text-sm transition',
      active
        ? 'border-sky-500/40 bg-sky-500/10 text-slate-100'
        : 'border-slate-800 bg-slate-900/60 text-slate-200 hover:border-slate-700 hover:bg-slate-900',
    )

  return (
    <>
      <div
        className={cn(
          'fixed inset-0 z-30 bg-slate-950/70 backdrop-blur-sm transition-opacity lg:hidden',
          open ? 'opacity-100' : 'pointer-events-none opacity-0',
        )}
        onClick={onClose}
      />

      <aside
        className={cn(
          'fixed inset-y-0 left-0 z-40 flex w-80 max-w-[85vw] flex-col border-r border-slate-800/80 bg-slate-950/95 backdrop-blur transition-transform lg:static lg:w-80 lg:max-w-none lg:translate-x-0',
          open ? 'translate-x-0' : '-translate-x-full',
        )}
      >
        <div className="flex items-center justify-between border-b border-slate-800/80 px-5 py-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.24em] text-sky-300">TalkToPDF</p>
            <p className="mt-1 text-sm text-slate-400">Document intelligence workspace</p>
          </div>
          <Button variant="ghost" size="icon" className="lg:hidden" onClick={onClose} aria-label="Close navigation">
            <X className="h-5 w-5" />
          </Button>
        </div>

        <div className="app-scrollbar flex-1 overflow-y-auto px-4 py-4">
          <div className="space-y-2">
            <button
              className={navButtonClassName(location.pathname.startsWith('/dashboard'))}
              onClick={() => onNavigate('/dashboard')}
            >
              <LayoutDashboard className="h-4 w-4 text-sky-300" />
              Dashboard
            </button>
            <button
              className={navButtonClassName(location.pathname.startsWith('/projects'))}
              onClick={() => onNavigate('/projects')}
            >
              <Folders className="h-4 w-4 text-emerald-300" />
              Projects
            </button>
          </div>

          {showProjectLibrary ? (
            <div className="mt-6 space-y-3">
              <p className="text-xs font-semibold uppercase tracking-[0.22em] text-slate-500">Projects</p>

              <div className="space-y-2">
                {projectsLoading ? (
                  <div className="flex items-center gap-3 rounded-2xl border border-slate-800 bg-slate-900/50 px-4 py-3 text-sm text-slate-400">
                    <Spinner />
                    Loading projects…
                  </div>
                ) : null}

                {!projectsLoading && !projects.length ? (
                  <div className="rounded-2xl border border-dashed border-slate-800 px-4 py-3 text-sm text-slate-500">
                    No projects yet.
                  </div>
                ) : null}

                {projects.map((project) => {
                  const isActive = activeProjectId === project.id

                  return (
                    <button
                      key={project.id}
                      className={cn(
                        'w-full rounded-2xl border px-4 py-3 text-left transition',
                        isActive
                          ? 'border-sky-500/40 bg-sky-500/10'
                          : 'border-slate-800 bg-slate-900/50 hover:border-slate-700 hover:bg-slate-900',
                      )}
                      onClick={() => onOpenProject(project.id)}
                    >
                      <div className="flex items-start gap-3">
                        <div className="rounded-xl bg-slate-950/80 p-2 text-sky-300">
                          <FileText className="h-4 w-4" />
                        </div>
                        <div className="min-w-0 flex-1">
                          <p className="truncate text-sm font-medium text-slate-100">{project.name}</p>
                          <p className="truncate text-xs text-slate-400">
                            {project.primary_document.original_filename}
                          </p>
                          <p className="mt-2 text-xs text-slate-500">{formatDateTime(project.created_at)}</p>
                        </div>
                      </div>
                    </button>
                  )
                })}
              </div>
            </div>
          ) : null}

          {showCreateProjectPanel ? (
            <div className="mt-6">
              <CreateProjectPanel
                onCreate={async (params) => {
                  await onCreateProject(params)
                  onClose()
                }}
              />
            </div>
          ) : null}

          {showQuestionLibrary ? (
            <div className="mt-6 space-y-4">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.22em] text-slate-500">Questions</p>
                <p className="mt-2 text-sm text-slate-400">Create a thread or reopen an existing one.</p>
              </div>

              <div className="space-y-3 rounded-2xl border border-slate-800 bg-slate-900/50 p-3">
                <Input
                  value={newChatTitle}
                  onChange={(event) => {
                    setNewChatTitle(event.target.value)
                    if (chatActionError) {
                      setChatActionError(null)
                    }
                  }}
                  placeholder={indexReady ? 'New question thread' : 'Finish indexing before creating chats'}
                  disabled={!indexReady || creatingChat}
                  onKeyDown={(event) => {
                    if (event.key === 'Enter') {
                      event.preventDefault()
                      void submitChat()
                    }
                  }}
                />
                <Button
                  className="w-full"
                  size="sm"
                  disabled={!indexReady}
                  loading={creatingChat}
                  onClick={() => void submitChat()}
                >
                  {!creatingChat ? <MessageSquarePlus className="h-4 w-4" /> : null}
                  New question
                </Button>
                {chatActionError ? <p className="text-xs text-rose-300">{chatActionError}</p> : null}
                {!indexReady ? (
                  <p className="text-xs text-slate-500">Questions unlock when the latest index is ready.</p>
                ) : null}
              </div>

              <div className="space-y-2">
                {chatsLoading ? (
                  <div className="flex items-center gap-3 rounded-2xl border border-slate-800 bg-slate-900/50 px-4 py-3 text-sm text-slate-400">
                    <Spinner />
                    Loading questions…
                  </div>
                ) : null}

                {chatsError ? (
                  <div className="rounded-2xl border border-rose-500/20 bg-rose-500/10 px-4 py-3 text-sm text-rose-100">
                    {chatsError}
                  </div>
                ) : null}

                {!chatsLoading && !chats.length ? (
                  <div className="rounded-2xl border border-dashed border-slate-800 px-4 py-3 text-sm text-slate-500">
                    No questions yet.
                  </div>
                ) : null}

                {chats.map((chat) => {
                  const isActive = activeChatId === chat.id

                  return (
                    <div
                      key={chat.id}
                      className={cn(
                        'rounded-2xl border px-3 py-3',
                        isActive
                          ? 'border-sky-500/40 bg-sky-500/10'
                          : 'border-slate-800 bg-slate-900/50',
                      )}
                    >
                      <div className="flex items-start gap-2">
                        <button
                          className="flex min-w-0 flex-1 items-start gap-3 text-left"
                          onClick={() => onNavigate(`/projects/${chat.project_id}/chats/${chat.id}`)}
                        >
                          <div className="rounded-xl bg-slate-950/80 p-2 text-slate-300">
                            <MessageSquareMore className="h-4 w-4" />
                          </div>
                          <div className="min-w-0 flex-1">
                            <p className="truncate text-sm font-medium text-slate-100">{chat.title}</p>
                            <p className="mt-1 text-xs text-slate-500">{formatDateTime(chat.updated_at)}</p>
                          </div>
                        </button>
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-8 w-8"
                          aria-label={`Delete ${chat.title}`}
                          onClick={() => {
                            if (window.confirm(`Delete chat "${chat.title}"?`)) {
                              void onDeleteChat(chat.id).catch((error: unknown) => {
                                setChatActionError(
                                  error instanceof Error ? error.message : 'Failed to delete chat.',
                                )
                              })
                            }
                          }}
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>
          ) : null}
        </div>
      </aside>
    </>
  )
}
