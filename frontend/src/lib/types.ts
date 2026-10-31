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
  source: string | null
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
  source?: string | null
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
  cancelled_at: string | null
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

/** Mirrors app/schema/analytics.py. Months are YYYY-MM in the business time zone. */
export interface PeriodTotals {
  revenue: Money
  orders: number
  average_order: Money
  new_customers: number
  repeat_customers: number
  cancelled_orders: number
}

export interface MonthTotals {
  month: string
  revenue: Money
  orders: number
  new_customers: number
}

export interface AnalyticsSummary {
  start: string
  end: string
  timezone: string
  currency: string
  current: PeriodTotals
  previous: PeriodTotals
  monthly: MonthTotals[]
  top_products: { product_id: number; name: string; units: number; revenue: Money }[]
  new_customers_by_source: { source: string; customers: number }[]
  low_stock: {
    product_id: number
    name: string
    quantity: number
    sold_last_30_days: number
    days_left: number | null
  }[]
}
