'use client'

import { useState, useEffect, useRef } from 'react'
import Image from 'next/image'
import { getApiUrl, API_ENDPOINTS } from './config/api'
import { robotArmGrab, apiGet, apiPost } from './utils/api'

// 类型定义
interface SystemStatus {
  detector_loaded: boolean
  training_active: boolean
  robot_arm_connected: boolean
  system_ready: boolean
  robot_arm_status?: {
    connected: boolean
    status: string
    current_position: {
      x: number
      y: number
      z: number
    }
    has_object: boolean
    move_speed: number
    grab_force: number
  }
}

interface DetectionResult {
  class: string
  confidence: number
  bbox: [number, number, number, number]
}

interface RobotArmType {
  type: string
  name: string
  description: string
  features: string[]
  config_required: boolean
  config_fields: string[]
  available: boolean
}

interface RobotArmConfig {
  current_type: string
  type_info: {
    name: string
    description: string
    features: string[]
    config_required: boolean
  }
  configuration: {
    max_reach: number
    max_payload: number
    degrees_of_freedom: number
    max_speed: number
    acceleration: number
    precision: number
  }
  status: any
  connection_config: any
}

export default function SmartBinDashboard() {
  const [systemStatus, setSystemStatus] = useState<SystemStatus | null>(null)
  const [selectedImage, setSelectedImage] = useState<File | null>(null)
  const [detectionResult, setDetectionResult] = useState<{
    image: string
    results: DetectionResult[]
  } | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  
  // 实时检测相关状态
  const [isLiveDetecting, setIsLiveDetecting] = useState(false)
  const [stream, setStream] = useState<MediaStream | null>(null)
  const [liveResults, setLiveResults] = useState<DetectionResult[]>([])
  const [detectionInterval, setDetectionInterval] = useState<NodeJS.Timeout | null>(null)
  const [currentDetections, setCurrentDetections] = useState<DetectionResult[]>([])
  
  // 检测参数控制
  const [detectionFps, setDetectionFps] = useState<number>(1) // 每秒检测次数
  const [armTriggerConfidence, setArmTriggerConfidence] = useState<number>(0.7) // 机械臂触发置信度
  
  // 镜头矫正相关状态
  const [calibrationEnabled, setCalibrationEnabled] = useState<boolean>(false)
  const [calibrationParams, setCalibrationParams] = useState<any>(null)
  const [undistortMaps, setUndistortMaps] = useState<any>(null)
  const [correctionQuality, setCorrectionQuality] = useState<number>(1) // 1=高质量, 2=中等, 3=低质量
  
  // 机械臂管理相关状态
  const [robotArmTypes, setRobotArmTypes] = useState<RobotArmType[]>([])
  const [currentArmConfig, setCurrentArmConfig] = useState<RobotArmConfig | null>(null)
  const [showArmManager, setShowArmManager] = useState(false)
  const [switchingArm, setSwitchingArm] = useState(false)
  
  // 使用useRef获取DOM元素
  const videoRef = useRef<HTMLVideoElement>(null)
  const canvasRef = useRef<HTMLCanvasElement>(null)
  
  // 用于避免闭包问题的检测状态引用
  const isLiveDetectingRef = useRef(false)

  // 同步状态到ref
  useEffect(() => {
    isLiveDetectingRef.current = isLiveDetecting
    console.log('🔄 检测状态:', isLiveDetecting)
    
    // 如果状态意外变成false
    if (!isLiveDetecting && stream) {
      console.warn('⚠️ 检测状态为false但摄像头流存在')
    }
  }, [isLiveDetecting, stream])
  
  // 确保视频流在状态更新时保持连接
  useEffect(() => {
    if (stream && videoRef.current && !videoRef.current.srcObject) {
      console.log('🔄 重新连接视频流')
      videoRef.current.srcObject = stream
      videoRef.current.play().catch(e => console.log('视频播放失败:', e))
    }
  }, [stream])

  // 持续将视频帧绘制到Canvas上
  useEffect(() => {
    if (!isLiveDetecting || !videoRef.current || !canvasRef.current) return

    const drawVideoFrame = () => {
      const video = videoRef.current
      const canvas = canvasRef.current
      if (!video || !canvas || video.videoWidth === 0) return

      const ctx = canvas.getContext('2d')
      if (!ctx) return

      // 设置Canvas尺寸
      canvas.width = video.videoWidth
      canvas.height = video.videoHeight

      // 绘制视频帧
      ctx.drawImage(video, 0, 0, canvas.width, canvas.height)
      
      // 应用镜头矫正到预览画面
      if (calibrationEnabled && undistortMaps) {
        applyLensCorrection(canvas, ctx)
      }
      
      // 绘制检测框
      if (currentDetections.length > 0) {
        drawDetections(ctx, currentDetections, canvas.width, canvas.height)
      }
    }

    // 每33ms绘制一次（约30fps）
    const frameInterval = setInterval(drawVideoFrame, 33)

    return () => clearInterval(frameInterval)
  }, [isLiveDetecting, currentDetections, calibrationEnabled, undistortMaps, correctionQuality])

  // 获取系统状态
  const fetchSystemStatus = async () => {
    try {
      const response = await apiGet<SystemStatus>(API_ENDPOINTS.STATUS)
      if (response.success) {
        setSystemStatus(response.data!)
        setError(null)
      } else {
        setError(response.error || '无法获取系统状态')
      }
    } catch (err) {
      setError('连接后端服务失败')
    }
  }

  // 获取机械臂类型列表
  const fetchRobotArmTypes = async () => {
    try {
      const response = await fetch(getApiUrl('/api/robot_arm/types'))
      if (response.ok) {
        const data = await response.json()
        setRobotArmTypes(data.types)
      }
    } catch (err) {
      console.error('获取机械臂类型失败:', err)
    }
  }

  // 获取当前机械臂配置
  const fetchCurrentArmConfig = async () => {
    try {
      const response = await fetch(getApiUrl('/api/robot_arm/current_config'))
      if (response.ok) {
        const data = await response.json()
        setCurrentArmConfig(data)
      }
    } catch (err) {
      console.error('获取机械臂配置失败:', err)
    }
  }

  // 切换机械臂类型
  const switchRobotArmType = async (armType: string, config: any = {}) => {
    setSwitchingArm(true)
    try {
      const response = await fetch(getApiUrl('/api/robot_arm/switch_type'), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          arm_type: armType,
          config: config
        })
      })

      if (response.ok) {
        const result = await response.json()
        await fetchCurrentArmConfig()
        await fetchSystemStatus()
        setError(null)
        alert(`✅ ${result.message}`)
      } else {
        const errorData = await response.json()
        setError(errorData.error || '切换机械臂失败')
      }
    } catch (err) {
      setError('切换机械臂请求失败')
    }
    setSwitchingArm(false)
  }

  // 连接/断开机械臂
  const toggleArmConnection = async (connect: boolean) => {
    try {
      const endpoint = connect ? '/api/robot_arm/connect' : '/api/robot_arm/disconnect'
      const response = await fetch(getApiUrl(endpoint), {
        method: 'POST'
      })

      if (response.ok) {
        await fetchCurrentArmConfig()
        await fetchSystemStatus()
        setError(null)
      } else {
        const errorData = await response.json()
        setError(errorData.error || (connect ? '连接机械臂失败' : '断开机械臂失败'))
      }
    } catch (err) {
      setError('机械臂操作请求失败')
    }
  }

  // 加载模型
  const loadModel = async () => {
    setLoading(true)
    try {
      const response = await fetch(getApiUrl(API_ENDPOINTS.LOAD_MODEL), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          model_path: 'models/best.pt'
        })
      })
      
      if (response.ok) {
        await fetchSystemStatus()
        setError(null)
      } else {
        const errorData = await response.json()
        setError(errorData.error || '模型加载失败')
      }
    } catch (err) {
      setError('模型加载请求失败')
    }
    setLoading(false)
  }

  // 检测图像
  const detectImage = async () => {
    if (!selectedImage) return

    setLoading(true)
    const formData = new FormData()
    formData.append('image', selectedImage)

    try {
      const response = await fetch(getApiUrl(API_ENDPOINTS.DETECT_IMAGE), {
        method: 'POST',
        body: formData
      })

      if (response.ok) {
        const result = await response.json()
        setDetectionResult(result)
        setError(null)
      } else {
        const errorData = await response.json()
        setError(errorData.error || '图像检测失败')
      }
    } catch (err) {
      setError('图像检测请求失败')
    }
    setLoading(false)
  }

  // 启动实时检测
  const startLiveDetection = async () => {
    try {
      // 检查模型是否已加载
      if (!systemStatus?.detector_loaded) {
        setError('请先加载检测模型')
        return
      }

      console.log('🔍 开始获取摄像头权限...')
      
      // 获取摄像头权限
      const mediaStream = await navigator.mediaDevices.getUserMedia({
        video: { width: 640, height: 480 }
      })

      console.log('✅ 摄像头权限获取成功，视频轨道:', mediaStream.getVideoTracks().length)
      
      setStream(mediaStream)
      
      // 设置视频流
      if (videoRef.current) {
        const video = videoRef.current
        video.srcObject = mediaStream
        
        try {
          await video.play()
          console.log('📹 视频播放命令已发送')
        } catch (playError) {
          console.error('❌ 视频播放失败:', playError)
        }
      }

      setIsLiveDetecting(true)
      setError(null)

      // 立即开始检测
      const intervalMs = Math.round(1000 / detectionFps)
      console.log(`🎯 开始AI检测，设置定时器，检测频率: ${detectionFps}FPS，间隔: ${intervalMs}ms`)
      
      const interval = setInterval(() => {
        captureAndDetect()
      }, intervalMs)
      setDetectionInterval(interval)
      
      // 立即执行一次检测
      setTimeout(() => {
        captureAndDetect()
      }, 1000)

    } catch (err) {
      console.error('❌ 摄像头启动失败:', err)
      if (err instanceof Error) {
        if (err.name === 'NotAllowedError') {
          setError('摄像头权限被拒绝，请允许访问摄像头并刷新页面')
        } else if (err.name === 'NotFoundError') {
          setError('未找到摄像头设备')
        } else {
          setError(`摄像头启动失败: ${err.message}`)
        }
      } else {
        setError('无法访问摄像头，请检查权限设置')
      }
    }
  }

  // 停止实时检测
  const stopLiveDetection = () => {
    console.log('🛑 停止实时检测')
    
    setIsLiveDetecting(false)
    setLiveResults([])
    setCurrentDetections([])

    // 停止定期检测
    if (detectionInterval) {
      clearInterval(detectionInterval)
      setDetectionInterval(null)
    }

    // 停止摄像头
    if (stream) {
      stream.getTracks().forEach(track => track.stop())
      setStream(null)
    }

    // 清除视频
    if (videoRef.current) {
      videoRef.current.srcObject = null
    }
  }

  // 触发机械臂抓取
  const triggerRobotArm = async (detection: DetectionResult) => {
    try {
      console.log(`🦾 准备触发机械臂抓取: ${detection.class}`)
      
      const target = {
        class: detection.class,
        confidence: detection.confidence,
        bbox: detection.bbox,
        center: [
          (detection.bbox[0] + detection.bbox[2]) / 2,
          (detection.bbox[1] + detection.bbox[3]) / 2
        ]
      }
      
      const result = await robotArmGrab(target)
      
      if (result.success) {
        console.log('✅ 机械臂指令发送成功')
      } else if (result.isBusy) {
        console.log(`⏳ 机械臂正忙 (${result.currentStatus}): ${result.message}`)
      } else {
        console.warn(`⚠️ 机械臂操作失败: ${result.message}`)
      }
    } catch (err) {
      console.error('❌ 机械臂通信异常:', err)
    }
  }

  // 捕获图像并检测
  const captureAndDetect = async () => {
    if (!videoRef.current || !canvasRef.current || !isLiveDetectingRef.current) {
      return
    }

    try {
      if (videoRef.current.videoWidth === 0 || videoRef.current.videoHeight === 0) {
        return
      }

      const canvas = canvasRef.current
      const context = canvas.getContext('2d')
      if (!context) return

      canvas.width = videoRef.current.videoWidth
      canvas.height = videoRef.current.videoHeight

      context.drawImage(videoRef.current, 0, 0, canvas.width, canvas.height)

      // 应用镜头矫正
      if (calibrationEnabled && undistortMaps) {
        applyLensCorrection(canvas, context)
      }

      canvas.toBlob(async (blob: Blob | null) => {
        if (!blob) return

        const formData = new FormData()
        formData.append('image', blob, 'capture.jpg')

        try {
          const apiUrl = getApiUrl(API_ENDPOINTS.DETECT_IMAGE)
          
          const response = await fetch(apiUrl, {
            method: 'POST',
            body: formData
          })

          if (response.ok) {
            const result = await response.json()
            const detections = result.results || []
            
            const highConfidenceDetections = detections.filter(
              (detection: DetectionResult) => detection.confidence >= armTriggerConfidence
            )
            
            if (highConfidenceDetections.length > 0) {
              triggerRobotArm(highConfidenceDetections[0])
            }
            
            setCurrentDetections(detections)
            setLiveResults(detections)
          }
        } catch (err) {
          console.error('❌ 检测请求异常:', err)
        }
      }, 'image/jpeg', 0.8)

    } catch (err) {
      console.error('❌ 捕获失败:', err)
    }
  }

  // 在画布上绘制检测框
  const drawDetections = (ctx: CanvasRenderingContext2D, detections: DetectionResult[], canvasWidth: number, canvasHeight: number) => {
    detections.forEach((detection, index) => {
      const [x1, y1, x2, y2] = detection.bbox
      const originalW = x2 - x1
      const originalH = y2 - y1
      
      const rectX = x1
      const rectY = y1
      const rectW = originalW
      const rectH = originalH
      
      // 绘制检测框
      ctx.strokeStyle = '#00ff00'
      ctx.lineWidth = 3
      ctx.strokeRect(rectX, rectY, rectW, rectH)
      
      // 绘制标签背景
      const label = `${detection.class} ${(detection.confidence * 100).toFixed(1)}%`
      ctx.font = '16px Arial'
      const textWidth = ctx.measureText(label).width
      
      ctx.fillStyle = 'rgba(0, 255, 0, 0.8)'
      ctx.fillRect(rectX, Math.max(0, rectY - 25), textWidth + 10, 25)
      
      // 绘制标签文字
      ctx.fillStyle = '#000'
      ctx.fillText(label, rectX + 5, Math.max(15, rectY - 5))
    })
  }

  // 机械臂调试功能
  const testRobotArmFunction = async (action: string) => {
    try {
      console.log(`🧪 测试机械臂功能: ${action}`)
      
      let endpoint = ''
      if (action === 'home') {
        endpoint = API_ENDPOINTS.ROBOT_ARM_HOME
      } else if (action === 'emergency_stop') {
        endpoint = API_ENDPOINTS.ROBOT_ARM_EMERGENCY_STOP
      }
      
      const response = await apiPost(endpoint)
      
      if (response.success) {
        console.log(`✅ ${action} 执行成功:`, response.data?.message)
        await fetchSystemStatus()
      } else if (response.isBusinessError) {
        console.warn(`⚠️ ${action} 执行失败:`, response.error)
      } else {
        console.error(`❌ ${action} 执行失败:`, response.error)
      }
    } catch (err) {
      console.error(`❌ ${action} 请求异常:`, err)
    }
  }

  const testRobotArmSort = async (garbageType: string) => {
    try {
      console.log(`🧪 测试垃圾分拣: ${garbageType}`)
      
      const response = await apiPost(`${API_ENDPOINTS.ROBOT_ARM_TEST_SORT}/${garbageType}`)
      
      if (response.success) {
        console.log(`✅ 分拣${garbageType}成功:`, response.data?.message)
        console.log('📊 统计信息:', response.data?.statistics)
        await fetchSystemStatus()
      } else if (response.isBusinessError) {
        console.warn(`⚠️ 分拣${garbageType}失败:`, response.error)
      } else {
        console.error(`❌ 分拣${garbageType}失败:`, response.error)
      }
    } catch (err) {
      console.error(`❌ 分拣${garbageType}请求异常:`, err)
    }
  }

  // 组件卸载时清理资源
  useEffect(() => {
    return () => {
      if (stream) {
        stream.getTracks().forEach(track => track.stop())
      }
      if (detectionInterval) {
        clearInterval(detectionInterval)
      }
    }
  }, [stream, detectionInterval])

  // 加载相机标定参数
  const loadCalibrationParams = async () => {
    try {
      const response = await fetch(API_ENDPOINTS.CAMERA_CALIBRATION)
      if (response.ok) {
        const params = await response.json()
        setCalibrationParams(params)
        console.log('✅ 相机标定参数加载成功:', params)
        return params
      } else {
        console.warn('⚠️ 相机标定参数文件未找到，跳过镜头矫正')
        return null
      }
    } catch (err) {
      console.error('❌ 加载相机标定参数失败:', err)
      return null
    }
  }

  // 创建畸变矫正映射表
  const createUndistortMaps = (params: any) => {
    if (!params) return null
    
    try {
      const { K, D, img_shape } = params
      const width = img_shape[0]
      const height = img_shape[1]
      
      // 在前端创建映射表的简化版本
      // 实际应用中，我们会在处理每帧时直接应用矫正公式
      const maps = {
        K: K,
        D: D,
        width: width,
        height: height
      }
      
      setUndistortMaps(maps)
      console.log('✅ 畸变矫正映射表创建成功')
      return maps
    } catch (err) {
      console.error('❌ 创建畸变矫正映射表失败:', err)
      return null
    }
  }

  // 应用镜头矫正（优化版本）
  const applyLensCorrection = (canvas: HTMLCanvasElement, ctx: CanvasRenderingContext2D) => {
    if (!calibrationEnabled || !undistortMaps) return
    
    try {
      // 获取原始图像数据
      const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height)
      const data = imageData.data
      
      // 创建输出图像数据
      const outputData = new Uint8ClampedArray(data.length)
      
      // 应用鱼眼矫正（优化版本）
      const { K, D, width, height } = undistortMaps
      const cx = K[0][2]
      const cy = K[1][2]
      const fx = K[0][0]
      const fy = K[1][1]
      
      // 将畸变系数从二维数组转换为一维数组
      const distCoeffs = D.flat()
      
      // 使用步长优化，减少计算量
      const step = correctionQuality // 1=高质量, 2=中等, 3=低质量
      
      for (let y = 0; y < height; y += step) {
        for (let x = 0; x < width; x += step) {
          // 归一化坐标
          const xn = (x - cx) / fx
          const yn = (y - cy) / fy
          
          // 计算径向距离
          const r = Math.sqrt(xn * xn + yn * yn)
          
          // 应用畸变矫正（鱼眼模型）
          const r2 = r * r
          const r4 = r2 * r2
          const radial = 1 + distCoeffs[0] * r2 + distCoeffs[1] * r4 + distCoeffs[2] * r2 * r4 + distCoeffs[3] * r4 * r4
          
          // 矫正后的坐标
          const xu = xn * radial
          const yu = yn * radial
          
          // 转换回像素坐标
          const xd = Math.round(xu * fx + cx)
          const yd = Math.round(yu * fy + cy)
          
          // 边界检查和像素复制
          if (xd >= 0 && xd < width && yd >= 0 && yd < height) {
            const srcIndex = (y * width + x) * 4
            const dstIndex = (yd * width + xd) * 4
            
            if (srcIndex < data.length && dstIndex < outputData.length) {
              outputData[dstIndex] = data[srcIndex]         // R
              outputData[dstIndex + 1] = data[srcIndex + 1] // G
              outputData[dstIndex + 2] = data[srcIndex + 2] // B
              outputData[dstIndex + 3] = data[srcIndex + 3] // A
              
              // 如果使用步长，填充邻近像素
              if (step > 1) {
                for (let dy = 0; dy < step && (yd + dy) < height; dy++) {
                  for (let dx = 0; dx < step && (xd + dx) < width; dx++) {
                    const fillIndex = ((yd + dy) * width + (xd + dx)) * 4
                    if (fillIndex < outputData.length) {
                      outputData[fillIndex] = data[srcIndex]
                      outputData[fillIndex + 1] = data[srcIndex + 1]
                      outputData[fillIndex + 2] = data[srcIndex + 2]
                      outputData[fillIndex + 3] = data[srcIndex + 3]
                    }
                  }
                }
              }
            }
          }
        }
      }
      
      // 应用矫正后的图像数据
      const correctedImageData = new ImageData(outputData, width, height)
      ctx.putImageData(correctedImageData, 0, 0)
      
    } catch (err) {
      console.error('❌ 应用镜头矫正失败:', err)
    }
  }

  // 切换镜头矫正
  const toggleCalibration = async () => {
    if (!calibrationEnabled && !calibrationParams) {
      // 首次启用，加载参数
      const params = await loadCalibrationParams()
      if (params) {
        createUndistortMaps(params)
        setCalibrationEnabled(true)
        console.log('✅ 镜头矫正已启用')
      }
    } else {
      setCalibrationEnabled(!calibrationEnabled)
      console.log(calibrationEnabled ? '❌ 镜头矫正已禁用' : '✅ 镜头矫正已启用')
    }
  }

  // 页面加载时获取系统状态
  useEffect(() => {
    fetchSystemStatus()
    fetchRobotArmTypes()
    fetchCurrentArmConfig()
    
    // 尝试加载相机标定参数
    loadCalibrationParams().then(params => {
      if (params) {
        createUndistortMaps(params)
      }
    })
    
    const interval = setInterval(() => {
      if (!isLiveDetectingRef.current) {
        fetchSystemStatus()
        fetchCurrentArmConfig()
      } else {
        console.log('🔄 跳过系统状态更新 - 实时检测进行中')
      }
    }, 5000)
    return () => clearInterval(interval)
  }, [])

  return (
    <div className="min-h-screen bg-gradient-to-br from-green-50 to-blue-50 p-4">
      <div className="max-w-7xl mx-auto">
        {/* 页面标题 */}
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold text-gray-800 mb-2">
            🗑️ SmartBin 智能垃圾分拣系统
          </h1>
          <p className="text-gray-600">
            基于YOLOv8的实时垃圾识别与自动分拣系统
          </p>
        </div>

        {/* 错误提示 */}
        {error && (
          <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-6">
            ❌ {error}
          </div>
        )}

        {/* 系统状态卡片 */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4 mb-8">
          <StatusCard
            title="检测模型"
            status={systemStatus?.detector_loaded}
            icon="🤖"
          />
          <StatusCard
            title="摄像头"
            status={!!stream}
            icon="📹"
          />
          <StatusCard
            title="机械臂"
            status={systemStatus?.robot_arm_connected}
            icon="🦾"
          />
          <StatusCard
            title="实时检测"
            status={isLiveDetecting}
            icon="🔍"
          />
          <StatusCard
            title="系统就绪"
            status={systemStatus?.system_ready}
            icon="✅"
          />
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* 左侧控制面板 */}
          <div className="bg-white rounded-lg shadow-lg p-6">
            <h2 className="text-2xl font-semibold mb-6 text-gray-800">
              📋 控制面板
            </h2>

            {/* 模型管理 */}
            <div className="mb-6">
              <h3 className="text-lg font-medium mb-3">模型管理</h3>
              <button
                onClick={loadModel}
                disabled={loading || systemStatus?.detector_loaded}
                className={`w-full py-2 px-4 rounded-lg font-medium transition-colors ${
                  systemStatus?.detector_loaded
                    ? 'bg-green-100 text-green-800 cursor-not-allowed'
                    : 'bg-blue-500 hover:bg-blue-600 text-white'
                } ${loading ? 'opacity-50 cursor-not-allowed' : ''}`}
              >
                {loading
                  ? '🔄 加载中...'
                  : systemStatus?.detector_loaded
                  ? '✅ 模型已加载'
                  : '📥 加载检测模型'}
              </button>
            </div>

            {/* 摄像头控制 */}
            <div className="mb-6">
              <h3 className="text-lg font-medium mb-3">📹 摄像头控制</h3>
              <div className="space-y-3">
                {/* 镜头矫正开关 */}
                <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                  <div>
                    <span className="font-medium text-gray-800">镜头矫正</span>
                    <p className="text-sm text-gray-600">修正鱼眼镜头畸变</p>
                  </div>
                  <button
                    onClick={toggleCalibration}
                    disabled={isLiveDetecting}
                    className={`px-3 py-1 rounded-lg text-sm font-medium transition-colors ${
                      calibrationEnabled
                        ? 'bg-green-500 hover:bg-green-600 text-white'
                        : 'bg-gray-300 hover:bg-gray-400 text-gray-700'
                    } ${isLiveDetecting ? 'opacity-50 cursor-not-allowed' : ''}`}
                  >
                    {calibrationEnabled ? '✅ 已启用' : '❌ 已禁用'}
                  </button>
                </div>

                {/* 标定参数状态 */}
                {calibrationParams && (
                  <div className="p-3 bg-blue-50 rounded-lg">
                    <h4 className="font-medium text-blue-800 mb-2">📋 标定参数</h4>
                    <div className="text-sm text-blue-700 space-y-1">
                      <div>图像尺寸: {calibrationParams.img_shape[0]}x{calibrationParams.img_shape[1]}</div>
                      <div>焦距: fx={calibrationParams.K[0][0].toFixed(2)}, fy={calibrationParams.K[1][1].toFixed(2)}</div>
                      <div>光心: cx={calibrationParams.K[0][2].toFixed(2)}, cy={calibrationParams.K[1][2].toFixed(2)}</div>
                    </div>
                  </div>
                )}

                {/* 矫正质量调节 */}
                {calibrationParams && (
                  <div className="p-3 bg-purple-50 rounded-lg">
                    <h4 className="font-medium text-purple-800 mb-2">⚙️ 矫正质量</h4>
                    <div className="space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="text-sm text-purple-700">处理精度</span>
                        <select 
                          value={correctionQuality} 
                          onChange={(e) => setCorrectionQuality(Number(e.target.value))}
                          disabled={isLiveDetecting}
                          className="px-2 py-1 text-sm border rounded"
                        >
                          <option value={1}>高质量 (慢)</option>
                          <option value={2}>中等质量</option>
                          <option value={3}>低质量 (快)</option>
                        </select>
                      </div>
                      <div className="text-xs text-purple-600">
                        {correctionQuality === 1 && "最佳画质，处理较慢"}
                        {correctionQuality === 2 && "平衡画质与性能"}
                        {correctionQuality === 3 && "快速处理，画质略低"}
                      </div>
                    </div>
                  </div>
                )}

                {/* 矫正状态提示 */}
                {isLiveDetecting && (
                  <div className={`p-2 rounded-lg text-sm ${
                    calibrationEnabled
                      ? 'bg-green-100 text-green-800'
                      : 'bg-yellow-100 text-yellow-800'
                  }`}>
                    {calibrationEnabled
                      ? `🔧 镜头矫正正在应用中 (${correctionQuality === 1 ? '高质量' : correctionQuality === 2 ? '中等质量' : '低质量'})`
                      : '⚠️ 镜头矫正已禁用，图像可能有畸变'}
                  </div>
                )}
              </div>
            </div>

            {/* 机械臂管理 */}
            <div className="mb-6">
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-lg font-medium">🦾 机械臂管理</h3>
                <button
                  onClick={() => setShowArmManager(!showArmManager)}
                  className="px-3 py-1 text-sm bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors"
                >
                  {showArmManager ? '🔼 收起' : '🔽 展开'}
                </button>
              </div>
              
              {/* 当前机械臂信息 */}
              <div className="p-3 bg-gray-50 rounded-lg mb-3">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="font-medium text-gray-800">
                      {currentArmConfig?.type_info?.name || '未知机械臂'}
                    </p>
                    <p className="text-sm text-gray-600">
                      {currentArmConfig?.type_info?.description || '无描述'}
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                      systemStatus?.robot_arm_connected
                        ? 'bg-green-100 text-green-800'
                        : 'bg-red-100 text-red-800'
                    }`}>
                      {systemStatus?.robot_arm_connected ? '已连接' : '未连接'}
                    </span>
                    <button
                      onClick={() => toggleArmConnection(!systemStatus?.robot_arm_connected)}
                      disabled={switchingArm}
                      className={`px-3 py-1 text-xs rounded-lg font-medium transition-colors ${
                        systemStatus?.robot_arm_connected
                          ? 'bg-red-500 hover:bg-red-600 text-white'
                          : 'bg-green-500 hover:bg-green-600 text-white'
                      } ${switchingArm ? 'opacity-50 cursor-not-allowed' : ''}`}
                    >
                      {systemStatus?.robot_arm_connected ? '断开' : '连接'}
                    </button>
                  </div>
                </div>
              </div>

              {/* 机械臂配置信息 */}
              {showArmManager && currentArmConfig && (
                <div className="space-y-3">
                  {/* 基本配置 */}
                  <div className="p-3 bg-blue-50 rounded-lg">
                    <h4 className="font-medium text-blue-800 mb-2">📋 配置参数</h4>
                    <div className="grid grid-cols-2 gap-2 text-sm">
                      <div>
                        <span className="text-gray-600">最大半径:</span>
                        <span className="ml-2 font-medium">{currentArmConfig.configuration.max_reach}mm</span>
                      </div>
                      <div>
                        <span className="text-gray-600">最大负载:</span>
                        <span className="ml-2 font-medium">{currentArmConfig.configuration.max_payload}kg</span>
                      </div>
                      <div>
                        <span className="text-gray-600">自由度:</span>
                        <span className="ml-2 font-medium">{currentArmConfig.configuration.degrees_of_freedom}轴</span>
                      </div>
                      <div>
                        <span className="text-gray-600">定位精度:</span>
                        <span className="ml-2 font-medium">{currentArmConfig.configuration.precision}mm</span>
                      </div>
                    </div>
                  </div>

                  {/* 功能特性 */}
                  <div className="p-3 bg-purple-50 rounded-lg">
                    <h4 className="font-medium text-purple-800 mb-2">✨ 功能特性</h4>
                    <div className="flex flex-wrap gap-1">
                      {currentArmConfig.type_info.features.map((feature, index) => (
                        <span key={index} className="px-2 py-1 text-xs bg-purple-100 text-purple-700 rounded-full">
                          {feature}
                        </span>
                      ))}
                    </div>
                  </div>

                  {/* 机械臂类型选择 */}
                  <div className="p-3 bg-orange-50 rounded-lg">
                    <h4 className="font-medium text-orange-800 mb-2">🔄 切换机械臂类型</h4>
                    <div className="space-y-2">
                      {robotArmTypes.map((armType) => (
                        <div key={armType.type} className={`p-2 rounded-lg border-2 transition-colors ${
                          currentArmConfig.current_type === armType.type
                            ? 'border-orange-300 bg-orange-100'
                            : 'border-gray-200 bg-white hover:border-orange-200'
                        }`}>
                          <div className="flex items-center justify-between">
                            <div className="flex-1">
                              <div className="flex items-center gap-2">
                                <span className="font-medium text-gray-800">{armType.name}</span>
                                {!armType.available && (
                                  <span className="px-1 py-0.5 text-xs bg-red-100 text-red-600 rounded">
                                    不可用
                                  </span>
                                )}
                                {currentArmConfig.current_type === armType.type && (
                                  <span className="px-1 py-0.5 text-xs bg-green-100 text-green-600 rounded">
                                    当前
                                  </span>
                                )}
                              </div>
                              <p className="text-xs text-gray-600 mt-1">{armType.description}</p>
                            </div>
                            {currentArmConfig.current_type !== armType.type && armType.available && (
                              <button
                                onClick={() => switchRobotArmType(armType.type)}
                                disabled={switchingArm}
                                className={`px-2 py-1 text-xs rounded-lg font-medium transition-colors ${
                                  switchingArm
                                    ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                                    : 'bg-orange-500 hover:bg-orange-600 text-white'
                                }`}
                              >
                                {switchingArm ? '切换中...' : '选择'}
                              </button>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* 机械臂状态显示 */}
                  {systemStatus?.robot_arm_status && (
                    <div className="p-3 bg-gray-50 rounded-lg">
                      <h4 className="font-medium text-gray-800 mb-2">📊 运行状态</h4>
                      <div className="grid grid-cols-2 gap-2 text-sm">
                        <div>
                          <span className="text-gray-600">运行状态:</span>
                          <span className={`ml-2 font-medium ${
                            systemStatus.robot_arm_status.status === 'idle' ? 'text-green-600' : 'text-orange-600'
                          }`}>
                            {systemStatus.robot_arm_status.status === 'idle' ? '🟢 空闲' : '🟠 运行中'}
                          </span>
                        </div>
                        <div>
                          <span className="text-gray-600">抓取状态:</span>
                          <span className={`ml-2 ${systemStatus.robot_arm_status.has_object ? 'text-orange-600' : 'text-green-600'}`}>
                            {systemStatus.robot_arm_status.has_object ? '🟠 有物体' : '🟢 空闲'}
                          </span>
                        </div>
                        <div className="col-span-2">
                          <span className="text-gray-600">位置:</span>
                          <span className="ml-2 font-mono text-xs">
                            ({systemStatus.robot_arm_status.current_position.x.toFixed(1)}, 
                             {systemStatus.robot_arm_status.current_position.y.toFixed(1)}, 
                             {systemStatus.robot_arm_status.current_position.z.toFixed(1)})
                          </span>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* 调试按钮 */}
                  <div className="grid grid-cols-2 gap-2">
                    <button 
                      onClick={() => testRobotArmFunction('home')}
                      className="py-2 px-3 bg-blue-500 hover:bg-blue-600 text-white rounded text-sm font-medium transition-colors"
                    >
                      🏠 归位
                    </button>
                    <button 
                      onClick={() => testRobotArmFunction('emergency_stop')}
                      className="py-2 px-3 bg-red-500 hover:bg-red-600 text-white rounded text-sm font-medium transition-colors"
                    >
                      🚨 急停
                    </button>
                  </div>

                  {/* 垃圾分拣测试 */}
                  <div className="mt-3">
                    <p className="text-xs text-gray-600 mb-2">测试垃圾分拣:</p>
                    <div className="grid grid-cols-3 gap-1">
                      {['plastic', 'banana', 'beverages'].map((type) => (
                        <button
                          key={type}
                          onClick={() => testRobotArmSort(type)}
                          className="py-1 px-2 bg-green-500 hover:bg-green-600 text-white rounded text-xs font-medium transition-colors"
                        >
                          {type}
                        </button>
                      ))}
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* 图像检测 */}
            <div className="mb-6">
              <h3 className="text-lg font-medium mb-3">图像检测</h3>
              <div className="border-2 border-dashed border-gray-300 rounded-lg p-4 text-center">
                <input
                  type="file"
                  accept="image/*"
                  onChange={(e) => setSelectedImage(e.target.files?.[0] || null)}
                  className="hidden"
                  id="imageInput"
                />
                <label
                  htmlFor="imageInput"
                  className="cursor-pointer block"
                >
                  {selectedImage ? (
                    <div>
                      <p className="text-green-600 font-medium">
                        📷 {selectedImage.name}
                      </p>
                      <p className="text-sm text-gray-500 mt-1">
                        点击重新选择
                      </p>
                    </div>
                  ) : (
                    <div>
                      <p className="text-gray-600">
                        📁 点击选择图像文件
                      </p>
                      <p className="text-sm text-gray-400 mt-1">
                        支持 JPG, PNG 格式
                      </p>
                    </div>
                  )}
                </label>
              </div>
              
              <button
                onClick={detectImage}
                disabled={!selectedImage || !systemStatus?.detector_loaded || loading}
                className={`w-full mt-3 py-2 px-4 rounded-lg font-medium transition-colors ${
                  !selectedImage || !systemStatus?.detector_loaded
                    ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                    : 'bg-green-500 hover:bg-green-600 text-white'
                } ${loading ? 'opacity-50 cursor-not-allowed' : ''}`}
              >
                {loading ? '🔄 检测中...' : '🔍 开始检测'}
              </button>
            </div>

            {/* 实时检测控制 */}
            <div className="mb-6">
              <h3 className="text-lg font-medium mb-3">实时检测</h3>
              
              <div className="space-y-3">
                {/* 检测参数控制 */}
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-sm text-gray-600 mb-1">检测频率 (FPS)</label>
                    <input
                      type="range"
                      min="0.5"
                      max="5"
                      step="0.5"
                      value={detectionFps}
                      onChange={(e) => setDetectionFps(parseFloat(e.target.value))}
                      className="w-full"
                    />
                    <span className="text-xs text-gray-500">{detectionFps}fps</span>
                  </div>
                  <div>
                    <label className="block text-sm text-gray-600 mb-1">触发阈值</label>
                    <input
                      type="range"
                      min="0.1"
                      max="1"
                      step="0.1"
                      value={armTriggerConfidence}
                      onChange={(e) => setArmTriggerConfidence(parseFloat(e.target.value))}
                      className="w-full"
                    />
                    <span className="text-xs text-gray-500">{(armTriggerConfidence * 100).toFixed(0)}%</span>
                  </div>
                </div>

                {/* 实时检测按钮 */}
                <button
                  onClick={isLiveDetecting ? stopLiveDetection : startLiveDetection}
                  disabled={!systemStatus?.detector_loaded}
                  className={`w-full py-2 px-4 rounded-lg font-medium transition-colors ${
                    !systemStatus?.detector_loaded
                      ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                      : isLiveDetecting
                      ? 'bg-red-500 hover:bg-red-600 text-white'
                      : 'bg-green-500 hover:bg-green-600 text-white'
                  }`}
                >
                  {!systemStatus?.detector_loaded
                    ? '⚠️ 请先加载模型'
                    : isLiveDetecting
                    ? '🛑 停止实时检测'
                    : '📹 开始实时检测'}
                </button>
              </div>
            </div>
          </div>

          {/* 右侧检测结果 */}
          <div className="bg-white rounded-lg shadow-lg p-6">
            <h2 className="text-2xl font-semibold mb-6 text-gray-800">
              📊 检测结果
            </h2>

            {/* 实时检测区域 */}
            {isLiveDetecting ? (
              <div>
                {/* AI检测画面 */}
                <div className="mb-4">
                  <canvas
                    ref={canvasRef}
                    className="w-full rounded-lg border shadow-lg bg-black"
                    style={{ maxHeight: '400px' }}
                  />
                  <div className="flex justify-between items-center mt-2">
                    <p className="text-sm text-green-600 font-medium">
                      🤖 实时AI检测 ({stream ? '✅ 已连接' : '⚠️ 未连接'})
                    </p>
                    <p className="text-sm text-gray-500">
                      检测到 {liveResults.length} 个物体
                    </p>
                  </div>
                </div>

                {/* 隐藏的视频元素用于捕获 */}
                <video
                  ref={videoRef}
                  autoPlay
                  muted
                  playsInline
                  style={{ display: 'none' }}
                />

                {/* 实时检测结果列表 */}
                {liveResults.length > 0 && (
                  <div>
                    <h3 className="text-lg font-medium mb-3">实时检测结果</h3>
                    <div className="space-y-2 max-h-48 overflow-y-auto">
                      {liveResults.map((result, index) => (
                        <div
                          key={index}
                          className="flex justify-between items-center p-3 bg-gray-50 rounded-lg"
                        >
                          <span className="font-medium">
                            🗑️ {result.class}
                          </span>
                          <span className="text-green-600 font-semibold">
                            {(result.confidence * 100).toFixed(1)}%
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ) : detectionResult ? (
              <div>
                {/* 静态检测图像 */}
                <div className="mb-4">
                  <img
                    src={detectionResult.image}
                    alt="检测结果"
                    className="w-full rounded-lg border"
                  />
                </div>

                {/* 静态检测详情 */}
                <div>
                  <h3 className="text-lg font-medium mb-3">检测详情</h3>
                  {detectionResult.results.length > 0 ? (
                    <div className="space-y-2">
                      {detectionResult.results.map((result, index) => (
                        <div
                          key={index}
                          className="flex justify-between items-center p-3 bg-gray-50 rounded-lg"
                        >
                          <span className="font-medium">
                            🗑️ {result.class}
                          </span>
                          <span className="text-green-600 font-semibold">
                            {(result.confidence * 100).toFixed(1)}%
                          </span>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-gray-500 text-center py-4">
                      未检测到垃圾物品
                    </p>
                  )}
                </div>
              </div>
            ) : (
              <div className="text-center py-12 text-gray-400">
                <div className="text-6xl mb-4">🖼️</div>
                <p>上传图像或启动实时检测</p>
              </div>
            )}
          </div>
        </div>

        {/* 垃圾分类说明 */}
        <div className="mt-8 bg-white rounded-lg shadow-lg p-6">
          <h2 className="text-2xl font-semibold mb-4 text-gray-800">
            📚 支持的垃圾分类
          </h2>
          <div className="grid grid-cols-3 md:grid-cols-5 lg:grid-cols-9 gap-4">
            {[
              { name: '香蕉皮', icon: '🍌', color: 'bg-yellow-100' },
              { name: '饮料瓶', icon: '🍶', color: 'bg-blue-100' },
              { name: '纸盒', icon: '📦', color: 'bg-orange-100' },
              { name: '薯片袋', icon: '🥔', color: 'bg-red-100' },
              { name: '鱼骨', icon: '🐟', color: 'bg-green-100' },
              { name: '泡面盒', icon: '🍜', color: 'bg-purple-100' },
              { name: '牛奶盒1', icon: '🥛', color: 'bg-pink-100' },
              { name: '牛奶盒2', icon: '🧈', color: 'bg-indigo-100' },
              { name: '塑料', icon: '♻️', color: 'bg-teal-100' },
            ].map((item, index) => (
              <div
                key={index}
                className={`${item.color} p-3 rounded-lg text-center`}
              >
                <div className="text-2xl mb-1">{item.icon}</div>
                <div className="text-sm font-medium text-gray-700">
                  {item.name}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}

// 状态卡片组件
function StatusCard({ title, status, icon }: {
  title: string
  status?: boolean
  icon: string
}) {
  return (
    <div className="bg-white rounded-lg shadow-lg p-4">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm text-gray-600">{title}</p>
          <p className={`font-semibold ${
            status ? 'text-green-600' : 'text-red-600'
          }`}>
            {status ? '正常' : '离线'}
          </p>
        </div>
        <div className="text-2xl">{icon}</div>
      </div>
      <div className="mt-2 h-2 bg-gray-200 rounded-full">
        <div
          className={`h-full rounded-full transition-all duration-300 ${
            status ? 'bg-green-500 w-full' : 'bg-red-500 w-1/4'
          }`}
        ></div>
      </div>
    </div>
  )
} 