export interface ApiErrorPayload {
  detail?: string | Record<string, unknown> | unknown[]
}

export interface HealthResponse {
  status: string
}
