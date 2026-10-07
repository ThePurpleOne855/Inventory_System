import { Navigate, Route, Routes } from 'react-router-dom'

import Layout from './components/Layout'
import { Spinner } from './components/ui'
import { useAuth } from './lib/auth'
import Clients from './pages/Clients'
import Login from './pages/Login'
import Messages from './pages/Messages'
import Orders from './pages/Orders'
import Products from './pages/Products'

export default function App() {
  const { username, ready } = useAuth()

  if (!ready) return <Spinner label="Checking your session…" />
  if (!username) return <Login />

  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<Navigate to="/clients" replace />} />
        <Route path="/clients" element={<Clients />} />
        <Route path="/inventory" element={<Products />} />
        <Route path="/orders" element={<Orders />} />
        <Route path="/messages" element={<Messages />} />
        <Route path="*" element={<Navigate to="/clients" replace />} />
      </Route>
    </Routes>
  )
}
