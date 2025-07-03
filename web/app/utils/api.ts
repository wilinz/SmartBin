/**
 * API请求工具
 * 统一处理HTTP请求和错误响应，避免控制台错误
 */

import { getApiUrl } from '../config/api'

// API响应类型
export interface ApiResponse<T = any> {
  success: boolean
  data?: T
  error?: string
  status: number
  isBusinessError?: boolean // 标识是否为业务错误（如409冲突）
}

// 业务错误状态码（不应该在控制台报红色错误）
const BUSINESS_ERROR_CODES = [409, 400, 404, 422]

/**
 * 统一的API请求函数
 * 优雅处理HTTP错误状态码，避免控制台报错
 */
export async function apiRequest<T = any>(
  endpoint: string,
  options: RequestInit = {}
): Promise<ApiResponse<T>> {
  try {
    const url = getApiUrl(endpoint)
    
    // 设置默认headers
    const defaultHeaders: HeadersInit = {
      'Content-Type': 'application/json',
    }
    
    // 如果body是FormData，移除Content-Type让浏览器自动设置
    if (options.body instanceof FormData) {
      delete defaultHeaders['Content-Type']
    }
    
    const response = await fetch(url, {
      ...options,
      headers: {
        ...defaultHeaders,
        ...options.headers,
      },
    })
    
    const status = response.status
    const isBusinessError = BUSINESS_ERROR_CODES.includes(status)
    
    // 尝试解析响应体
    let responseData: any
    try {
      const text = await response.text()
      responseData = text ? JSON.parse(text) : {}
    } catch {
      responseData = {}
    }
    
    if (response.ok) {
      return {
        success: true,
        data: responseData,
        status,
      }
    } else {
      // 对于业务错误，不作为异常处理
      if (isBusinessError) {
        return {
          success: false,
          error: responseData.error || responseData.message || `请求失败 (${status})`,
          status,
          isBusinessError: true,
          data: responseData, // 有时错误响应也包含有用信息
        }
      } else {
        // 真正的网络错误或服务器错误
        console.warn(`HTTP Error ${status}:`, responseData)
        return {
          success: false,
          error: responseData.error || responseData.message || `服务器错误 (${status})`,
          status,
          isBusinessError: false,
        }
      }
    }
  } catch (error) {
    // 网络错误或其他异常
    console.error('API请求异常:', error)
    return {
      success: false,
      error: error instanceof Error ? error.message : '网络连接失败',
      status: 0,
      isBusinessError: false,
    }
  }
}

/**
 * GET请求
 */
export async function apiGet<T = any>(endpoint: string): Promise<ApiResponse<T>> {
  return apiRequest<T>(endpoint, { method: 'GET' })
}

/**
 * POST请求
 */
export async function apiPost<T = any>(
  endpoint: string,
  data?: any,
  isFormData = false
): Promise<ApiResponse<T>> {
  const options: RequestInit = { method: 'POST' }
  
  if (data) {
    if (isFormData || data instanceof FormData) {
      options.body = data instanceof FormData ? data : data
    } else {
      options.body = JSON.stringify(data)
    }
  }
  
  return apiRequest<T>(endpoint, options)
}

/**
 * 处理机械臂抓取请求（专门处理409状态）
 */
export async function robotArmGrab(target: any): Promise<{
  success: boolean
  message: string
  isBusy?: boolean
  currentStatus?: string
}> {
  const response = await apiPost('/api/robot_arm/grab', { target })
  
  if (response.success) {
    return {
      success: true,
      message: '机械臂操作成功',
    }
  } else if (response.status === 409) {
    // 机械臂忙碌不是错误，是正常的业务状态
    return {
      success: false,
      message: response.error || '机械臂正忙',
      isBusy: true,
      currentStatus: response.data?.current_status,
    }
  } else {
    return {
      success: false,
      message: response.error || '机械臂操作失败',
      isBusy: false,
    }
  }
}

/**
 * 静默处理请求（完全不显示错误，适用于轮询等场景）
 */
export async function apiRequestSilent<T = any>(
  endpoint: string,
  options: RequestInit = {}
): Promise<ApiResponse<T>> {
  try {
    const response = await apiRequest<T>(endpoint, options)
    // 即使失败也不在控制台显示任何信息
    return response
  } catch (error) {
    return {
      success: false,
      error: 'Request failed silently',
      status: 0,
      isBusinessError: false,
    }
  }
}

/**
 * 批量请求处理
 */
export async function apiBatch<T = any>(
  requests: Array<{ endpoint: string; options?: RequestInit }>
): Promise<ApiResponse<T>[]> {
  const promises = requests.map(({ endpoint, options }) =>
    apiRequest<T>(endpoint, options)
  )
  
  return Promise.all(promises)
} 