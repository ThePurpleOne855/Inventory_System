import type { Client, Money } from './types'

/** pydantic's PhoneNumber serialises as "tel:+1-555-0100"; the scheme is noise here. */
export const displayPhone = (value: string | null | undefined): string =>
  (value ?? '').replace(/^tel:/, '')

/** Digits only, as wa.me requires. */
export const whatsappNumber = (value: string | null | undefined): string =>
  displayPhone(value).replace(/\D/g, '')

export const whatsappLink = (phone: string, message = ''): string => {
  const number = whatsappNumber(phone)
  const text = message ? `?text=${encodeURIComponent(message)}` : ''
  return `https://wa.me/${number}${text}`
}

export const fullName = (client: Pick<Client, 'name' | 'last_name'>): string =>
  [client.name, client.last_name].filter(Boolean).join(' ')

export const money = (value: Money | number, currency = '$'): string =>
  `${currency}${Number(value).toLocaleString(undefined, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`

export const shortDate = (iso: string): string =>
  new Date(iso).toLocaleDateString(undefined, {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
  })

export const dateTime = (iso: string): string =>
  new Date(iso).toLocaleString(undefined, {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })

/** Replace the same tokens the backend's personalize() understands. */
export const personalize = (template: string, client: Client): string =>
  template
    .replaceAll('{name}', client.name ?? '')
    .replaceAll('{last_name}', client.last_name ?? '')
    .replaceAll('{full_name}', fullName(client))
