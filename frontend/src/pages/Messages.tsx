import { useEffect, useMemo, useState, type FormEvent } from 'react'

import { Alert, Button, Card, EmptyState, PageHeader, Spinner } from '../components/ui'
import { api } from '../lib/api'
import { displayPhone, fullName, personalize, whatsappLink, whatsappNumber } from '../lib/format'
import type { BroadcastResult, Client, MailStatus } from '../lib/types'

export default function Messages() {
  const [clients, setClients] = useState<Client[]>([])
  const [mail, setMail] = useState<MailStatus | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [filter, setFilter] = useState('')
  const [selected, setSelected] = useState<Set<number>>(new Set())
  const [subject, setSubject] = useState('')
  const [body, setBody] = useState('')
  const [sending, setSending] = useState(false)
  const [result, setResult] = useState<BroadcastResult | null>(null)

  useEffect(() => {
    let cancelled = false
    Promise.all([api.clients.list(100, 0), api.messages.status()])
      .then(([clientPage, status]) => {
        if (cancelled) return
        setClients(clientPage)
        setMail(status)
        setSelected(new Set(clientPage.map((client) => client.id)))
      })
      .catch(
        (caught) =>
          !cancelled &&
          setError(caught instanceof Error ? caught.message : 'Could not load clients'),
      )
      .finally(() => !cancelled && setLoading(false))
    return () => {
      cancelled = true
    }
  }, [])

  const visible = useMemo(() => {
    const needle = filter.trim().toLowerCase()
    if (!needle) return clients
    return clients.filter((client) =>
      [fullName(client), client.email].join(' ').toLowerCase().includes(needle),
    )
  }, [clients, filter])

  const recipients = clients.filter((client) => selected.has(client.id))
  const preview = recipients[0]

  function toggle(id: number) {
    setSelected((previous) => {
      const next = new Set(previous)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  async function send(event: FormEvent) {
    event.preventDefault()
    setError('')
    setResult(null)
    setSending(true)
    try {
      setResult(
        await api.messages.broadcast({
          subject,
          body,
          client_ids: [...selected],
        }),
      )
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Could not send the broadcast')
    } finally {
      setSending(false)
    }
  }

  if (loading) return <Spinner label="Loading clients…" />

  return (
    <>
      <PageHeader
        title="Messages"
        subtitle="Email every selected client at once, or open a WhatsApp chat one at a time."
      />

      {error && <Alert onDismiss={() => setError('')}>{error}</Alert>}
      {mail && !mail.configured && (
        <Alert tone="info">
          Email sending is off until SMTP is configured. Set <code>SMTP_HOST</code>,{' '}
          <code>SMTP_USER</code>, <code>SMTP_PASSWORD</code> and <code>SMTP_FROM</code> in{' '}
          <code>.env</code>, then restart the API. WhatsApp links below work regardless.
        </Alert>
      )}
      {result && (
        <Alert tone={result.failed === 0 ? 'success' : 'error'} onDismiss={() => setResult(null)}>
          <p className="font-medium">
            Sent to {result.sent} client{result.sent === 1 ? '' : 's'}
            {result.failed > 0 && `, ${result.failed} failed`}.
          </p>
          {result.failed > 0 && (
            <ul className="mt-2 space-y-0.5 text-xs">
              {result.results
                .filter((item) => item.status === 'failed')
                .map((item) => (
                  <li key={item.client_id}>
                    {item.email}: {item.detail}
                  </li>
                ))}
            </ul>
          )}
        </Alert>
      )}

      <div className="grid gap-6 lg:grid-cols-[22rem_1fr]">
        <Card className="h-fit">
          <div className="flex items-center justify-between border-b border-bark-200 px-4 py-3">
            <p className="text-sm font-semibold text-bark-900">
              Recipients ({selected.size}/{clients.length})
            </p>
            <div className="flex gap-1">
              <Button
                variant="ghost"
                onClick={() => setSelected(new Set(clients.map((client) => client.id)))}
              >
                All
              </Button>
              <Button variant="ghost" onClick={() => setSelected(new Set())}>
                None
              </Button>
            </div>
          </div>
          <div className="border-b border-bark-200 p-3">
            <input
              className="field"
              placeholder="Filter clients…"
              value={filter}
              onChange={(event) => setFilter(event.target.value)}
            />
          </div>
          {visible.length === 0 ? (
            <EmptyState title="No clients match" />
          ) : (
            <ul className="max-h-96 divide-y divide-bark-100 overflow-y-auto">
              {visible.map((client) => (
                <li key={client.id} className="flex items-center gap-3 px-4 py-2.5">
                  <input
                    type="checkbox"
                    id={`client-${client.id}`}
                    className="size-4 accent-leaf-600"
                    checked={selected.has(client.id)}
                    onChange={() => toggle(client.id)}
                  />
                  <label htmlFor={`client-${client.id}`} className="min-w-0 flex-1 cursor-pointer">
                    <span className="block truncate text-sm font-medium text-bark-900">
                      {fullName(client)}
                    </span>
                    <span className="block truncate text-xs text-bark-700">{client.email}</span>
                  </label>
                  {whatsappNumber(client.phone_number) && (
                    <a
                      href={whatsappLink(client.phone_number, personalize(body, client))}
                      target="_blank"
                      rel="noreferrer"
                      title={`WhatsApp ${displayPhone(client.phone_number)}`}
                      className="shrink-0 rounded-md px-2 py-1 text-xs font-medium text-leaf-700 hover:bg-leaf-50"
                    >
                      WhatsApp
                    </a>
                  )}
                </li>
              ))}
            </ul>
          )}
        </Card>

        <Card className="p-5">
          <form onSubmit={send} className="space-y-4">
            <div>
              <label className="label" htmlFor="subject">
                Subject
              </label>
              <input
                id="subject"
                className="field"
                required
                maxLength={200}
                value={subject}
                onChange={(event) => setSubject(event.target.value)}
              />
            </div>
            <div>
              <label className="label" htmlFor="body">
                Message
              </label>
              <textarea
                id="body"
                className="field min-h-56 resize-y"
                required
                maxLength={20000}
                placeholder={'Hi {name},\n\nOur spring seedlings are in…'}
                value={body}
                onChange={(event) => setBody(event.target.value)}
              />
              <p className="mt-1.5 text-xs text-bark-700">
                Placeholders <code>{'{name}'}</code>, <code>{'{last_name}'}</code> and{' '}
                <code>{'{full_name}'}</code> are filled in per client. Each person receives
                their own email — nobody sees the other recipients.
              </p>
            </div>

            {preview && body && (
              <div className="rounded-lg border border-bark-200 bg-bark-50 p-3">
                <p className="mb-1 text-xs font-semibold tracking-wide text-bark-700 uppercase">
                  Preview for {fullName(preview)}
                </p>
                <p className="text-sm font-medium text-bark-900">
                  {personalize(subject, preview)}
                </p>
                <p className="mt-1 text-sm whitespace-pre-wrap text-bark-800">
                  {personalize(body, preview)}
                </p>
              </div>
            )}

            <div className="flex items-center justify-between gap-3 border-t border-bark-200 pt-4">
              <p className="text-sm text-bark-700">
                {selected.size === 0
                  ? 'Select at least one client.'
                  : `Will email ${selected.size} client${selected.size === 1 ? '' : 's'}.`}
              </p>
              <Button
                type="submit"
                disabled={sending || selected.size === 0 || !mail?.configured}
              >
                {sending ? 'Sending…' : 'Send email'}
              </Button>
            </div>
          </form>
        </Card>
      </div>
    </>
  )
}
