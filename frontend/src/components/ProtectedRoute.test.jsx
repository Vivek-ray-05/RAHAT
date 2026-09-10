import { render, screen } from '@testing-library/react'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import { describe, it, expect, vi } from 'vitest'

import ProtectedRoute from './ProtectedRoute'
import { useAuth } from '../context/AuthContext'

vi.mock('../context/AuthContext', () => ({ useAuth: vi.fn() }))

function renderProtected(roles) {
  return render(
    <MemoryRouter initialEntries={['/dashboard']}>
      <Routes>
        <Route
          path="/dashboard"
          element={
            <ProtectedRoute roles={roles}>
              <div>SECRET_CONTENT</div>
            </ProtectedRoute>
          }
        />
        <Route path="/login" element={<div>LOGIN_PAGE</div>} />
      </Routes>
    </MemoryRouter>
  )
}

describe('ProtectedRoute', () => {
  it('redirects to /login when there is no user', () => {
    useAuth.mockReturnValue({ user: null })

    renderProtected(['central_coordinator'])

    expect(screen.getByText('LOGIN_PAGE')).toBeInTheDocument()
    expect(screen.queryByText('SECRET_CONTENT')).not.toBeInTheDocument()
  })

  it('redirects to /login when the user role is not in the allowed list', () => {
    useAuth.mockReturnValue({ user: { id: 1, role: 'citizen' } })

    renderProtected(['central_coordinator', 'zone_admin'])

    expect(screen.getByText('LOGIN_PAGE')).toBeInTheDocument()
  })

  it('renders children when the user role is allowed', () => {
    useAuth.mockReturnValue({ user: { id: 1, role: 'zone_admin' } })

    renderProtected(['central_coordinator', 'zone_admin'])

    expect(screen.getByText('SECRET_CONTENT')).toBeInTheDocument()
  })

  it('renders children when no roles restriction is given, as long as a user exists', () => {
    useAuth.mockReturnValue({ user: { id: 1, role: 'citizen' } })

    renderProtected(undefined)

    expect(screen.getByText('SECRET_CONTENT')).toBeInTheDocument()
  })
})
