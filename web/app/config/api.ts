/**
 * API配置管理
 */

// 默认API配置
const DEFAULT_API_PORT = 5001
const DEFAULT_API_HOST = '127.0.0.1'

/**
 * 获取API基础URL
 */
export const getApiBaseUrl = (): string => {
  // 优先使用环境变量
  if (process.env.NEXT_PUBLIC_API_BASE_URL) {
    return process.env.NEXT_PUBLIC_API_BASE_URL
  }
  
  // 浏览器环境下动态获取
  if (typeof window !== 'undefined') {
    const currentHost = window.location.hostname
    const currentPort = parseInt(window.location.port) || 3000
    
    // 智能端口推断：前端3000 → 后端5001，前端3001 → 后端5002
    const apiPort = currentPort === 3000 ? 5001 : 5001 + currentPort - 3000
    
    const apiUrl = `${window.location.protocol}//${currentHost}:${apiPort}`
    console.log('🔗 API基础URL:', apiUrl)
    return apiUrl
  }
  
  // 服务端渲染或默认情况
  return `http://${DEFAULT_API_HOST}:${DEFAULT_API_PORT}`
}

/**
 * API端点配置
 */
export const API_ENDPOINTS = {
  STATUS: '/api/status',
  LOAD_MODEL: '/api/load_model',
  DETECT_IMAGE: '/api/detect_image',
  TRAINING: '/api/start_training',
  ROBOT_ARM_GRAB: '/api/robot_arm/grab',
  ROBOT_ARM_STATUS: '/api/robot_arm/status',
  ROBOT_ARM_HOME: '/api/robot_arm/home',
  ROBOT_ARM_EMERGENCY_STOP: '/api/robot_arm/emergency_stop',
  ROBOT_ARM_STATISTICS: '/api/robot_arm/statistics',
  ROBOT_ARM_RESET_STATS: '/api/robot_arm/reset_stats',
  ROBOT_ARM_TEST_SORT: '/api/robot_arm/test_sort',
  ROBOT_ARM_TYPES: '/api/robot_arm/types',
  ROBOT_ARM_CURRENT_CONFIG: '/api/robot_arm/current_config',
  ROBOT_ARM_SWITCH_TYPE: '/api/robot_arm/switch_type',
  ROBOT_ARM_CONNECT: '/api/robot_arm/connect',
  ROBOT_ARM_DISCONNECT: '/api/robot_arm/disconnect'
} as const

/**
 * 获取完整的API URL
 */
export const getApiUrl = (endpoint: string): string => {
  const baseUrl = getApiBaseUrl()
  return `${baseUrl}${endpoint}`
}

/**
 * API客户端配置
 */
export const API_CONFIG = {
  timeout: 30000,  // 30秒超时
  retries: 3,      // 重试3次
  retryDelay: 1000 // 重试间隔1秒
} 