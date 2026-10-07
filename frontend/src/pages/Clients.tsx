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
import { ClientContactFields } from '../components/ClientContactFields'
import { formatPhoneInput } from '../lib/phone'
import { displayPhone, fullName, whatsappLink } from '../lib/format'
import type { Client, ClientInput } from '../lib/types'

const PAGE_SIZE = 100

const BLANK: ClientInput = {
  name: '',
  last_name: '',
  email: '',
  phone_number: '',
  password: '',
}

export default function Clients() {
  const [clients, setClients] = useState<Client[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [filter, setFilter] = useState('')
  const [hasMore, setHasMore] = useState(false)
  const [editing, setEditing] = useState<Client | 'new' | null>(null)
  const [confirming, setConfirming] = useState<Client | null>(null)

  const load = useCallback(async (offset = 0) => {
    setLoading(true)
    setError('')
    try {
      const page = await api.clients.list(PAGE_SIZE, offset)
      setClients((previous) => (offset === 0 ? page : [...previous, ...page]))
      setHasMore(page.length === PAGE_SIZE)
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Could not load clients')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void load(0)
  }, [load])

  const visible = useMemo(() => {
    const needle = filter.trim().toLowerCase()
    if (!needle) return clients
    return clients.filter((client) =>
      [fullName(client), client.email, displayPhone(client.phone_number)]
        .join(' ')
        .toLowerCase()
        .includes(needle),
    )
  }, [clients, filter])

  async function remove(client: Client) {
    setConfirming(null)
    setError('')
    try {
      await api.clients.remove(client.id)
      setClients((previous) => previous.filter((item) => item.id !== client.id))
      setNotice(`${fullName(client)} was deleted.`)
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Could not delete the client')
    }
  }

  return (
    <>
      <PageHeader
        title="Clients"
        subtitle={`${clients.length} client${clients.length === 1 ? '' : 's'} on file`}
        actions={<Button onClick={() => setEditing('new')}>Add client</Button>}
      />

      {error && <Alert onDismiss={() => setError('')}>{error}</Alert>}
      {notice && (
        <Alert tone="success" onDismiss={() => setNotice('')}>
          {notice}
        </Alert>
      )}

      <Card>
        <div className="border-b border-bark-200 p-4">
          <input
            className="field max-w-sm"
            placeholder="Filter by name, email or phone…"
            value={filter}
            onChange={(event) => setFilter(event.target.value)}
          />
        </div>

        {loading && clients.length === 0 ? (
          <Spinner label="Loading clients…" />
        ) : visible.length === 0 ? (
          <EmptyState
            title={clients.length === 0 ? 'No clients yet' : 'No clients match that filter'}
            hint={clients.length === 0 ? 'Add your first client to get started.' : undefined}
          />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-bark-200 text-left text-xs tracking-wide text-bark-700 uppercase">
                  <th className="px-4 py-3 font-semibold">Name</th>
                  <th className="px-4 py-3 font-semibold">Email</th>
                  <th className="px-4 py-3 font-semibold">Phone</th>
                  <th className="px-4 py-3 text-right font-semibold">Actions</th>
                </tr>
              </thead>
              <tbody>
                {visible.map((client) => (
                  <tr key={client.id} className="border-b border-bark-100 last:border-0">
                    <td className="px-4 py-3 font-medium text-bark-900">{fullName(client)}</td>
                    <td className="px-4 py-3 text-bark-700">
                      <a className="hover:text-leaf-700" href={`mailto:${client.email}`}>
                        {client.email}
                      </a>
                    </td>
                    <td className="px-4 py-3 text-bark-700">
                      <a
                        className="hover:text-leaf-700"
                        href={whatsappLink(client.phone_number)}
                        target="_blank"
                        rel="noreferrer"
                        title="Open WhatsApp"
                      >
                        {displayPhone(client.phone_number)}
                      </a>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex justify-end gap-1">
                        <Button variant="ghost" onClick={() => setEditing(client)}>
                          Edit
                        </Button>
                        <Button variant="ghost" onClick={() => setConfirming(client)}>
                          Delete
                        </Button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {hasMore && !filter && (
          <div className="border-t border-bark-200 p-4 text-center">
            <Button variant="secondary" disabled={loading} onClick={() => void load(clients.length)}>
              {loading ? 'Loading…' : 'Load more'}
            </Button>
          </div>
        )}
      </Card>

      {editing && (
        <ClientForm
          client={editing === 'new' ? null : editing}
          onClose={() => setEditing(null)}
          onSaved={(saved, isNew) => {
            setClients((previous) =>
              isNew
                ? [...previous, saved]
                : previous.map((item) => (item.id === saved.id ? saved : item)),
            )
            setNotice(`${fullName(saved)} was ${isNew ? 'added' : 'updated'}.`)
            setEditing(null)
          }}
        />
      )}

      {confirming && (
        <Modal title="Delete client" onClose={() => setConfirming(null)}>
          <p className="text-sm text-bark-800">
            Delete <strong>{fullName(confirming)}</strong>? This cannot be undone. Clients
            with existing orders cannot be deleted.
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

function ClientForm({
  client,
  onClose,
  onSaved,
}: {
  client: Client | null
  onClose: () => void
  onSaved: (client: Client, isNew: boolean) => void
}) {
  const isNew = client === null
  const [form, setForm] = useState<ClientInput>(
    client
      ? {
          name: client.name,
          last_name: client.last_name ?? '',
          address: client.address ?? '',
          city: client.city ?? '',
          state: client.state ?? '',
          country: client.country ?? '',
          zipcode: client.zipcode ?? '',
          email: client.email,
          phone_number: displayPhone(client.phone_number),
        }
      : BLANK,
  )
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  const set = (key: keyof ClientInput) => (event: { target: { value: string } }) =>
    setForm((previous) => ({ ...previous, [key]: event.target.value }))

  async function onSubmit(event: FormEvent) {
    event.preventDefault()
    setError('')
    setBusy(true)
    try {
      const payload: ClientInput = {
        ...form,
        phone_number: formatPhoneInput(form.phone_number, form.country),
        last_name: form.last_name?.trim() ? form.last_name.trim() : null,
      }
      const saved = isNew
        ? await api.clients.create(payload)
        : await api.clients.update(client.id, payload)
      onSaved(saved, isNew)
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Could not save the client')
    } finally {
      setBusy(false)
    }
  }

  return (
    <Modal title={isNew ? 'Add client' : `Edit ${fullName(client)}`} onClose={onClose}>
      {error && <Alert onDismiss={() => setError('')}>{error}</Alert>}
      <form onSubmit={onSubmit} className="space-y-4">
        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <label className="label" htmlFor="name">
              First name
            </label>
            <input id="name" className="field" required value={form.name} onChange={set('name')} />
          </div>
          <div>
            <label className="label" htmlFor="last_name">
              Last name
            </label>
            <input
              id="last_name"
              className="field"
              value={form.last_name ?? ''}
              onChange={set('last_name')}
            />
          </div>
        </div>
        <div>
          <label className="label" htmlFor="email">
            Email
          </label>
          <input
            id="email"
            type="email"
            className="field"
            required
            value={form.email}
            onChange={set('email')}
          />
        </div>
        <div className="grid gap-4 sm:grid-cols-2">
          <ClientContactFields
            prefix="client"
            value={form}
            required={isNew}
            onChange={(change) => setForm((previous) => ({ ...previous, ...change }))}
          />
        </div>
        {isNew && (
          <div>
            <label className="label" htmlFor="password">
              Password
            </label>
            <input
              id="password"
              type="password"
              className="field"
              required
              minLength={8}
              value={form.password ?? ''}
              onChange={set('password')}
            />
            <p className="mt-1 text-xs text-bark-700">
              At least 8 characters. Stored hashed; needed for the client account.
            </p>
          </div>
        )}
        <div className="flex justify-end gap-2 pt-2">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" disabled={busy}>
            {busy ? 'Saving…' : isNew ? 'Add client' : 'Save changes'}
          </Button>
        </div>
      </form>
    </Modal>
  )
}
