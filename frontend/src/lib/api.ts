import type {
  BroadcastResult,
  Client,
  ClientInput,
  Invoice,
  MailStatus,
  Order,
  OrderItem,
  Product,
  ProductInput,
  RecipientResult,
} from './types'

const BASE = import.meta.env.VITE_API_URL ?? '/api'
const TOKEN_KEY = 'madre-tierra.token'

/** Fired when the API rejects our token, so the app can drop to the login screen. */
export const UNAUTHORIZED_EVENT = 'madre-tierra:unauthorized'

export class ApiError extends Error {
  status: number

  constructor(status: number, message: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

export const getToken = (): string | null => localStorage.getItem(TOKEN_KEY)
export const setToken = (token: string) => localStorage.setItem(TOKEN_KEY, token)
export const clearToken = () => localStorage.removeItem(TOKEN_KEY)

function authHeaders(): Record<string, string> {
  const token = getToken()
  return token ? { Authorization: `Bearer ${token}` } : {}
}

async function errorFrom(response: Response): Promise<ApiError> {
  let detail = response.statusText || `Request failed (${response.status})`
  try {
    const body = await response.json()
    if (typeof body?.detail === 'string') {
      detail = body.detail
    } else if (Array.isArray(body?.detail)) {
      // FastAPI validation errors: "body.email: value is not a valid email"
      detail = body.detail
        .map((item: { loc?: unknown[]; msg?: string }) =>
          [item.loc?.slice(1).join('.'), item.msg].filter(Boolean).join(': '),
        )
        .join('; ')
    }
  } catch {
    /* response had no JSON body; the status text stands */
  }
  return new ApiError(response.status, detail)
}

async function send(path: string, init: RequestInit = {}): Promise<Response> {
  const headers: Record<string, string> = { ...authHeaders() }
  if (init.body !== undefined) headers['Content-Type'] = 'application/json'

  let response: Response
  try {
    response = await fetch(`${BASE}${path}`, {
      ...init,
      headers: { ...headers, ...(init.headers as Record<string, string>) },
    })
  } catch {
    throw new ApiError(0, 'Cannot reach the API. Is the server running on :8000?')
  }

  if (response.status === 401) {
    clearToken()
    window.dispatchEvent(new Event(UNAUTHORIZED_EVENT))
  }
  if (!response.ok) throw await errorFrom(response)
  return response
}

async function json<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await send(path, init)
  return response.status === 204 ? (undefined as T) : ((await response.json()) as T)
}

const body = (payload: unknown) => JSON.stringify(payload)
const query = (params: Record<string, string | number | undefined>) => {
  const search = new URLSearchParams()
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== '') search.set(key, String(value))
  }
  const text = search.toString()
  return text ? `?${text}` : ''
}

export const api = {
  auth: {
    login: (username: string, password: string) =>
      json<{ access_token: string; expires_in: number }>('/auth/login', {
        method: 'POST',
        body: body({ username, password }),
      }),
    me: () => json<{ username: string }>('/auth/me'),
    logout: () => send('/auth/logout', { method: 'POST' }),
  },

  clients: {
    list: (limit = 100, offset = 0) =>
      json<Client[]>(`/clients/${query({ limit, offset })}`),
    search: (params: { name?: string; email?: string; phone_number?: string }) =>
      json<Client[]>(`/clients/search${query({ ...params, limit: 50 })}`),
    get: (id: number) => json<Client>(`/clients/${id}`),
    create: (payload: ClientInput) =>
      json<Client>('/clients/', { method: 'POST', body: body(payload) }),
    update: (id: number, payload: ClientInput) =>
      json<Client>(`/clients/${id}`, { method: 'PUT', body: body(payload) }),
    remove: (id: number) => json<{ id: number }>(`/clients/${id}`, { method: 'DELETE' }),
  },

  products: {
    list: (limit = 100, offset = 0) =>
      json<Product[]>(`/products/${query({ limit, offset })}`),
    get: (id: number) => json<Product>(`/products/${id}`),
    create: (payload: ProductInput) =>
      json<Product>('/products/', { method: 'POST', body: body(payload) }),
    update: (id: number, payload: Partial<ProductInput>) =>
      json<Product>(`/products/${id}`, { method: 'PUT', body: body(payload) }),
    remove: (id: number) => json<{ id: number }>(`/products/${id}`, { method: 'DELETE' }),
  },

  orders: {
    list: (limit = 100, offset = 0) =>
      json<Order[]>(`/orders/${query({ limit, offset })}`),
    get: (id: number) => json<Order>(`/orders/${id}`),
    create: (payload: { client_id?: number; client?: Omit<ClientInput, 'password'>; products: { product_id: number; quantity: number }[] }) =>
      json<Order>('/orders/', { method: 'POST', body: body(payload) }),
    remove: (id: number) => json<{ id: number }>(`/orders/${id}`, { method: 'DELETE' }),
    items: (id: number) => json<OrderItem[]>(`/orders/${id}/items`),
  },

  invoices: {
    get: (orderId: number) => json<Invoice>(`/invoices/${orderId}`),
    email: (orderId: number) =>
      json<RecipientResult>(`/invoices/${orderId}/email`, { method: 'POST' }),
    /** Fetch with auth, then hand the browser a Blob so the PDF downloads. */
    download: async (orderId: number, filename: string) => {
      const response = await send(`/invoices/${orderId}/pdf`)
      const url = URL.createObjectURL(await response.blob())
      const link = document.createElement('a')
      link.href = url
      link.download = filename
      document.body.append(link)
      link.click()
      link.remove()
      URL.revokeObjectURL(url)
    },
  },

  messages: {
    status: () => json<MailStatus>('/messages/status'),
    broadcast: (payload: { subject: string; body: string; client_ids: number[] | null }) =>
      json<BroadcastResult>('/messages/broadcast', {
        method: 'POST',
        body: body(payload),
      }),
  },
}
