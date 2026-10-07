import type { ButtonHTMLAttributes, ReactNode } from 'react'
import { useEffect } from 'react'

type Variant = 'primary' | 'secondary' | 'ghost' | 'danger'

const VARIANTS: Record<Variant, string> = {
  primary: 'bg-leaf-600 text-white hover:bg-leaf-700 focus-visible:outline-leaf-600',
  secondary:
    'border border-bark-200 bg-white text-bark-800 hover:bg-bark-50 focus-visible:outline-bark-700',
  ghost: 'text-bark-700 hover:bg-bark-100 focus-visible:outline-bark-700',
  danger: 'border border-red-200 bg-white text-red-700 hover:bg-red-50 focus-visible:outline-red-600',
}

export function Button({
  variant = 'primary',
  className = '',
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant }) {
  return (
    <button
      {...props}
      className={`inline-flex items-center justify-center gap-2 rounded-lg px-3.5 py-2
        text-sm font-medium transition-colors focus-visible:outline-2
        focus-visible:outline-offset-2 disabled:cursor-not-allowed disabled:opacity-50
        ${VARIANTS[variant]} ${className}`}
    />
  )
}

export function Card({ children, className = '' }: { children: ReactNode; className?: string }) {
  return (
    <div
      className={`rounded-xl border border-bark-200 bg-white shadow-sm shadow-bark-900/5 ${className}`}
    >
      {children}
    </div>
  )
}

export function PageHeader({
  title,
  subtitle,
  actions,
}: {
  title: string
  subtitle?: string
  actions?: ReactNode
}) {
  return (
    <header className="mb-6 flex flex-wrap items-end justify-between gap-4">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight text-bark-900">{title}</h1>
        {subtitle && <p className="mt-1 text-sm text-bark-700">{subtitle}</p>}
      </div>
      {actions && <div className="flex flex-wrap gap-2">{actions}</div>}
    </header>
  )
}

export function Alert({
  tone = 'error',
  children,
  onDismiss,
}: {
  tone?: 'error' | 'success' | 'info'
  children: ReactNode
  onDismiss?: () => void
}) {
  const tones = {
    error: 'border-red-200 bg-red-50 text-red-800',
    success: 'border-leaf-500/30 bg-leaf-50 text-leaf-700',
    info: 'border-bark-200 bg-bark-100/70 text-bark-800',
  }
  return (
    <div
      role="status"
      className={`mb-4 flex items-start gap-3 rounded-lg border px-4 py-3 text-sm ${tones[tone]}`}
    >
      <div className="flex-1">{children}</div>
      {onDismiss && (
        <button
          onClick={onDismiss}
          aria-label="Dismiss"
          className="shrink-0 opacity-60 hover:opacity-100"
        >
          ✕
        </button>
      )}
    </div>
  )
}

export function Modal({
  title,
  onClose,
  children,
  wide = false,
}: {
  title: string
  onClose: () => void
  children: ReactNode
  wide?: boolean
}) {
  useEffect(() => {
    const onKey = (event: KeyboardEvent) => event.key === 'Escape' && onClose()
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [onClose])

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto
        bg-bark-900/40 p-4 backdrop-blur-sm sm:p-8"
      onClick={onClose}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-label={title}
        onClick={(event) => event.stopPropagation()}
        className={`my-auto w-full rounded-xl bg-white shadow-xl ${wide ? 'max-w-3xl' : 'max-w-lg'}`}
      >
        <div className="flex items-center justify-between border-b border-bark-200 px-5 py-4">
          <h2 className="text-base font-semibold text-bark-900">{title}</h2>
          <button
            onClick={onClose}
            aria-label="Close"
            className="rounded p-1 text-bark-700 hover:bg-bark-100"
          >
            ✕
          </button>
        </div>
        <div className="px-5 py-5">{children}</div>
      </div>
    </div>
  )
}

export function EmptyState({ title, hint }: { title: string; hint?: string }) {
  return (
    <div className="px-6 py-16 text-center">
      <p className="text-sm font-medium text-bark-800">{title}</p>
      {hint && <p className="mt-1 text-sm text-bark-700">{hint}</p>}
    </div>
  )
}

export function Spinner({ label = 'Loading…' }: { label?: string }) {
  return (
    <div className="flex items-center justify-center gap-3 px-6 py-16 text-sm text-bark-700">
      <span className="size-4 animate-spin rounded-full border-2 border-bark-200 border-t-leaf-600" />
      {label}
    </div>
  )
}
