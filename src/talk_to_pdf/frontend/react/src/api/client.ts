import { resolveApiUrl, resolveHealthUrl } from '@/lib/env'
import type { ApiErrorPayload, HealthResponse } from '@/types/api'
import type { AuthUser, LoginRequest, RegisterRequest, TokenResponse } from '@/types/auth'
import type {
  Chat,
  ChatMessage,
  CreateChatRequest,
  ListChatsResponse,
  ListMessagesResponse,
  QueryRequest,
  StreamingReplyEvent,
} from '@/types/chat'
import type { IndexingStatus } from '@/types/indexing'
import type { ListProjectsResponse, Project } from '@/types/project'

export class ApiError extends Error {
  readonly status: number
  readonly body?: unknown

  constructor(message: string, status: number, body?: unknown) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.body = body
  }
}

export function isApiError(error: unknown): error is ApiError {
  return error instanceof ApiError
}

function normalizeErrorMessage(body: unknown, fallback: string) {
  if (!body) {
    return fallback
  }

  if (typeof body === 'string') {
    return body
  }

  const payload = body as ApiErrorPayload
  if (typeof payload.detail === 'string') {
    return payload.detail
  }

  if (Array.isArray(payload.detail)) {
    return payload.detail.join(', ')
  }

  if (payload.detail && typeof payload.detail === 'object') {
    return Object.values(payload.detail)
      .flatMap((value) => (Array.isArray(value) ? value : [value]))
      .map((value) => String(value))
      .join(', ')
  }

  return fallback
}

type RequestOptions = {
  method?: string
  body?: BodyInit | null
  headers?: HeadersInit
  signal?: AbortSignal
  skipAuth?: boolean
  tokenOverride?: string | null
  responseType?: 'json' | 'text' | 'void'
  rawUrl?: string
}

type ClientOptions = {
  getToken: () => string | null
  onUnauthorized?: (error: ApiError) => void
}

export class TalkToPdfApi {
  constructor(private readonly options: ClientOptions) {}

  private async request<T>(path: string, options: RequestOptions = {}): Promise<T> {
    const token = options.skipAuth ? null : options.tokenOverride ?? this.options.getToken()
    const headers = new Headers(options.headers)

    if (token) {
      headers.set('Authorization', `Bearer ${token}`)
    }

    const response = await fetch(options.rawUrl ?? resolveApiUrl(path), {
      method: options.method ?? 'GET',
      body: options.body,
      headers,
      signal: options.signal,
    })

    if (options.responseType === 'void' || response.status === 204) {
      if (!response.ok) {
        const body = await this.parseBody(response)
        const error = new ApiError(
          normalizeErrorMessage(body, `Request failed with status ${response.status}`),
          response.status,
          body,
        )
        if (response.status === 401 && token) {
          this.options.onUnauthorized?.(error)
        }
        throw error
      }

      return undefined as T
    }

    const body = await this.parseBody(response)

    if (!response.ok) {
      const error = new ApiError(
        normalizeErrorMessage(body, `Request failed with status ${response.status}`),
        response.status,
        body,
      )
      if (response.status === 401 && token) {
        this.options.onUnauthorized?.(error)
      }
      throw error
    }

    return body as T
  }

  private async parseBody(response: Response) {
    const contentType = response.headers.get('content-type') ?? ''
    if (contentType.includes('application/json')) {
      return response.json()
    }

    return response.text()
  }

  async register(payload: RegisterRequest) {
    return this.request<AuthUser>('/auth/register', {
      method: 'POST',
      body: JSON.stringify(payload),
      headers: {
        'Content-Type': 'application/json',
      },
      skipAuth: true,
    })
  }

  async login(payload: LoginRequest) {
    return this.request<TokenResponse>('/auth/token', {
      method: 'POST',
      body: JSON.stringify(payload),
      headers: {
        'Content-Type': 'application/json',
      },
      skipAuth: true,
    })
  }

