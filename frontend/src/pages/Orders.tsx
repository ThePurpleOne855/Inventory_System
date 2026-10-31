import { useCallback, useEffect, useMemo, useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'

import {
  Alert,
  Button,
  Card,
  EmptyState,
  Modal,
  PageHeader,
  Spinner,
} from '../components/ui'
import { api } from '../lib/api'
import { ClientContactFields } from '../components/ClientContactFields'
import { formatPhoneInput } from '../lib/phone'
import { dateTime, displayPhone, fullName, money, shortDate } from '../lib/format'
import type { Client, ClientInput, Invoice, Order, Product } from '../lib/types'

const PAGE_SIZE = 100

async function loadAll<T>(list: (limit: number, offset: number) => Promise<T[]>): Promise<T[]> {
  const result: T[] = []
  while (true) {
    const page = await list(PAGE_SIZE, result.length)
    result.push(...page)
    if (page.length < PAGE_SIZE) return result
  }
}

const EMPTY_CLIENT: ClientInput = {
  name: '', last_name: '', address: '', city: '', state: '', country: '', zipcode: '', phone_number: '', email: '', source: '',
}

export default function Orders() {
  const [orders, setOrders] = useState<Order[]>([])
  const [clients, setClients] = useState<Client[]>([])
  const [products, setProducts] = useState<Product[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [hasMore, setHasMore] = useState(false)
  const [creating, setCreating] = useState(false)
  const [invoiceFor, setInvoiceFor] = useState<number | null>(null)
  const [confirming, setConfirming] = useState<Order | null>(null)
  const [busyId, setBusyId] = useState<number | null>(null)

  const clientsById = useMemo(
    () => new Map(clients.map((client) => [client.id, client])),
    [clients],
  )

  const load = useCallback(async (offset = 0) => {
    setLoading(true)
    setError('')
    try {
      const [page, clientPage, productPage] = await Promise.all([
        api.orders.list(PAGE_SIZE, offset),
        loadAll(api.clients.list),
        loadAll(api.products.list),
      ])
      setOrders((previous) => (offset === 0 ? page : [...previous, ...page]))
      setClients(clientPage)
      setProducts(productPage)
      setHasMore(page.length === PAGE_SIZE)
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Could not load orders')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void load(0)
  }, [load])

  const sorted = useMemo(
    () => [...orders].sort((a, b) => b.id - a.id),
    [orders],
  )

  async function download(order: Order) {
    setBusyId(order.id)
    setError('')
    try {
      await api.invoices.download(order.id, `INV-${String(order.id).padStart(5, '0')}.pdf`)
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Could not download the invoice')
    } finally {
      setBusyId(null)
    }
  }

  async function emailInvoice(order: Order) {
    setBusyId(order.id)
    setError('')
    setNotice('')
    try {
      const result = await api.invoices.email(order.id)
      if (result.status === 'sent') {
        setNotice(`Invoice for order #${order.id} emailed to ${result.email}.`)
      } else {
        setError(`Could not email ${result.email}: ${result.detail}`)
      }
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Could not email the invoice')
    } finally {
      setBusyId(null)
    }
  }

  async function cancel(order: Order) {
    setConfirming(null)
    setError('')
    try {
      const cancelled = await api.orders.cancel(order.id)
      setOrders((previous) => previous.map((item) => (item.id === order.id ? cancelled : item)))
      setNotice(`Order #${order.id} was cancelled and its stock returned.`)
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Could not cancel the order')
    }
  }

  return (
    <>
      <PageHeader
        title="Orders"
        subtitle={`${orders.length} order${orders.length === 1 ? '' : 's'}`}
        actions={
          <Button onClick={() => setCreating(true)}>
            New order
          </Button>
        }
      />

      {error && <Alert onDismiss={() => setError('')}>{error}</Alert>}
      {notice && (
        <Alert tone="success" onDismiss={() => setNotice('')}>
          {notice}
        </Alert>
      )}

      <Card>
        {loading && orders.length === 0 ? (
          <Spinner label="Loading orders…" />
        ) : sorted.length === 0 ? (
          <EmptyState title="No orders yet" hint="Create an order to generate its invoice." />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-bark-200 text-left text-xs tracking-wide text-bark-700 uppercase">
                  <th className="px-4 py-3 font-semibold">Order</th>
                  <th className="px-4 py-3 font-semibold">Client</th>
                  <th className="px-4 py-3 font-semibold">Placed</th>
                  <th className="px-4 py-3 text-right font-semibold">Total</th>
                  <th className="px-4 py-3 text-right font-semibold">Invoice</th>
                </tr>
              </thead>
              <tbody>
                {sorted.map((order) => {
                  const client = clientsById.get(order.client_id)
                  const busy = busyId === order.id
                  const cancelled = order.cancelled_at !== null
                  return (
                    <tr key={order.id} className="border-b border-bark-100 last:border-0">
                      <td className="px-4 py-3 font-medium text-bark-900">#{order.id}</td>
                      <td className="px-4 py-3 text-bark-700">
                        {client ? fullName(client) : `Client #${order.client_id}`}
                      </td>
                      <td className="px-4 py-3 text-bark-700">{shortDate(order.created_at)}</td>
                      <td className="px-4 py-3 text-right font-medium text-bark-900">
                        {cancelled ? (
                          <>
                            <span className="mr-2 rounded bg-bark-100 px-1.5 py-0.5 text-xs font-medium text-bark-700">
                              Cancelled
                            </span>
                            <span className="text-bark-700 line-through">{money(order.total)}</span>
                          </>
                        ) : (
                          money(order.total)
                        )}
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex flex-wrap justify-end gap-1">
                          <Button variant="ghost" onClick={() => setInvoiceFor(order.id)}>
                            View
                          </Button>
                          <Button variant="ghost" disabled={busy} onClick={() => void download(order)}>
                            {busy ? '…' : 'PDF'}
                          </Button>
                          {!cancelled && (
                            <>
                              <Button
                                variant="ghost"
                                disabled={busy}
                                onClick={() => void emailInvoice(order)}
                              >
                                Email
                              </Button>
                              <Button variant="ghost" onClick={() => setConfirming(order)}>
                                Cancel
                              </Button>
                            </>
                          )}
                        </div>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}

        {hasMore && (
          <div className="border-t border-bark-200 p-4 text-center">
            <Button variant="secondary" disabled={loading} onClick={() => void load(orders.length)}>
              {loading ? 'Loading…' : 'Load more'}
            </Button>
          </div>
        )}
      </Card>

      {creating && (
        <OrderForm
          clients={clients}
          products={products}
          loading={loading}
          onClose={() => setCreating(false)}
          onCreated={(order) => {
            setOrders((previous) => [order, ...previous])
            setNotice(`Order #${order.id} created for ${money(order.total)}.`)
            setCreating(false)
            void load(0)
          }}
        />
      )}

      {invoiceFor !== null && (
        <InvoicePreview
          orderId={invoiceFor}
          onClose={() => setInvoiceFor(null)}
          onDownload={(order) => void download(order)}
        />
      )}

      {confirming && (
        <Modal title="Cancel order" onClose={() => setConfirming(null)}>
          <p className="text-sm text-bark-800">
            Cancel order <strong>#{confirming.id}</strong>? Its stock is returned to inventory.
            The order stays in your history but no longer counts as a sale.
          </p>
          <div className="mt-6 flex justify-end gap-2">
            <Button variant="secondary" onClick={() => setConfirming(null)}>
              Keep order
            </Button>
            <Button variant="danger" onClick={() => void cancel(confirming)}>
              Cancel order
            </Button>
          </div>
        </Modal>
      )}
    </>
  )
}

interface DraftLine {
  product_id: number
  quantity: number
}

function OrderForm({
  clients,
  products,
  loading,
  onClose,
  onCreated,
}: {
  clients: Client[]
  products: Product[]
  loading: boolean
  onClose: () => void
  onCreated: (order: Order) => void
}) {
  const [clientId, setClientId] = useState<number | ''>('')
  const [clientDetails, setClientDetails] = useState<ClientInput>({ ...EMPTY_CLIENT })
  const [clientSearch, setClientSearch] = useState('')
  const [lines, setLines] = useState<DraftLine[]>([])
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  const matchingClients = clients.filter((client) => client.id === clientId ||
    [fullName(client), client.email, displayPhone(client.phone_number)]
      .join(' ').toLowerCase().includes(clientSearch.trim().toLowerCase()))

  function selectClient(value: string) {
    const selected = clients.find((client) => client.id === Number(value))
    setClientId(selected?.id ?? '')
    setClientDetails(selected ? {
      name: selected.name,
      last_name: selected.last_name ?? '',
      address: selected.address ?? '',
      city: selected.city ?? '',
      state: selected.state ?? '',
      country: selected.country ?? '',
      zipcode: selected.zipcode ?? '',
      source: selected.source ?? '',
      phone_number: displayPhone(selected.phone_number),
      email: selected.email,
    } : { ...EMPTY_CLIENT })
    setError('')
  }

  const setClientField = (key: keyof ClientInput) =>
    (event: { target: { value: string } }) =>
      setClientDetails((previous) => ({ ...previous, [key]: event.target.value }))

  const productsById = useMemo(
    () => new Map(products.map((product) => [product.id, product])),
    [products],
  )
  const available = products.filter(
    (product) => !lines.some((line) => line.product_id === product.id),
  )

  const total = lines.reduce((sum, line) => {
    const product = productsById.get(line.product_id)
    return sum + (product ? Number(product.price) * line.quantity : 0)
  }, 0)

  function addLine(productId: number) {
    setLines((previous) => [...previous, { product_id: productId, quantity: 1 }])
  }

  function setQuantity(productId: number, quantity: number) {
    setLines((previous) =>
      previous.map((line) =>
        line.product_id === productId ? { ...line, quantity } : line,
      ),
    )
  }

  async function onSubmit(event: FormEvent) {
    event.preventDefault()
    if (busy || loading || lines.length === 0) return
    setError('')
    setBusy(true)
    try {
      onCreated(await api.orders.create({
        client_id: clientId === '' ? undefined : clientId,
        client: {
          ...clientDetails,
          name: clientDetails.name.trim(),
          last_name: clientDetails.last_name?.trim() || null,
          address: clientDetails.address?.trim() || null,
          email: clientDetails.email.trim(),
          phone_number: formatPhoneInput(clientDetails.phone_number, clientDetails.country),
        },
        products: lines,
      }))
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Could not create the order')
    } finally {
      setBusy(false)
    }
  }

  return (
    <Modal title="New order" onClose={() => { if (!busy) onClose() }} wide>
      {error && <Alert onDismiss={() => setError('')}>{error}</Alert>}
      <form onSubmit={onSubmit}>
        <fieldset disabled={busy || loading} className="space-y-5">
        {loading && <Spinner label="Loading clients and products…" />}
        <div>
          <label className="label" htmlFor="client-search">Find an existing client</label>
          <input
            id="client-search"
            className="field"
            placeholder="Search by name, email or phone"
            value={clientSearch}
            onChange={(event) => setClientSearch(event.target.value)}
          />
        </div>
        <div>
          <label className="label" htmlFor="client">
            Client
          </label>
          <select
            id="client"
            className="field"
            value={clientId}
            onChange={(event) => selectClient(event.target.value)}
          >
            <option value="">New client — enter details below</option>
            {matchingClients.map((client) => (
              <option key={client.id} value={client.id}>
                {fullName(client)} — {client.email}
              </option>
            ))}
          </select>
          <p className="mt-2 text-sm text-bark-700">
            {clientId === ''
              ? 'A client profile will be created when you save this order.'
              : 'Details filled from this profile. Any changes will also update the client profile.'}
          </p>
          {clientSearch && matchingClients.length === 0 && (
            <p className="mt-2 text-sm text-bark-700">No matching clients. Enter their details below to create a profile.</p>
          )}
        </div>

        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <label className="label" htmlFor="order-client-name">First name</label>
            <input id="order-client-name" className="field" required value={clientDetails.name} onChange={setClientField('name')} />
          </div>
          <div>
            <label className="label" htmlFor="order-client-last-name">Last name</label>
            <input id="order-client-last-name" className="field" value={clientDetails.last_name ?? ''} onChange={setClientField('last_name')} />
          </div>
          <div>
            <label className="label" htmlFor="order-client-email">Email</label>
            <input id="order-client-email" className="field" type="email" required value={clientDetails.email} onChange={setClientField('email')} />
          </div>
          <ClientContactFields
            prefix="order-client"
            value={clientDetails}
            required={clientId === ''}
            onChange={(change) => setClientDetails((previous) => ({ ...previous, ...change }))}
          />
        </div>

        <div>
          <span className="label">Items</span>
          {lines.length === 0 ? (
            <p className="rounded-lg border border-dashed border-bark-200 px-4 py-6 text-center text-sm text-bark-700">
              Add at least one product below.
            </p>
          ) : (
            <ul className="divide-y divide-bark-100 rounded-lg border border-bark-200">
              {lines.map((line) => {
                const product = productsById.get(line.product_id)
                if (!product) return null
                const overStock = line.quantity > product.quantity
                return (
                  <li
                    key={line.product_id}
                    className="flex flex-wrap items-center gap-3 px-3 py-2.5"
                  >
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm font-medium text-bark-900">
                        {product.name}
                      </p>
                      <p className="text-xs text-bark-700">
                        {money(product.price)} each · {product.quantity} in stock
                      </p>
                    </div>
                    <input
                      type="number"
                      min={1}
                      max={product.quantity}
                      aria-label={`Quantity of ${product.name}`}
                      className={`field w-20 ${overStock ? 'border-red-400' : ''}`}
                      value={line.quantity}
                      onChange={(event) =>
                        setQuantity(line.product_id, Math.max(1, Number(event.target.value)))
                      }
                    />
                    <span className="w-24 text-right text-sm font-medium text-bark-900">
                      {money(Number(product.price) * line.quantity)}
                    </span>
                    <Button
                      type="button"
                      variant="ghost"
                      onClick={() =>
                        setLines((previous) =>
                          previous.filter((item) => item.product_id !== line.product_id),
                        )
                      }
                    >
                      Remove
                    </Button>
                  </li>
                )
              })}
            </ul>
          )}

          {available.length > 0 ? (
            <select
              className="field mt-3"
              value=""
              onChange={(event) => event.target.value && addLine(Number(event.target.value))}
            >
              <option value="">Add a product…</option>
              {available.map((product) => (
                <option key={product.id} value={product.id} disabled={product.quantity < 1}>
                  {product.name} — {money(product.price)} ({product.quantity} in stock)
                </option>
              ))}
            </select>
          ) : (
            products.length === 0 && (
              <p className="mt-3 text-xs text-bark-700">
                No products exist yet — add them on the{' '}
                <Link to="/inventory" className="font-medium text-leaf-700 hover:underline">
                  Inventory
                </Link>{' '}
                page.
              </p>
            )
          )}
        </div>

        <div className="flex items-center justify-between border-t border-bark-200 pt-4">
          <span className="text-sm text-bark-700">Estimated total</span>
          <span className="text-lg font-semibold text-bark-900">{money(total)}</span>
        </div>

        <div className="flex justify-end gap-2">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" disabled={busy || loading || lines.length === 0}>
            {busy ? 'Creating…' : 'Create order'}
          </Button>
        </div>
        </fieldset>
      </form>
    </Modal>
  )
}

function InvoicePreview({
  orderId,
  onClose,
  onDownload,
}: {
  orderId: number
  onClose: () => void
  onDownload: (order: Order) => void
}) {
  const [invoice, setInvoice] = useState<Invoice | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    let cancelled = false
    api.invoices
      .get(orderId)
      .then((data) => !cancelled && setInvoice(data))
      .catch(
        (caught) =>
          !cancelled &&
          setError(caught instanceof Error ? caught.message : 'Could not load the invoice'),
      )
    return () => {
      cancelled = true
    }
  }, [orderId])

  return (
    <Modal title={`Invoice for order #${orderId}`} onClose={onClose} wide>
      {error && <Alert>{error}</Alert>}
      {!invoice && !error ? (
        <Spinner label="Building invoice…" />
      ) : (
        invoice && (
          <div className="space-y-5">
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div>
                <p className="text-xs tracking-wide text-bark-700 uppercase">Bill to</p>
                <p className="font-medium text-bark-900">{fullName(invoice.client)}</p>
                <p className="text-sm text-bark-700">{invoice.client.email}</p>
                {invoice.client.address && <p className="whitespace-pre-line text-sm text-bark-700">{invoice.client.address}</p>}
                <p className="text-sm text-bark-700">
                  {[invoice.client.city, invoice.client.state, invoice.client.zipcode, invoice.client.country].filter(Boolean).join(', ')}
                </p>
                <p className="text-sm text-bark-700">
                  {displayPhone(invoice.client.phone_number)}
                </p>
              </div>
              <div className="text-right text-sm">
                <p className="font-semibold text-bark-900">{invoice.invoice_number}</p>
                <p className="text-bark-700">{dateTime(invoice.created_at)}</p>
                <p className="text-bark-700">{invoice.company.name}</p>
              </div>
            </div>

            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-bark-200 text-left text-xs tracking-wide text-bark-700 uppercase">
                  <th className="py-2 font-semibold">Item</th>
                  <th className="py-2 text-right font-semibold">Qty</th>
                  <th className="py-2 text-right font-semibold">Unit</th>
                  <th className="py-2 text-right font-semibold">Amount</th>
                </tr>
              </thead>
              <tbody>
                {invoice.lines.map((line) => (
                  <tr key={line.product_id} className="border-b border-bark-100">
                    <td className="py-2 text-bark-900">{line.product_name}</td>
                    <td className="py-2 text-right text-bark-700">{line.quantity}</td>
                    <td className="py-2 text-right text-bark-700">
                      {money(line.unit_price, invoice.currency)}
                    </td>
                    <td className="py-2 text-right font-medium text-bark-900">
                      {money(line.line_total, invoice.currency)}
                    </td>
                  </tr>
                ))}
              </tbody>
              <tfoot>
                <tr>
                  <td colSpan={3} className="pt-3 text-right text-bark-700">
                    Total due
                  </td>
                  <td className="pt-3 text-right text-base font-semibold text-bark-900">
                    {money(invoice.total, invoice.currency)}
                  </td>
                </tr>
              </tfoot>
            </table>

            <div className="flex justify-end gap-2 border-t border-bark-200 pt-4">
              <Button variant="secondary" onClick={onClose}>
                Close
              </Button>
              <Button
                onClick={() =>
                  onDownload({
                    id: invoice.order_id,
                    client_id: invoice.client.id,
                    total: invoice.total,
                    created_at: invoice.created_at,
                    cancelled_at: null,
                  })
                }
              >
                Download PDF
              </Button>
            </div>
          </div>
        )
      )}
    </Modal>
  )
}
