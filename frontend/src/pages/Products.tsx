import { useCallback, useEffect, useMemo, useState, type FormEvent } from 'react'

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
import { money } from '../lib/format'
import type { Product, ProductInput } from '../lib/types'

const PAGE_SIZE = 100

/** At or below this many units a product is worth restocking soon. */
const LOW_STOCK_AT = 5

type Status = 'out' | 'low' | 'in'
type StatusFilter = Status | 'all'
type SortKey = 'name' | 'stock' | 'value'

const statusOf = (product: Product): Status =>
  product.quantity <= 0 ? 'out' : product.quantity <= LOW_STOCK_AT ? 'low' : 'in'

const STATUS_LABEL: Record<Status, string> = {
  out: 'Out of stock',
  low: 'Low stock',
  in: 'In stock',
}

const STATUS_STYLE: Record<Status, string> = {
  out: 'bg-red-50 text-red-700 ring-red-600/20',
  low: 'bg-amber-50 text-amber-800 ring-amber-600/20',
  in: 'bg-leaf-50 text-leaf-700 ring-leaf-500/25',
}

function StatusBadge({ status }: { status: Status }) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium
        ring-1 ring-inset ${STATUS_STYLE[status]}`}
    >
      {STATUS_LABEL[status]}
    </span>
  )
}

function Tile({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <Card className="px-4 py-3">
      <p className="text-xs font-semibold tracking-wide text-bark-700 uppercase">{label}</p>
      <p className="mt-1 text-xl font-semibold text-bark-900">{value}</p>
      {hint && <p className="text-xs text-bark-700">{hint}</p>}
    </Card>
  )
}

export default function Products() {
  const [products, setProducts] = useState<Product[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [filter, setFilter] = useState('')
  const [status, setStatus] = useState<StatusFilter>('all')
  const [sort, setSort] = useState<SortKey>('name')
  const [hasMore, setHasMore] = useState(false)
  const [editing, setEditing] = useState<Product | 'new' | null>(null)
  const [confirming, setConfirming] = useState<Product | null>(null)
  const [adjusting, setAdjusting] = useState<number | null>(null)

  const load = useCallback(async (offset = 0) => {
    setLoading(true)
    setError('')
    try {
      const page = await api.products.list(PAGE_SIZE, offset)
      setProducts((previous) => (offset === 0 ? page : [...previous, ...page]))
      setHasMore(page.length === PAGE_SIZE)
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Could not load products')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void load(0)
  }, [load])

  const totals = useMemo(() => {
    const units = products.reduce((sum, product) => sum + product.quantity, 0)
    const value = products.reduce(
      (sum, product) => sum + Number(product.price) * product.quantity,
      0,
    )
    const out = products.filter((product) => statusOf(product) === 'out').length
    const low = products.filter((product) => statusOf(product) === 'low').length
    return { units, value, out, low }
  }, [products])

  const visible = useMemo(() => {
    const needle = filter.trim().toLowerCase()
    const matched = products.filter((product) => {
      if (status !== 'all' && statusOf(product) !== status) return false
      if (!needle) return true
      return [product.name, product.description ?? ''].join(' ').toLowerCase().includes(needle)
    })
    const sorters: Record<SortKey, (a: Product, b: Product) => number> = {
      name: (a, b) => a.name.localeCompare(b.name),
      stock: (a, b) => a.quantity - b.quantity,
      value: (a, b) =>
        Number(b.price) * b.quantity - Number(a.price) * a.quantity,
    }
    return [...matched].sort(sorters[sort])
  }, [products, filter, status, sort])

  /** Inline restock. Applies optimistically and rolls back if the API refuses. */
  async function adjust(product: Product, delta: number) {
    const quantity = Math.max(0, product.quantity + delta)
    if (quantity === product.quantity) return
    setAdjusting(product.id)
    setError('')
    setProducts((previous) =>
      previous.map((item) => (item.id === product.id ? { ...item, quantity } : item)),
    )
    try {
      const saved = await api.products.update(product.id, { quantity })
      setProducts((previous) =>
        previous.map((item) => (item.id === saved.id ? saved : item)),
      )
    } catch (caught) {
      setProducts((previous) =>
        previous.map((item) => (item.id === product.id ? product : item)),
      )
      setError(caught instanceof Error ? caught.message : 'Could not update the stock level')
    } finally {
      setAdjusting(null)
    }
  }

  async function remove(product: Product) {
    setConfirming(null)
    setError('')
    try {
      await api.products.remove(product.id)
      setProducts((previous) => previous.filter((item) => item.id !== product.id))
      setNotice(`${product.name} was deleted.`)
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Could not delete the product')
    }
  }

  const filters: { key: StatusFilter; label: string; count: number }[] = [
    { key: 'all', label: 'All', count: products.length },
    { key: 'in', label: 'In stock', count: products.length - totals.out - totals.low },
    { key: 'low', label: 'Low', count: totals.low },
    { key: 'out', label: 'Out', count: totals.out },
  ]

  return (
    <>
      <PageHeader
        title="Inventory"
        subtitle="Find an existing product and update its stock or price, or add a new product."
        actions={<Button onClick={() => setEditing('new')}>Add product</Button>}
      />

      {error && <Alert onDismiss={() => setError('')}>{error}</Alert>}
      {notice && (
        <Alert tone="success" onDismiss={() => setNotice('')}>
          {notice}
        </Alert>
      )}

      <div className="mb-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <Tile label="Products" value={String(products.length)} />
        <Tile label="Units in stock" value={totals.units.toLocaleString()} />
        <Tile label="Stock value" value={money(totals.value)} hint="Price × quantity on hand" />
        <Tile
          label="Needs attention"
          value={String(totals.out + totals.low)}
          hint={`${totals.out} out, ${totals.low} at or below ${LOW_STOCK_AT}`}
        />
      </div>

      <Card>
        <div className="flex flex-wrap items-center gap-3 border-b border-bark-200 p-4">
          <input
            className="field max-w-xs"
            placeholder="Filter by name or description…"
            value={filter}
            onChange={(event) => setFilter(event.target.value)}
          />
          <div className="flex gap-1">
            {filters.map((item) => (
              <button
                key={item.key}
                onClick={() => setStatus(item.key)}
                className={`rounded-lg px-3 py-1.5 text-sm font-medium transition-colors ${
                  status === item.key
                    ? 'bg-bark-800 text-white'
                    : 'text-bark-700 hover:bg-bark-100'
                }`}
              >
                {item.label} ({item.count})
              </button>
            ))}
          </div>
          <label className="ml-auto flex items-center gap-2 text-sm text-bark-700">
            Sort
            <select
              className="field w-auto py-1.5"
              value={sort}
              onChange={(event) => setSort(event.target.value as SortKey)}
            >
              <option value="name">Name</option>
              <option value="stock">Stock, lowest first</option>
              <option value="value">Stock value, highest first</option>
            </select>
          </label>
        </div>

        {loading && products.length === 0 ? (
          <Spinner label="Loading inventory…" />
        ) : visible.length === 0 ? (
          <EmptyState
            title={products.length === 0 ? 'No products yet' : 'Nothing matches those filters'}
            hint={
              products.length === 0
                ? 'Add your first product to start tracking stock.'
                : undefined
            }
          />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-bark-200 text-left text-xs tracking-wide text-bark-700 uppercase">
                  <th className="px-4 py-3 font-semibold">Product</th>
                  <th className="px-4 py-3 text-right font-semibold">Price</th>
                  <th className="px-4 py-3 text-center font-semibold">On hand</th>
                  <th className="px-4 py-3 font-semibold">Availability</th>
                  <th className="px-4 py-3 text-right font-semibold">Stock value</th>
                  <th className="px-4 py-3 text-right font-semibold">Actions</th>
                </tr>
              </thead>
              <tbody>
                {visible.map((product) => {
                  const busy = adjusting !== null
                  return (
                    <tr key={product.id} className="border-b border-bark-100 last:border-0">
                      <td className="px-4 py-3">
                        <p className="font-medium text-bark-900">{product.name}</p>
                        {product.description && (
                          <p className="text-xs text-bark-700">{product.description}</p>
                        )}
                      </td>
                      <td className="px-4 py-3 text-right text-bark-700">
                        {money(product.price)}
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex items-center justify-center gap-1">
                          <button
                            onClick={() => void adjust(product, -1)}
                            disabled={busy || product.quantity <= 0}
                            aria-label={`Remove one ${product.name}`}
                            className="size-7 rounded-md border border-bark-200 text-bark-700
                              hover:bg-bark-100 disabled:opacity-40"
                          >
                            −
                          </button>
                          <span className="w-12 text-center font-medium tabular-nums text-bark-900">
                            {product.quantity}
                          </span>
                          <button
                            onClick={() => void adjust(product, 1)}
                            disabled={busy}
                            aria-label={`Add one ${product.name}`}
                            className="size-7 rounded-md border border-bark-200 text-bark-700
                              hover:bg-bark-100 disabled:opacity-40"
                          >
                            +
                          </button>
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        <StatusBadge status={statusOf(product)} />
                      </td>
                      <td className="px-4 py-3 text-right text-bark-700 tabular-nums">
                        {money(Number(product.price) * product.quantity)}
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex flex-wrap justify-end gap-1">
                          <Button variant="ghost" disabled={busy} onClick={() => setEditing(product)}>
                            Edit
                          </Button>
                          <Button variant="ghost" disabled={busy} onClick={() => setConfirming(product)}>
                            Delete
                          </Button>
                        </div>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}

        {hasMore && !filter && status === 'all' && (
          <div className="border-t border-bark-200 p-4 text-center">
            <Button
              variant="secondary"
              disabled={loading}
              onClick={() => void load(products.length)}
            >
              {loading ? 'Loading…' : 'Load more'}
            </Button>
          </div>
        )}
      </Card>

      {editing && (
        <ProductForm
          product={editing === 'new' ? null : editing}
          onClose={() => setEditing(null)}
          onSaved={(saved, isNew) => {
            setProducts((previous) =>
              isNew
                ? [...previous, saved]
                : previous.map((item) => (item.id === saved.id ? saved : item)),
            )
            setNotice(`${saved.name} was ${isNew ? 'added' : 'updated'}.`)
            setEditing(null)
          }}
        />
      )}

      {confirming && (
        <Modal title="Delete product" onClose={() => setConfirming(null)}>
          <p className="text-sm text-bark-800">
            Delete <strong>{confirming.name}</strong>? Products that appear on an existing
            order cannot be deleted — set the quantity to 0 instead to take it off the shelf.
          </p>
          <div className="mt-6 flex justify-end gap-2">
            <Button variant="secondary" onClick={() => setConfirming(null)}>
              Cancel
            </Button>
            <Button variant="danger" onClick={() => void remove(confirming)}>
              Delete
            </Button>
          </div>
        </Modal>
      )}
    </>
  )
}

function ProductForm({
  product,
  onClose,
  onSaved,
}: {
  product: Product | null
  onClose: () => void
  onSaved: (product: Product, isNew: boolean) => void
}) {
  const isNew = product === null
  const [form, setForm] = useState<ProductInput>(
    product
      ? {
          name: product.name,
          description: product.description ?? '',
          // Trim the database's trailing zeros so the field reads "18.50".
          price: Number(product.price).toFixed(2),
          quantity: product.quantity,
        }
      : { name: '', description: '', price: '', quantity: 0 },
  )
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  async function onSubmit(event: FormEvent) {
    event.preventDefault()
    setError('')
    setBusy(true)
    try {
      const payload: ProductInput = {
        ...form,
        description: form.description?.trim() ? form.description.trim() : null,
      }
      const saved = isNew
        ? await api.products.create(payload)
        : await api.products.update(product.id, payload)
      onSaved(saved, isNew)
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Could not save the product')
    } finally {
      setBusy(false)
    }
  }

  return (
    <Modal title={isNew ? 'Add product' : `Edit ${product.name}`} onClose={onClose}>
      {error && <Alert onDismiss={() => setError('')}>{error}</Alert>}
      <form onSubmit={onSubmit} className="space-y-4">
        <div>
          <label className="label" htmlFor="name">
            Name
          </label>
          <input
            id="name"
            className="field"
            required
            value={form.name}
            onChange={(event) => setForm({ ...form, name: event.target.value })}
          />
        </div>
        <div>
          <label className="label" htmlFor="description">
            Description
          </label>
          <input
            id="description"
            className="field"
            placeholder="Optional"
            value={form.description ?? ''}
            onChange={(event) => setForm({ ...form, description: event.target.value })}
          />
        </div>
        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <label className="label" htmlFor="price">
              Unit price
            </label>
            <input
              id="price"
              type="number"
              step="0.01"
              min="0"
              className="field"
              required
              value={form.price}
              onChange={(event) => setForm({ ...form, price: event.target.value })}
            />
          </div>
          <div>
            <label className="label" htmlFor="quantity">
              Quantity on hand
            </label>
            <input
              id="quantity"
              type="number"
              min="0"
              step="1"
              className="field"
              required
              value={form.quantity}
              onChange={(event) =>
                setForm({ ...form, quantity: Math.max(0, Number(event.target.value)) })
              }
            />
          </div>
        </div>
        <div className="flex justify-end gap-2 pt-2">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" disabled={busy}>
            {busy ? 'Saving…' : isNew ? 'Add product' : 'Save changes'}
          </Button>
        </div>
      </form>
    </Modal>
  )
}
