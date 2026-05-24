
// api.ts 就是前端和后端的唯一沟通渠道，所有数据请求都经过这个文件。
// 前端页面不会直接调后端接口，而是通过这里的函数来调。

// axios：HTTP 请求库，类似浏览器的 fetch，但功能更强（拦截器、超时等）
import axios from 'axios'
import type { TripFormData, TripPlanResponse } from '@/types'

// 后端地址：优先读环境变量，未设置则默认本地 8000 端口
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

// 创建 axios 实例，统一配置所有请求的默认行为
const apiClient = axios.create({
  baseURL: API_BASE_URL, // 所有请求自动拼上这个前缀
  timeout: 120000, // AI 生成计划较慢，设 2 分钟超时
  headers: {
    'Content-Type': 'application/json' // 告诉后端请求体是 JSON 格式
  }
})

// 请求拦截器：每次发请求前自动执行
apiClient.interceptors.request.use(
  (config) => {
    console.log('发送请求:', config.method?.toUpperCase(), config.url)
    return config
  },
  (error) => {
    console.error('请求错误:', error)
    return Promise.reject(error)
  }
)

// 响应拦截器：每次收到响应后自动执行
apiClient.interceptors.response.use(
  (response) => {
    console.log('收到响应:', response.status, response.config.url)
    return response
  },
  (error) => {
    console.error('响应错误:', error.response?.status, error.message)
    return Promise.reject(error)
  }
)

// 核心 API：向 POST /api/trip/plan 发送表单数据，返回 AI 生成的旅行计划
export async function generateTripPlan(formData: TripFormData): Promise<TripPlanResponse> {
  try {
    const response = await apiClient.post<TripPlanResponse>('/api/trip/plan', formData)
    return response.data // axios 响应体包装在 .data 里
  } catch (error: any) {
    console.error('生成旅行计划失败:', error)
    // 优先取后端返回的 detail 信息，否则用兜底文案
    throw new Error(error.response?.data?.detail || error.message || '生成旅行计划失败')
  }
}

// 检查后端是否在线
export async function healthCheck(): Promise<any> {
  try {
    const response = await apiClient.get('/health')
    return response.data
  } catch (error: any) {
    console.error('健康检查失败:', error)
    throw new Error(error.message || '健康检查失败')
  }
}

export default apiClient