  async getMe(tokenOverride?: string | null) {
    return this.request<AuthUser>('/auth/me', {
      tokenOverride,
      skipAuth: false,
    })
  }

  async getHealth() {
    return this.request<HealthResponse>('/health', {
      rawUrl: resolveHealthUrl(),
      skipAuth: true,
    })
  }

  async listProjects() {
    return this.request<ListProjectsResponse>('/projects')
  }

  async getProject(projectId: string) {
    return this.request<Project>(`/projects/${projectId}`)
  }

  async createProject(params: { name: string; file: File }) {
    const formData = new FormData()
    formData.set('name', params.name)
    formData.set('file', params.file)

    return this.request<Project>('/projects/create', {
      method: 'POST',
      body: formData,
    })
  }

  async renameProject(projectId: string, newName: string) {
    return this.request<Project>(`/projects/${projectId}/rename`, {
      method: 'PATCH',
      body: JSON.stringify({ new_name: newName }),
      headers: {
        'Content-Type': 'application/json',
      },
    })
  }

  async deleteProject(projectId: string) {
    return this.request<void>(`/projects/${projectId}`, {
      method: 'DELETE',
      responseType: 'void',
    })
  }

  async startIndexing(projectId: string, documentId: string) {
    return this.request<IndexingStatus>(`/indexing/projects/${projectId}/documents/${documentId}/start`, {
      method: 'POST',
    })
  }

  async getLatestIndexStatus(projectId: string) {
    return this.request<IndexingStatus>(`/indexing/projects/${projectId}/latest`)
  }

  async getIndexStatus(indexId: string) {
    return this.request<IndexingStatus>(`/indexing/${indexId}`)
  }

  async cancelIndexing(indexId: string) {
    return this.request<void>(`/indexing/${indexId}/cancel`, {
      method: 'POST',
      responseType: 'void',
    })
  }

  async createChat(payload: CreateChatRequest) {
    return this.request<Chat>('/chats', {
      method: 'POST',
      body: JSON.stringify(payload),
      headers: {
        'Content-Type': 'application/json',
      },
    })
  }

  async listChats(projectId: string, limit = 50, offset = 0) {
    const search = new URLSearchParams({
      limit: String(limit),
      offset: String(offset),
    })

    return this.request<ListChatsResponse>(`/projects/${projectId}/chats?${search.toString()}`)
  }

  async deleteChat(chatId: string) {
    return this.request<void>(`/chats/${chatId}`, {
      method: 'DELETE',
      responseType: 'void',
    })
  }

  async getChatMessages(chatId: string, limit = 100) {
    const search = new URLSearchParams({
      limit: String(limit),
    })

    return this.request<ListMessagesResponse>(`/chats/${chatId}/messages?${search.toString()}`)
  }

  async streamProjectReply(
    payload: QueryRequest,
    options: {
      signal?: AbortSignal
      onChunk?: (event: StreamingReplyEvent) => void
    } = {},
  ) {
    const token = this.options.getToken()
    const response = await fetch(resolveApiUrl('/query'), {
      method: 'POST',
      signal: options.signal,
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify(payload),
    })

    if (!response.ok) {
      const body = await this.parseBody(response)
      const error = new ApiError(
        normalizeErrorMessage(body, `Request failed with status ${response.status}`),
        response.status,
        body,
      )
      if (response.status === 401 && token) {
        this.options.onUnauthorized?.(error)
      }
      throw error
    }

    if (!response.body) {
      return ''
    }

    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let accumulated = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) {
        break
      }

      const chunk = decoder.decode(value, { stream: true })
      if (!chunk) {
        continue
      }

      accumulated += chunk
      options.onChunk?.({
        text: chunk,
        accumulated,
      })
    }

    const tail = decoder.decode()
    if (tail) {
      accumulated += tail
      options.onChunk?.({
        text: tail,
        accumulated,
      })
    }

    return accumulated
  }
}
