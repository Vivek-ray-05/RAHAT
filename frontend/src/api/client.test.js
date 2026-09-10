import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'

import { api, setToken } from './client'

describe('api client', () => {
  beforeEach(() => {
    sessionStorage.clear()
    global.fetch = vi.fn()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('setToken stores and clears the token in sessionStorage', () => {
    setToken('abc123')
    expect(sessionStorage.getItem('rahat_token')).toBe('abc123')

    setToken(null)
    expect(sessionStorage.getItem('rahat_token')).toBeNull()
  })

  it('attaches an Authorization header when a token is present', async () => {
    setToken('mytoken')
    fetch.mockResolvedValue({ ok: true, status: 200, json: async () => ({ hello: 'world' }) })

    await api.get('/zones')

    const [, options] = fetch.mock.calls[0]
    expect(options.headers.Authorization).toBe('Bearer mytoken')
  })

  it('omits the Authorization header when there is no token', async () => {
    fetch.mockResolvedValue({ ok: true, status: 200, json: async () => ([]) })

    await api.get('/zones')

    const [, options] = fetch.mock.calls[0]
    expect(options.headers.Authorization).toBeUndefined()
  })

  it('sends a JSON body and method on post', async () => {
    fetch.mockResolvedValue({ ok: true, status: 200, json: async () => ({}) })

    await api.post('/citizen-reports', { zone_id: 3, description: 'flooding' })

    const [url, options] = fetch.mock.calls[0]
    expect(url).toContain('/citizen-reports')
    expect(options.method).toBe('POST')
    expect(JSON.parse(options.body)).toEqual({ zone_id: 3, description: 'flooding' })
  })

  it('throws an Error carrying the response status and detail on failure', async () => {
    fetch.mockResolvedValue({
      ok: false,
      status: 403,
      statusText: 'Forbidden',
      json: async () => ({ detail: 'This recommendation belongs to a different zone.' }),
    })

    await expect(api.get('/recommendations/1')).rejects.toMatchObject({
      status: 403,
      message: 'This recommendation belongs to a different zone.',
    })
  })

  it('falls back to statusText when the error body is not JSON', async () => {
    fetch.mockResolvedValue({
      ok: false,
      status: 500,
      statusText: 'Internal Server Error',
      json: async () => {
        throw new Error('not json')
      },
    })

    await expect(api.get('/zones')).rejects.toMatchObject({ status: 500, message: 'Internal Server Error' })
  })

  it('returns null for a 204 response instead of parsing a body', async () => {
    fetch.mockResolvedValue({ ok: true, status: 204, json: async () => { throw new Error('should not be called') } })

    const result = await api.post('/recommendations/1/approve')

    expect(result).toBeNull()
  })
})
