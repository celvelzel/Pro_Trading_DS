/**
 * Lobster Quant - API Client
 * Centralized API client for communicating with the FastAPI backend.
 */

import { API_BASE_URL } from './constants'
import type { ApiError } from './types'

// ============================================================================
// API Client Class
// ============================================================================

class ApiClient {
  private baseUrl: string

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl
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
      const error: ApiError = {
        detail: `API error: ${response.status} ${response.statusText}`,
        status: response.status,
      }
      throw error
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
      const error: ApiError = {
        detail: `API error: ${response.status} ${response.statusText}`,
        status: response.status,
      }
      throw error
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
      const error: ApiError = {
        detail: `API error: ${response.status} ${response.statusText}`,
        status: response.status,
      }
      throw error
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
      const error: ApiError = {
        detail: `API error: ${response.status} ${response.statusText}`,
        status: response.status,
      }
      throw error
    }

    return response.json()
  }
}

// ============================================================================
// Singleton Instance
// ============================================================================

export const api = new ApiClient(API_BASE_URL)

// ============================================================================
// Convenience Functions
// ============================================================================

/**
 * Fetch stock data for a given symbol.
 */
export async function fetchStockData(symbol: string) {
  return api.get(`/api/stocks/${symbol}`)
}

/**
 * Fetch technical indicators for a given symbol.
 */
export async function fetchIndicators(symbol: string) {
  return api.get(`/api/stocks/${symbol}/indicators`)
}

/**
 * Fetch trading signals for a given symbol.
 */
export async function fetchSignals(symbol: string) {
  return api.get(`/api/stocks/${symbol}/signals`)
}

/**
 * Fetch options analysis for a given symbol.
 */
export async function fetchOptionsAnalysis(symbol: string) {
  return api.get(`/api/stocks/${symbol}/options`)
}

/**
 * Fetch risk assessment for a given symbol.
 */
export async function fetchRiskAssessment(symbol: string) {
  return api.get(`/api/stocks/${symbol}/risk`)
}

/**
 * Scan stocks based on market and minimum score.
 */
export async function scanStocks(market: string, minScore: number) {
  return api.post('/api/scanner/scan', { market, minScore })
}

/**
 * Run a strategy backtest.
 */
export async function runBacktest(params: {
  symbol: string
  holdingDays: number
  minScore: number
  startDate?: string
  endDate?: string
}) {
  return api.post('/api/backtest/run', params)
}
