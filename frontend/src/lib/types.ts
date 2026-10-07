/** Mirrors app/schema/*.py. Pydantic serialises Decimal as a JSON string. */
export type Money = string

export interface Client {
  id: number
  name: string
  last_name: string | null
  address: string | null
  city: string | null
  state: string | null
  country: string | null
  zipcode: string | null
  email: string
  phone_number: string
}

export interface ClientInput {
  name: string
  last_name?: string | null
  address?: string | null
  city?: string | null
  state?: string | null
  country?: string | null
  zipcode?: string | null
  email: string
  phone_number: string
  password?: string
}

export interface Product {
  id: number
  name: string
  description: string | null
  price: Money
  quantity: number
}

export interface ProductInput {
  name: string
  description?: string | null
  price: Money
  quantity: number
}

export interface Order {
  id: number
  client_id: number
  total: Money
  created_at: string
}

export interface OrderItem {
  id: number
  order_id: number
  product_id: number
  quantity: number
  unit_price: Money
}

export interface InvoiceLine {
  product_id: number
  product_name: string
  quantity: number
  unit_price: Money
  line_total: Money
}

export interface Invoice {
  invoice_number: string
  order_id: number
  created_at: string
  client: Client
  lines: InvoiceLine[]
  subtotal: Money
  total: Money
  currency: string
  company: { name: string; address: string; email: string; phone: string }
}

export interface RecipientResult {
  client_id: number
  name: string
  email: string
  status: 'sent' | 'failed'
  detail: string
}

export interface BroadcastResult {
  sent: number
  failed: number
  results: RecipientResult[]
}

export interface MailStatus {
  configured: boolean
  host: string
  sender: string
}
