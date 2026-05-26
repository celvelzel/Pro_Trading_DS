/**
 * Lobster Quant - API Client
 * Centralized API client for communicating with the FastAPI backend.
 */

import { API_BASE_URL } from './constants'
import type { ApiError } from './types'

// ============================================================================
// Status Code Messages
// ============================================================================

/**
 * User-friendly error messages for common HTTP status codes.
 */
const STATUS_MESSAGES: Record<number, string> = {
  400: 'Invalid request',
  401: 'Unauthorized',
  403: 'Access denied',
  404: 'Resource not found',
  429: 'Rate limited. Please try again later.',
  500: 'Server error. Please try again later.',
  503: 'Service unavailable',
}

// ============================================================================
// API Client Class
// ============================================================================

class ApiClient {
  private baseUrl: string

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl
  }

  /**
   * Build a structured ApiError from a failed response.
   * Attempts to parse the response body for a server-provided message,
   * falling back to user-friendly messages for common status codes.
   */
  private async buildError(response: Response): Promise<ApiError> {
    let detail: string | undefined

    // Try to extract a message from the response body
    try {
      const body = await response.json()
      if (typeof body === 'object' && body !== null) {
        const raw =
          (body as Record<string, unknown>).detail ??
          (body as Record<string, unknown>).message ??
          (body as Record<string, unknown>).error
        if (typeof raw === 'string') {
          detail = raw
        }
      }
    } catch {
      // Response body is not JSON or empty — ignore
    }

    if (!detail) {
      detail =
        STATUS_MESSAGES[response.status] ??
        `API error: ${response.status} ${response.statusText}`
    }

    return { detail, status: response.status }
  }

  /**
   * Make a GET request to the API.
   */
  async get<T>(path: string): Promise<T> {
    const url = `${this.baseUrl}${path}`
    
    const response = await fetch(url, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    })

    if (!response.ok) {
      throw await this.buildError(response)
    }

    return response.json()
  }

  /**
   * Make a POST request to the API.
   */
  async post<T>(path: string, body: unknown): Promise<T> {
    const url = `${this.baseUrl}${path}`
    
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body),
    })

    if (!response.ok) {
      throw await this.buildError(response)
    }

    return response.json()
  }

  /**
   * Make a PUT request to the API.
   */
  async put<T>(path: string, body: unknown): Promise<T> {
    const url = `${this.baseUrl}${path}`
    
    const response = await fetch(url, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body),
    })

    if (!response.ok) {
      throw await this.buildError(response)
    }

    return response.json()
  }

  /**
   * Make a DELETE request to the API.
   */
  async delete<T>(path: string): Promise<T> {
    const url = `${this.baseUrl}${path}`
    
    const response = await fetch(url, {
      method: 'DELETE',
      headers: {
        'Content-Type': 'application/json',
      },
    })

    if (!response.ok) {
      throw await this.buildError(response)
    }

    return response.json()
  }
}

// ============================================================================
// Singleton Instance
// ============================================================================

export const api = new ApiClient(API_BASE_URL)
