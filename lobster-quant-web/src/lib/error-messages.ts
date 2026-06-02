/**
 * Unified error classification and messages for Lobster Quant.
 * Supports both English and Chinese.
 */

export type ErrorCategory = 
  | 'network'    // Network connection issues
  | 'auth'       // Authentication/Permission issues
  | 'api'        // Backend API errors
  | 'validation' // Form or input validation errors
  | 'market'     // Market data specific errors
  | 'timeout'    // Request timeouts
  | 'unknown'    // Generic fallback

export interface ErrorMessage {
  title: {
    en: string
    zh: string
  }
  message: {
    en: string
    zh: string
  }
  action?: {
    en: string
    zh: string
  }
}

export const ERROR_MESSAGES: Record<ErrorCategory, ErrorMessage> = {
  network: {
    title: {
      en: 'Network Connection Error',
      zh: '网络连接错误'
    },
    message: {
      en: 'Please check your internet connection and try again.',
      zh: '请检查您的网络连接并重试。'
    },
    action: {
      en: 'Check Connection',
      zh: '检查连接'
    }
  },
  auth: {
    title: {
      en: 'Authentication Required',
      zh: '需要身份验证'
    },
    message: {
      en: 'Your session has expired or you do not have permission to access this resource.',
      zh: '您的会话已过期，或者您没有权限访问此资源。'
    },
    action: {
      en: 'Sign In',
      zh: '登录'
    }
  },
  api: {
    title: {
      en: 'Server Error',
      zh: '服务器错误'
    },
    message: {
      en: 'The server encountered an unexpected condition. Our team has been notified.',
      zh: '服务器遇到意外情况。我们的团队已收到通知。'
    },
    action: {
      en: 'Retry Request',
      zh: '重试请求'
    }
  },
  validation: {
    title: {
      en: 'Invalid Data',
      zh: '无效数据'
    },
    message: {
      en: 'The provided data is invalid or incomplete. Please check your input.',
      zh: '提供的数据无效或不完整。请检查您的输入。'
    }
  },
  market: {
    title: {
      en: 'Market Data Unavailable',
      zh: '行情数据不可用'
    },
    message: {
      en: 'Real-time market data is currently unavailable for this symbol. Please try again during market hours.',
      zh: '该交易对的实时行情数据目前不可用。请在开盘时间内重试。'
    },
    action: {
      en: 'Refresh Data',
      zh: '刷新数据'
    }
  },
  timeout: {
    title: {
      en: 'Request Timeout',
      zh: '请求超时'
    },
    message: {
      en: 'The request took too long to complete. The server might be busy.',
      zh: '请求处理时间过长。服务器可能正忙。'
    },
    action: {
      en: 'Try Again',
      zh: '重试'
    }
  },
  unknown: {
    title: {
      en: 'Something Went Wrong',
      zh: '出错了'
    },
    message: {
      en: 'An unexpected error occurred. Please try again later.',
      zh: '发生了意外错误。请稍后重试。'
    }
  }
}

/**
 * Maps common error patterns/codes to ErrorCategory
 */
export function categorizeError(error: any): ErrorCategory {
  if (!error) return 'unknown'
  
  const message = (error.message || '').toLowerCase()
  const code = error.code || error.status

  if (message.includes('network') || message.includes('fetch') || message.includes('failed to fetch')) {
    return 'network'
  }
  
  if (code === 401 || code === 403 || message.includes('unauthorized') || message.includes('forbidden')) {
    return 'auth'
  }
  
  if (message.includes('timeout') || code === 504 || code === 408) {
    return 'timeout'
  }
  
  if (code === 400 || code === 422 || message.includes('invalid') || message.includes('validation')) {
    return 'validation'
  }
  
  if (message.includes('market') || message.includes('ticker') || message.includes('price')) {
    return 'market'
  }
  
  if (code >= 500) {
    return 'api'
  }
  
  return 'unknown'
}
