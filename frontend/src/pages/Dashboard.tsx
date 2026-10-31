import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

import { Alert, Card, PageHeader, Spinner } from '../components/ui'
import { api } from '../lib/api'
import { money } from '../lib/format'
import type { AnalyticsSummary, MonthTotals } from '../lib/types'

const RANGES = [
  { id: '30d', label: 'Last 30 days', start: (t: Date) => new Date(t.getFullYear(), t.getMonth(), t.getDate() - 29) },
  { id: '90d', label: 'Last 90 days', start: (t: Date) => new Date(t.getFullYear(), t.getMonth(), t.getDate() - 89) },
  { id: '12m', label: 'Last 12 months', start: (t: Date) => new Date(t.getFullYear(), t.getMonth() - 11, 1) },
  { id: 'ytd', label: 'This year', start: (t: Date) => new Date(t.getFullYear(), 0, 1) },
] as const
type RangeId = (typeof RANGES)[number]['id']

const isoDay = (day: Date) =>
  `${day.getFullYear()}-${String(day.getMonth() + 1).padStart(2, '0')}-${String(day.getDate()).padStart(2, '0')}`

/** Parse YYYY-MM(-DD) as a local date; new Date('2026-01-01') would be UTC and can show the day before. */
const localDay = (iso: string) => {
  const [year, month, day = 1] = iso.split('-').map(Number)
  return new Date(year, month - 1, day)
}
const longDay = (iso: string) =>
  localDay(iso).toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: 'numeric' })
const shortMonth = (month: string) => localDay(month).toLocaleDateString(undefined, { month: 'short' })
const longMonth = (month: string) =>
  localDay(month).toLocaleDateString(undefined, { month: 'long', year: 'numeric' })

const count = (value: number) => value.toLocaleString()
const compactMoney = (value: number, currency: string) =>
  `${currency}${value.toLocaleString(undefined, { notation: 'compact', maximumFractionDigits: 1 })}`
const tileMoney = (value: number, currency: string) =>
  value >= 10_000 ? compactMoney(value, currency) : money(value, currency)

/** Round an axis maximum up to a clean number whose half is also clean (2,000 / 3,000 / 40). */
function niceMax(value: number): number {
  if (value <= 0) return 1
  const power = 10 ** Math.floor(Math.log10(value))
  const step = [1, 2, 3, 4, 5, 6, 8, 10].find((candidate) => value <= candidate * power) ?? 10
  return step * power
}

