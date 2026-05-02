export interface ReplyMetricsPromptBreakdown {
  system: number
  history: number
  rewritten_question: number
  context: number
  question: number
  total: number
}

export interface ReplyMetrics {
  tokens: {
    prompt: ReplyMetricsPromptBreakdown
    completion: number
    total: number
  }
  latency: {
    query_rewriting?: number | null
    retrieval?: number | null
    reply_generation?: number | null
    total?: number | null
  }
}

export interface CitationChunk {
  chunk_id: string
  score?: number | null
  citation?: Record<string, unknown> | null
  content?: string | null
  matched_by?: number[] | null
}

export interface MessageCitations {
  index_id: string
  embed_signature: string
  metric: string
  chunks: CitationChunk[]
  top_k: number
  rerank_signature?: string | null
  prompt_version?: string | null
  model?: string | null
  rewritten_query?: string | null
  rewritten_queries?: string[] | null
  rewrite_strategy?: string | null
  original_query?: string | null
}

export interface Chat {
  id: string
  owner_id: string
  project_id: string
  title: string
  created_at: string
  updated_at: string
}

export interface ListChatsResponse {
  items: Chat[]
}

export interface ChatMessage {
  id: string
  chat_id: string
  role: string
  content: string
  created_at: string
  citations?: MessageCitations | null
  metrics?: ReplyMetrics | null
}

export interface ListMessagesResponse {
  items: ChatMessage[]
}

export interface CreateChatRequest {
  project_id: string
  title: string
}

export interface QueryRequest {
  project_id: string
  chat_id: string
  query: string
  top_k: number
  top_n: number
  rerank_timeout_s: number
}

export interface StreamingReplyEvent {
  text: string
  accumulated: string
}
