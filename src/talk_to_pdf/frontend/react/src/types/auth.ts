export interface LoginRequest {
  email: string
  password: string
}

export interface RegisterRequest {
  email: string
  name: string
  password: string
}

export interface TokenResponse {
  access_token: string
  token_type: string
}

export interface AuthUser {
  id: string
  email: string
  name: string
  is_active?: boolean
  created_at?: string
}
