import api from './client'

export interface TokenResponse {
  access_token: string
  token_type: string
  expires_in: number
  refresh_token: string
}

export interface UserOut {
  user_id: string
  username: string
  email: string
  roles: string[]
  is_active: boolean
}

/** POST /auth/token */
export async function login(username: string, password: string): Promise<TokenResponse> {
  const { data } = await api.post<TokenResponse>('/auth/token', { username, password })
  return data
}

/** GET /auth/me */
export async function getMe(): Promise<UserOut> {
  const { data } = await api.get<UserOut>('/auth/me')
  return data
}

/** POST /auth/logout */
export async function logout(refreshToken: string) {
  await api.post('/auth/logout', { refresh_token: refreshToken })
}