export default function Dashboard() {
  const [rangeId, setRangeId] = useState<RangeId>('12m')
  const [summary, setSummary] = useState<AnalyticsSummary | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    let cancelled = false
    const today = new Date()
    const range = RANGES.find((item) => item.id === rangeId) ?? RANGES[2]
    api.analytics
      .summary(isoDay(range.start(today)), isoDay(today))
      .then((data) => !cancelled && setSummary(data))
      .catch(
        (caught) =>
          !cancelled &&
          setError(caught instanceof Error ? caught.message : 'Could not load the dashboard'),
      )
      .finally(() => !cancelled && setLoading(false))
    return () => {
      cancelled = true
    }
  }, [rangeId])

  function selectRange(id: RangeId) {
    if (id === rangeId) return
    setRangeId(id)
    setLoading(true)
    setError('')
  }

  return (
    <>
      <PageHeader
        title="Dashboard"
        subtitle={
          summary
            ? `${longDay(summary.start)} – ${longDay(summary.end)}`
            : 'Sales and customers at a glance'
        }
      />

      <div className="mb-6 flex flex-wrap items-center gap-x-4 gap-y-2">
        <div role="group" aria-label="Date range" className="flex flex-wrap gap-1 rounded-lg bg-bark-100 p-1">
          {RANGES.map((range) => (
            <button
              key={range.id}
              aria-pressed={range.id === rangeId}
              onClick={() => selectRange(range.id)}
              className={`rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
                range.id === rangeId
                  ? 'bg-white text-bark-900 shadow-sm'
                  : 'text-bark-700 hover:text-bark-900'
              }`}
            >
              {range.label}
            </button>
          ))}
        </div>
        <p className="text-xs text-bark-700">
          Changes compare with the period of the same length just before.
        </p>
      </div>

      {error && <Alert onDismiss={() => setError('')}>{error}</Alert>}

      {!summary ? (
        loading && <Spinner label="Loading dashboard…" />
      ) : (
        <div
          aria-busy={loading}
          className={`space-y-6 transition-opacity ${loading ? 'opacity-60' : ''}`}
        >
          <KpiRow summary={summary} />

          <div className="grid gap-6 lg:grid-cols-2">
            <ChartCard title="Revenue by month">
              <ColumnChart
                months={summary.monthly}
                value={(month) => Number(month.revenue)}
                format={(value) => money(value, summary.currency)}
                axis={(value) => compactMoney(value, summary.currency)}
              />
            </ChartCard>
            <ChartCard title="New customers by month" subtitle="Counted in the month of their first order">
              <ColumnChart
                months={summary.monthly}
                value={(month) => month.new_customers}
                format={(value) => `${count(value)} new`}
                axis={count}
                integer
              />
            </ChartCard>
            <MonthlyTable summary={summary} />
            <ChartCard title="Top products" subtitle="By revenue in this period">
              <RankedBars
                empty="No sales in this period."
                rows={summary.top_products.map((product) => ({
                  key: String(product.product_id),
                  label: product.name,
                  value: Number(product.revenue),
                  display: money(product.revenue, summary.currency),
                  detail: `${count(product.units)} sold`,
                }))}
              />
            </ChartCard>
            <ChartCard title="Where new customers came from" subtitle="From “How they found you” on the client profile">
              <RankedBars
                empty="No new customers in this period."
                rows={summary.new_customers_by_source.map((source) => ({
                  key: source.source,
                  label: source.source,
                  value: source.customers,
                  display: count(source.customers),
                }))}
              />
            </ChartCard>
          </div>

          <LowStock rows={summary.low_stock} />
        </div>
      )}
    </>
  )
}

function KpiRow({ summary }: { summary: AnalyticsSummary }) {
  const { current, previous, currency } = summary
  const tiles = [
    {
      label: 'Revenue',
      value: tileMoney(Number(current.revenue), currency),
      now: Number(current.revenue),
      before: Number(previous.revenue),
    },
    {
      label: 'Orders',
      value: count(current.orders),
      now: current.orders,
      before: previous.orders,
      note: current.cancelled_orders ? `${count(current.cancelled_orders)} cancelled` : undefined,
    },
    {
      label: 'Average order',
      value: tileMoney(Number(current.average_order), currency),
      now: Number(current.average_order),
      before: Number(previous.average_order),
    },
    {
      label: 'New customers',
      value: count(current.new_customers),
      now: current.new_customers,
      before: previous.new_customers,
    },
    {
      label: 'Repeat customers',
      value: count(current.repeat_customers),
      now: current.repeat_customers,
      before: previous.repeat_customers,
      note: 'Bought 2 or more times',
    },
  ]
  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
      {tiles.map((tile) => (
        <Card key={tile.label} className="p-4">
          <p className="text-xs font-medium text-bark-700">{tile.label}</p>
          <p className="mt-1 text-2xl font-semibold tracking-tight text-bark-900">{tile.value}</p>
          <Delta now={tile.now} before={tile.before} />
          {tile.note && <p className="mt-0.5 text-xs text-bark-700">{tile.note}</p>}
        </Card>
      ))}
    </div>
  )
}

function Delta({ now, before }: { now: number; before: number }) {
  if (before === 0) {
    return (
      <p className="mt-1 text-xs text-bark-700">
        {now === 0 ? 'No change' : 'None in previous period'}
      </p>
    )
  }
  const change = (now - before) / before
  const flat = Math.abs(change) < 0.005
  const tone = flat ? 'text-bark-700' : change > 0 ? 'text-leaf-700' : 'text-red-700'
  const arrow = flat ? '→' : change > 0 ? '↑' : '↓'
  const amount = Math.abs(change).toLocaleString(undefined, { style: 'percent', maximumFractionDigits: 0 })
  return (
    <p className={`mt-1 text-xs font-medium ${tone}`}>
      <span aria-hidden="true">{arrow}</span> {flat ? 'No change' : `${change > 0 ? 'Up' : 'Down'} ${amount}`}
    </p>
  )
}

