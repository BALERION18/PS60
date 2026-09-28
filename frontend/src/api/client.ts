import axios from 'axios'

// Token stored in module memory — safe from XSS compared to localStorage
let _token: string | null = null

export function setToken(t: string | null) { _token = t }
export function getToken() { return _token }

const api = axios.create({
  baseURL: `${import.meta.env.VITE_API_BASE_URL || ''}/api/v1`,
  headers: { 'Content-Type': 'application/json' },
})

// Attach JWT on every request
api.interceptors.request.use((config) => {
  if (_token) config.headers.Authorization = `Bearer ${_token}`
  return config
})

// On 401 clear token so app redirects to login
api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      _token = null
      window.location.href = '/login'
    }
    return Promise.reject(err)
  }
)

export default api
