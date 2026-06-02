/**
 * Integration tests for the API client.
 * Tests error handling and response parsing with mocked fetch.
 */
import { describe, it, expect, beforeEach, vi } from 'vitest'

// Mock the constants module to control API_BASE_URL
vi.mock('@/lib/constants', () => ({
  API_BASE_URL: 'http://localhost:8000',
}))

// We need to mock fetch before importing the API client
const mockFetch = vi.fn()
vi.stubGlobal('fetch', mockFetch)

// Import after mocking
const { api } = await import('@/lib/api')

describe('ApiClient integration', () => {
  beforeEach(() => {
    mockFetch.mockReset()
  })

  // ─── GET requests ────────────────────────────────────────────

  describe('GET requests', () => {
    it('makes GET request to correct URL', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ data: 'test' }),
      })

      const result = await api.get('/test')

      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8000/test',
        expect.objectContaining({
          method: 'GET',
          headers: { 'Content-Type': 'application/json' },
        })
      )
      expect(result).toEqual({ data: 'test' })
    })

    it('throws ApiError on non-ok response', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 404,
        statusText: 'Not Found',
        json: () => Promise.resolve({ detail: 'Resource not found' }),
      })

      await expect(api.get('/missing')).rejects.toMatchObject({
        detail: 'Resource not found',
        status: 404,
      })
    })

    it('uses fallback message when response body is not JSON', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        statusText: 'Internal Server Error',
        json: () => Promise.reject(new Error('Not JSON')),
      })

      await expect(api.get('/error')).rejects.toMatchObject({
        detail: 'Server error. Please try again later.',
        status: 500,
      })
    })
  })

  // ─── POST requests ───────────────────────────────────────────

  describe('POST requests', () => {
    it('makes POST request with body', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ id: 1 }),
      })

      const body = { symbol: 'AAPL', market: 'US' }
      await api.post('/scan', body)

      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8000/scan',
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify(body),
        })
      )
    })

    it('throws on POST error with status message', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 429,
        statusText: 'Too Many Requests',
        json: () => Promise.resolve({}),
      })

      await expect(api.post('/scan', {})).rejects.toMatchObject({
        detail: 'Rate limited. Please try again later.',
        status: 429,
      })
    })
  })

  // ─── PUT requests ────────────────────────────────────────────

  describe('PUT requests', () => {
    it('makes PUT request with body', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ updated: true }),
      })

      await api.put('/settings', { theme: 'dark' })

      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8000/settings',
        expect.objectContaining({
          method: 'PUT',
          body: JSON.stringify({ theme: 'dark' }),
        })
      )
    })
  })

  // ─── DELETE requests ─────────────────────────────────────────

  describe('DELETE requests', () => {
    it('makes DELETE request', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ deleted: true }),
      })

      await api.delete('/items/1')

      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8000/items/1',
        expect.objectContaining({
          method: 'DELETE',
        })
      )
    })
  })

  // ─── Error message extraction ────────────────────────────────

  describe('error message extraction', () => {
    it('extracts detail from response body', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 400,
        json: () => Promise.resolve({ detail: 'Custom error detail' }),
      })

      await expect(api.get('/bad')).rejects.toMatchObject({
        detail: 'Custom error detail',
      })
    })

    it('extracts message field from response body', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 400,
        json: () => Promise.resolve({ message: 'Alt error message' }),
      })

      await expect(api.get('/bad')).rejects.toMatchObject({
        detail: 'Alt error message',
      })
    })

    it('extracts error field from response body', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 400,
        json: () => Promise.resolve({ error: 'Error field message' }),
      })

      await expect(api.get('/bad')).rejects.toMatchObject({
        detail: 'Error field message',
      })
    })

    it('falls back to status code message for 401', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 401,
        statusText: 'Unauthorized',
        json: () => Promise.resolve({}),
      })

      await expect(api.get('/protected')).rejects.toMatchObject({
        detail: 'Unauthorized',
        status: 401,
      })
    })
  })
})