function ChartCard({
  title,
  subtitle,
  children,
}: {
  title: string
  subtitle?: string
  children: React.ReactNode
}) {
  return (
    <Card className="p-5">
      <h2 className="text-sm font-semibold text-bark-900">{title}</h2>
      {subtitle && <p className="mt-0.5 text-xs text-bark-700">{subtitle}</p>}
      <div className="mt-4">{children}</div>
    </Card>
  )
}

function ColumnChart({
  months,
  value,
  format,
  axis,
  integer = false,
}: {
  months: MonthTotals[]
  value: (month: MonthTotals) => number
  format: (value: number) => string
  axis: (value: number) => string
  integer?: boolean
}) {
  const [active, setActive] = useState<number | null>(null)
  const values = months.map(value)
  const max = niceMax(Math.max(...values, 0))
  const ticks = [max, max / 2, 0].filter((tick) => !integer || Number.isInteger(tick))
  const latest = values.length - 1
  const crowded = months.length > 6

  return (
    <div>
      <div className="flex h-44 pt-5">
        <div className="relative w-12 shrink-0 text-right text-[11px] text-bark-700 tabular-nums">
          {ticks.map((tick) => (
            <span
              key={tick}
              className="absolute right-2 -translate-y-1/2"
              style={{ top: `${(1 - tick / max) * 100}%` }}
            >
              {axis(tick)}
            </span>
          ))}
        </div>
        <div className="relative flex-1">
          {ticks.map((tick) => (
            <div
              key={tick}
              className={`absolute inset-x-0 border-t ${tick === 0 ? 'border-bark-200' : 'border-bark-100'}`}
              style={{ top: `${(1 - tick / max) * 100}%` }}
            />
          ))}
          <div className="absolute inset-0 flex items-end">
            {months.map((month, index) => {
              const height = `${(values[index] / max) * 100}%`
              return (
                <div
                  key={month.month}
                  tabIndex={0}
                  aria-label={`${longMonth(month.month)}: ${format(values[index])}`}
                  onPointerEnter={() => setActive(index)}
                  onPointerLeave={() => setActive(null)}
                  onFocus={() => setActive(index)}
                  onBlur={() => setActive(null)}
                  className="relative flex h-full flex-1 items-end justify-center px-0.5 outline-none focus-visible:bg-leaf-50"
                >
                  <div
                    className={`w-full max-w-6 rounded-t transition-colors ${
                      active === index ? 'bg-leaf-500' : 'bg-leaf-600'
                    }`}
                    style={{ height }}
                  />
                  {active === index ? (
                    <div
                      role="tooltip"
                      className="pointer-events-none absolute left-1/2 z-10 mb-2 -translate-x-1/2 rounded-md bg-bark-900 px-2.5 py-1.5 text-xs whitespace-nowrap text-white shadow-lg"
                      style={{ bottom: height }}
                    >
                      <span className="block font-semibold">{format(values[index])}</span>
                      <span className="block text-white/70">{longMonth(month.month)}</span>
                    </div>
                  ) : (
                    index === latest &&
                    values[index] > 0 && (
                      <span
                        className="absolute mb-1 text-[11px] font-medium whitespace-nowrap text-bark-800"
                        style={{ bottom: height }}
                      >
                        {axis(values[index])}
                      </span>
                    )
                  )}
                </div>
              )
            })}
          </div>
        </div>
      </div>
      <div className="mt-1.5 ml-12 flex text-[11px] text-bark-700">
        {months.map((month, index) => (
          <span
            key={month.month}
            className={`flex-1 text-center ${crowded && (latest - index) % 2 ? 'invisible sm:visible' : ''}`}
          >
            {shortMonth(month.month)}
          </span>
        ))}
      </div>
    </div>
  )
}

