export interface IndexingStatus {
  project_id: string
  document_id: string
  index_id: string
  storage_path: string
  status: string
  progress: number
  message?: string | null
  error?: string | null
  cancel_requested: boolean
  updated_at?: string | null
  meta?: Record<string, unknown> | null
}
