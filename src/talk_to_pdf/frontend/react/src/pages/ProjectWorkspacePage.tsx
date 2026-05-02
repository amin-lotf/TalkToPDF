import { AlertCircle, FileClock, Search } from 'lucide-react'
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useLocation, useParams } from 'react-router-dom'

import { useApiClient } from '@/app/auth'
import { useAppShell } from '@/app/shell'
import { ChatComposer } from '@/components/chat/ChatComposer'
import { ChatMessageBubble, type DisplayChatMessage } from '@/components/chat/ChatMessageBubble'
import { CitationPanel } from '@/components/chat/CitationPanel'
import { IndexingStatusPanel } from '@/components/chat/IndexingStatusPanel'
import {
  RetrievalSettingsPanel,
  type RetrievalSettings,
} from '@/components/chat/RetrievalSettingsPanel'
import { Button } from '@/components/ui/Button'
import { EmptyState } from '@/components/ui/EmptyState'
import { Panel } from '@/components/ui/Panel'
import { Spinner } from '@/components/ui/Spinner'
import type { ChatMessage } from '@/types/chat'

function getLatestAssistantMessage(messages: ChatMessage[]) {
  return [...messages].reverse().find((message) => message.role === 'assistant') ?? null
}

function isActiveIndexStatus(status?: string | null) {
  const normalized = (status ?? '').toLowerCase()
  return normalized === 'pending' || normalized === 'queued' || normalized === 'running'
}

function canRestartIndexing(status?: string | null) {
  const normalized = (status ?? '').toLowerCase()
  return !normalized || normalized === 'failed' || normalized === 'error' || normalized === 'cancelled' || normalized === 'canceled'
}