function MonthlyTable({ summary }: { summary: AnalyticsSummary }) {
  return (
    <details className="text-sm lg:col-span-2">
      <summary className="cursor-pointer text-xs font-medium text-bark-700 hover:text-bark-900">
        Show monthly numbers as a table
      </summary>
      <Card className="mt-2 overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="border-b border-bark-200 text-left text-xs tracking-wide text-bark-700 uppercase">
              <th className="px-4 py-2 font-semibold">Month</th>
              <th className="px-4 py-2 text-right font-semibold">Revenue</th>
              <th className="px-4 py-2 text-right font-semibold">Orders</th>
              <th className="px-4 py-2 text-right font-semibold">New customers</th>
            </tr>
          </thead>
          <tbody className="tabular-nums">
            {summary.monthly.map((month) => (
              <tr key={month.month} className="border-b border-bark-100 last:border-0">
                <td className="px-4 py-2 text-bark-900">{longMonth(month.month)}</td>
                <td className="px-4 py-2 text-right text-bark-900">{money(month.revenue, summary.currency)}</td>
                <td className="px-4 py-2 text-right text-bark-700">{count(month.orders)}</td>
                <td className="px-4 py-2 text-right text-bark-700">{count(month.new_customers)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
    </details>
  )
}

function RankedBars({
  rows,
  empty,
}: {
  rows: { key: string; label: string; value: number; display: string; detail?: string }[]
  empty: string
}) {
  if (rows.length === 0) return <p className="py-8 text-center text-sm text-bark-700">{empty}</p>
  const max = Math.max(...rows.map((row) => row.value))
  return (
    <ul className="space-y-3">
      {rows.map((row) => (
        <li key={row.key}>
          <div className="mb-1 flex items-baseline justify-between gap-3 text-sm">
            <span className="truncate text-bark-900">{row.label}</span>
            <span className="shrink-0 font-medium text-bark-900 tabular-nums">
              {row.display}
              {row.detail && <span className="ml-2 font-normal text-bark-700">{row.detail}</span>}
            </span>
          </div>
          <div
            className="h-2 rounded-r bg-leaf-600"
            style={{ width: `${max > 0 ? (row.value / max) * 100 : 0}%` }}
          />
        </li>
      ))}
    </ul>
  )
}

function LowStock({ rows }: { rows: AnalyticsSummary['low_stock'] }) {
  return (
    <Card>
      <div className="flex flex-wrap items-baseline justify-between gap-2 border-b border-bark-200 px-5 py-4">
        <div>
          <h2 className="text-sm font-semibold text-bark-900">Running low</h2>
          <p className="mt-0.5 text-xs text-bark-700">
            5 or fewer left, or out within 30 days at the last 30 days’ pace
          </p>
        </div>
        <Link to="/inventory" className="text-sm font-medium text-leaf-700 hover:underline">
          Restock in Inventory
        </Link>
      </div>
      {rows.length === 0 ? (
        <p className="px-5 py-8 text-center text-sm text-bark-700">Nothing is running low.</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-bark-200 text-left text-xs tracking-wide text-bark-700 uppercase">
                <th className="px-5 py-2 font-semibold">Product</th>
                <th className="px-5 py-2 font-semibold">Status</th>
                <th className="px-5 py-2 text-right font-semibold">In stock</th>
                <th className="px-5 py-2 text-right font-semibold">Sold, 30 days</th>
                <th className="px-5 py-2 text-right font-semibold">Runs out</th>
              </tr>
            </thead>
            <tbody className="tabular-nums">
              {rows.map((row) => (
                <tr key={row.product_id} className="border-b border-bark-100 last:border-0">
                  <td className="px-5 py-2.5 font-medium text-bark-900">{row.name}</td>
                  <td className="px-5 py-2.5">
                    {row.quantity === 0 ? (
                      <span className="inline-flex items-center gap-1 rounded bg-red-50 whitespace-nowrap px-1.5 py-0.5 text-xs font-medium text-red-800">
                        <span aria-hidden="true">✕</span> Out of stock
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1 rounded bg-amber-50 whitespace-nowrap px-1.5 py-0.5 text-xs font-medium text-amber-800">
                        <span aria-hidden="true">!</span> Low
                      </span>
                    )}
                  </td>
                  <td className="px-5 py-2.5 text-right text-bark-900">{count(row.quantity)}</td>
                  <td className="px-5 py-2.5 text-right text-bark-700">{count(row.sold_last_30_days)}</td>
                  <td className="px-5 py-2.5 text-right text-bark-700">
                    {row.days_left === null
                      ? 'No recent sales'
                      : row.days_left === 0
                        ? 'Now'
                        : `~${count(row.days_left)} days`}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Card>
  )
}
