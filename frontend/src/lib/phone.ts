import { parsePhoneNumberFromString, isSupportedCountry, type CountryCode } from 'libphonenumber-js'

export function formatPhoneInput(value: string, country?: string | null): string {
  const region: CountryCode | undefined = country && isSupportedCountry(country) ? country : undefined
  const raw = value.replace(/^tel:/, '').trim()
  const parsed = parsePhoneNumberFromString(raw, { defaultCountry: region, extract: false })
  return parsed?.isPossible() ? parsed.formatInternational() : raw
}