export function ProjectWorkspacePage() {
  const api = useApiClient()
  const location = useLocation()
  const { chatId } = useParams()
  const {
    activeProjectId,
    chats,
    chatsLoading,
    currentProject,
    indexReady,
    indexStatusError,
    indexStatusLoading,
    latestIndexStatus,
    projectError,
    projectLoading,
    refreshChats,
    refreshIndexStatus,
  } = useAppShell()

  const [messages, setMessages] = useState<DisplayChatMessage[]>([])
  const [messagesLoading, setMessagesLoading] = useState(false)
  const [messagesError, setMessagesError] = useState<string | null>(null)
  const [composerValue, setComposerValue] = useState('')
  const [sending, setSending] = useState(false)
  const [selectedMessageId, setSelectedMessageId] = useState<string | null>(null)
  const [showMessageDetails, setShowMessageDetails] = useState(false)
  const [workspaceError, setWorkspaceError] = useState<string | null>(
    () => (location.state as { startIndexingError?: string } | null)?.startIndexingError ?? null,
  )
  const [settings, setSettings] = useState<RetrievalSettings>({
    topK: 40,
    topN: 10,
    rerankTimeoutS: 2,
  })
  const transcriptRef = useRef<HTMLDivElement | null>(null)

  const loadMessages = useCallback(async () => {
    if (!chatId) {
      setMessages([])
      setMessagesLoading(false)
      setMessagesError(null)
      return
    }

    setMessagesLoading(true)
    setMessagesError(null)

    try {
      const response = await api.getChatMessages(chatId, 100)
      setMessages(response.items)
      const latestAssistant = getLatestAssistantMessage(response.items)
      setSelectedMessageId(latestAssistant?.id ?? null)
    } catch (error) {
      setMessages([])
      setMessagesError(error instanceof Error ? error.message : 'Failed to load messages.')
    } finally {
      setMessagesLoading(false)
    }
  }, [api, chatId])

  useEffect(() => {
    void loadMessages()
  }, [loadMessages])

  useEffect(() => {
    setShowMessageDetails(false)
  }, [chatId])

  useEffect(() => {
    const frame = window.requestAnimationFrame(() => {
      if (!transcriptRef.current) {
        return
      }
      transcriptRef.current.scrollTop = transcriptRef.current.scrollHeight
    })

    return () => {
      window.cancelAnimationFrame(frame)
    }
  }, [messages])

  useEffect(() => {
    if (!selectedMessageId && messages.length) {
      const latestAssistant = getLatestAssistantMessage(messages)
      if (latestAssistant) {
        setSelectedMessageId(latestAssistant.id)
      }
      return
    }

    if (selectedMessageId && !messages.some((message) => message.id === selectedMessageId)) {
      const latestAssistant = getLatestAssistantMessage(messages)
      setSelectedMessageId(latestAssistant?.id ?? null)
    }
  }, [messages, selectedMessageId])

  const selectedAssistantMessage = useMemo(
    () => messages.find((message) => message.id === selectedMessageId && message.role === 'assistant') ?? null,
    [messages, selectedMessageId],
  )

  const activeChat = useMemo(() => chats.find((chat) => chat.id === chatId) ?? null, [chatId, chats])
  const showDetailsView = showMessageDetails && Boolean(selectedAssistantMessage)

  if (projectLoading && !currentProject) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <div className="flex items-center gap-3 rounded-2xl border border-slate-800 bg-slate-900/80 px-5 py-4 text-sm text-slate-300">
          <Spinner />
          Loading project…
        </div>
      </div>
    )
  }

  if (projectError || !currentProject || !activeProjectId) {
    return (
      <Panel title="Project unavailable" description="The selected project could not be loaded.">
        <div className="rounded-2xl border border-rose-500/20 bg-rose-500/10 px-4 py-4 text-sm text-rose-100">
          {projectError ?? 'Project not found.'}
        </div>
      </Panel>
    )
  }

  const handleStartIndexing = canRestartIndexing(latestIndexStatus?.status)
    ? async () => {
        setWorkspaceError(null)
        try {
          await api.startIndexing(currentProject.id, currentProject.primary_document.id)
          await refreshIndexStatus()
        } catch (error) {
          setWorkspaceError(error instanceof Error ? error.message : 'Failed to start indexing.')
        }
      }
    : null

  const handleCancelIndexing =
    latestIndexStatus && isActiveIndexStatus(latestIndexStatus.status) && !latestIndexStatus.cancel_requested
      ? async () => {
          setWorkspaceError(null)
          try {
            await api.cancelIndexing(latestIndexStatus.index_id)
            await refreshIndexStatus()
          } catch (error) {
            setWorkspaceError(error instanceof Error ? error.message : 'Failed to cancel indexing.')
          }
        }
      : null

  const sidePanels = (
    <>
      <IndexingStatusPanel
        project={currentProject}
        status={latestIndexStatus}
        loading={indexStatusLoading}
        error={indexStatusError}
        onStart={handleStartIndexing}
        onCancel={handleCancelIndexing}
      />

      <RetrievalSettingsPanel value={settings} onChange={setSettings} disabled={sending || !indexReady} />
    </>
  )

  if (showDetailsView && selectedAssistantMessage) {
    return (
      <div className="space-y-6">
        {workspaceError ? (
          <div className="flex items-start gap-3 rounded-3xl border border-amber-500/20 bg-amber-500/10 px-5 py-4 text-sm text-amber-100">
            <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
            <span>{workspaceError}</span>
          </div>
        ) : null}

        <CitationPanel message={selectedAssistantMessage} onBack={() => setShowMessageDetails(false)} />

        <div className="grid gap-6 xl:grid-cols-2">{sidePanels}</div>
      </div>
    )
  }

  return (
    <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_360px]">
      <div className="space-y-6">
        {workspaceError ? (
          <div className="flex items-start gap-3 rounded-3xl border border-amber-500/20 bg-amber-500/10 px-5 py-4 text-sm text-amber-100">
            <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
            <span>{workspaceError}</span>
          </div>
        ) : null}

        {!indexReady ? (
          <EmptyState
            icon={<FileClock className="h-6 w-6" />}
            title="Indexing is required before chat"
            description="This project already has its primary PDF. Start or resume indexing to unlock retrieval and streamed answers."
            action={
              handleStartIndexing ? (
                <Button onClick={() => void handleStartIndexing()}>Start indexing</Button>
              ) : undefined
            }
            className="min-h-[420px]"
          />
        ) : !chatId ? (
          <EmptyState
            icon={<Search className="h-6 w-6" />}
            title="Choose a question"
            description="Choose an existing question or create a new thread."
            className="min-h-[420px]"
          />
        ) : (
          <>
            <Panel
              title={activeChat?.title ?? 'Chat'}
              description={
                chatsLoading
                  ? 'Loading question list…'
                  : 'Open answer details from the source badge on any assistant response.'
              }
            >
              {messagesError ? (
                <div className="mb-4 rounded-2xl border border-rose-500/20 bg-rose-500/10 px-4 py-3 text-sm text-rose-100">
                  {messagesError}
                </div>
              ) : null}

              <div
                ref={transcriptRef}
                className="app-scrollbar min-h-[420px] max-h-[calc(100vh-22rem)] space-y-4 overflow-y-auto pr-1"
              >
                {messagesLoading ? (
                  <div className="flex items-center gap-3 rounded-2xl border border-slate-800 bg-slate-950/60 px-4 py-3 text-sm text-slate-400">
                    <Spinner />
                    Loading messages…
                  </div>
                ) : messages.length ? (
                  messages.map((message) => (
                    <ChatMessageBubble
                      key={message.id}
                      message={message}
                      selected={showMessageDetails && message.id === selectedMessageId}
                      onOpenDetails={(messageId) => {
                        setSelectedMessageId(messageId)
                        setShowMessageDetails(true)
                      }}
                    />
                  ))
                ) : (
                  <EmptyState
                    icon={<Search className="h-6 w-6" />}
                    title="Ask the first question"
                    description="The backend will stream the answer and save its sources for later inspection."
                    className="min-h-[360px]"
                  />
                )}
              </div>
            </Panel>

            <ChatComposer
              value={composerValue}
              onChange={setComposerValue}
              loading={sending}
              disabled={!indexReady}
              onSubmit={async () => {
                if (!activeProjectId || !chatId || !composerValue.trim() || sending) {
                  return
                }

                const prompt = composerValue.trim()
                const optimisticUserId = `user-${crypto.randomUUID()}`
                const optimisticAssistantId = `assistant-${crypto.randomUUID()}`

                setComposerValue('')
                setWorkspaceError(null)
                setShowMessageDetails(false)
                setMessages((currentMessages) => [
                  ...currentMessages,
                  {
                    id: optimisticUserId,
                    chat_id: chatId,
                    role: 'user',
                    content: prompt,
                    created_at: new Date().toISOString(),
                    optimistic: true,
                  },
                  {
                    id: optimisticAssistantId,
                    chat_id: chatId,
                    role: 'assistant',
                    content: '',
                    created_at: new Date().toISOString(),
                    optimistic: true,
                    streaming: true,
                  },
                ])
                setSelectedMessageId(optimisticAssistantId)
                setSending(true)

                try {
                  await api.streamProjectReply(
                    {
                      project_id: activeProjectId,
                      chat_id: chatId,
                      query: prompt,
                      top_k: settings.topK,
                      top_n: settings.topN,
                      rerank_timeout_s: settings.rerankTimeoutS,
                    },
                    {
                      onChunk: ({ accumulated }) => {
                        setMessages((currentMessages) =>
                          currentMessages.map((message) =>
                            message.id === optimisticAssistantId
                              ? {
                                  ...message,
                                  content: accumulated,
                                  streaming: true,
                                }
                              : message,
                          ),
                        )
                      },
                    },
                  )

                  setMessages((currentMessages) =>
                    currentMessages.map((message) =>
                      message.id === optimisticAssistantId
                        ? {
                            ...message,
                            streaming: false,
                          }
                        : message,
                    ),
                  )
                  await loadMessages()
                  await refreshChats()
                } catch (error) {
                  setWorkspaceError(error instanceof Error ? error.message : 'The streamed reply failed.')
                  await loadMessages()
                } finally {
                  setSending(false)
                }
              }}
            />
          </>
        )}
      </div>

      <aside className="space-y-6">{sidePanels}</aside>
    </div>
  )
}
