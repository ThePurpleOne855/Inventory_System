import { NavLink, Outlet } from 'react-router-dom'

import { useAuth } from '../lib/auth'
import { Button } from './ui'

const NAV = [
  { to: '/clients', label: 'Clients', hint: 'Everyone you sell to' },
  { to: '/inventory', label: 'Inventory', hint: 'Products and stock' },
  { to: '/orders', label: 'Orders', hint: 'Orders and invoices' },
  { to: '/messages', label: 'Messages', hint: 'Email and WhatsApp' },
]

export default function Layout() {
  const { username, logout } = useAuth()

  return (
    <div className="flex min-h-full flex-col md:flex-row">
      <aside className="shrink-0 border-b border-bark-200 bg-white md:w-64 md:border-r md:border-b-0">
        <div className="flex items-center gap-3 px-5 py-5">
          <span className="grid size-9 place-items-center rounded-lg bg-leaf-600 text-base font-bold text-white">
            MT
          </span>
          <div className="leading-tight">
            <p className="text-sm font-semibold text-bark-900">Madre Tierra</p>
            <p className="text-xs text-bark-700">Inventory</p>
          </div>
        </div>

        <nav className="flex gap-1 overflow-x-auto px-3 pb-3 md:flex-col md:overflow-visible">
          {NAV.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                `rounded-lg px-3 py-2 text-sm font-medium whitespace-nowrap transition-colors ${
                  isActive
                    ? 'bg-leaf-50 text-leaf-700'
                    : 'text-bark-700 hover:bg-bark-100 hover:text-bark-900'
                }`
              }
            >
              <span className="block">{item.label}</span>
              <span className="hidden text-xs font-normal text-bark-700/70 md:block">
                {item.hint}
              </span>
            </NavLink>
          ))}
        </nav>

        <div className="mt-auto hidden border-t border-bark-200 px-5 py-4 md:block">
          <p className="text-xs text-bark-700">Signed in as</p>
          <p className="mb-3 truncate text-sm font-medium text-bark-900">{username}</p>
          <Button variant="secondary" className="w-full" onClick={() => void logout()}>
            Sign out
          </Button>
        </div>
      </aside>

      <main className="flex-1 px-4 py-6 sm:px-8 sm:py-10">
        <div className="mx-auto max-w-6xl">
          <Outlet />
        </div>
        <div className="mx-auto mt-10 max-w-6xl md:hidden">
          <Button variant="secondary" onClick={() => void logout()}>
            Sign out ({username})
          </Button>
        </div>
      </main>
    </div>
  )
}
