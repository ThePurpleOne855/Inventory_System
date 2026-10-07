import { getCountries } from 'libphonenumber-js'
import type { ClientInput } from '../lib/types'
import { formatPhoneInput } from '../lib/phone'

const countryNames = new Intl.DisplayNames(['en'], { type: 'region' })
const countries = getCountries().map((code) => ({ code, name: countryNames.of(code) ?? code }))
  .sort((a, b) => a.name.localeCompare(b.name))

export function ClientContactFields({ value, onChange, required, prefix }: {
  value: ClientInput
  onChange: (change: Partial<ClientInput>) => void
  required: boolean
  prefix: string
}) {
  const fields = [
    { key: 'address', label: 'Address', autocomplete: 'address-line1' },
    { key: 'city', label: 'City', autocomplete: 'address-level2' },
    { key: 'state', label: 'State / Province', autocomplete: 'address-level1' },
    { key: 'zipcode', label: 'ZIP / Postal code', autocomplete: 'postal-code' },
  ] as const
  return (
    <>
      <div>
        <label className="label" htmlFor={`${prefix}-phone`}>Phone number</label>
        <input
          id={`${prefix}-phone`} className="field" type="tel" autoComplete="tel"
          required placeholder="+1 415 555 2671" value={value.phone_number}
          onChange={(event) => onChange({ phone_number: event.target.value })}
          onBlur={() => onChange({ phone_number: formatPhoneInput(value.phone_number, value.country) })}
        />
        <p className="mt-1 text-xs text-bark-700">
          Formats automatically when you leave the field. Include +country code or select your country below.
        </p>
      </div>
      {fields.map(({ key, label, autocomplete }) => (
        <div key={key} className={key === 'address' ? 'sm:col-span-2' : undefined}>
          <label className="label" htmlFor={`${prefix}-${key}`}>{label}</label>
          <input
            id={`${prefix}-${key}`} className="field" required={required}
            autoComplete={autocomplete} value={value[key] ?? ''}
            onChange={(event) => onChange({ [key]: event.target.value })}
          />
        </div>
      ))}
      <div>
        <label className="label" htmlFor={`${prefix}-country`}>Country</label>
        <select
          id={`${prefix}-country`} className="field" autoComplete="country"
          required={required} value={value.country ?? ''}
          onChange={(event) => onChange({
            country: event.target.value,
            phone_number: formatPhoneInput(value.phone_number, event.target.value),
          })}
        >
          <option value="">Select country</option>
          {countries.map(({ code, name }) => <option key={code} value={code}>{name}</option>)}
        </select>
      </div>
    </>
  )
}
