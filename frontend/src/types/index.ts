// ===== 后端响应数据模型 =====

export interface Location {
  longitude: number
  latitude: number
}

export interface Attraction {
  name: string
  address: string
  location: Location
  visit_duration: number // 单位：分钟
  description: string
  category?: string
  rating?: number
  image_url?: string
  ticket_price?: number
}

export interface Meal {
  type: 'breakfast' | 'lunch' | 'dinner' | 'snack'
  name: string
  address?: string
  location?: Location
  description?: string
  estimated_cost?: number
}

export interface Hotel {
  name: string
  address: string
  location?: Location
  price_range: string // 文字描述，如 "300-500元"
  rating: string // 文字描述，如 "4.5分"
  distance: string // 文字描述，如 "距离市中心2km"
  type: string
  estimated_cost?: number
}

// 行程总预算（后端汇总）
export interface Budget {
  total_attractions: number
  total_hotels: number
  total_meals: number
  total_transportation: number
  total: number
}

// 单日行程，TripPlan.days 的数组元素
export interface DayPlan {
  date: string
  day_index: number // 从 0 开始
  description: string
  transportation: string
  accommodation: string
  hotel?: Hotel
  attractions: Attraction[]
  meals: Meal[]
}

export interface WeatherInfo {
  date: string
  day_weather: string
  night_weather: string
  day_temp: number
  night_temp: number
  wind_direction: string
  wind_power: string
}

// 后端 /api/trip/plan 返回的完整旅行计划
export interface TripPlan {
  city: string
  start_date: string
  end_date: string
  days: DayPlan[]
  weather_info: WeatherInfo[]
  overall_suggestions: string
  budget?: Budget
}

// ===== 前端请求数据模型 =====

// Home.vue 表单提交给后端的请求体
export interface TripFormData {
  city: string
  start_date: string
  end_date: string
  travel_days: number
  transportation: string // 公共交通 | 自驾 | 步行 | 混合
  accommodation: string // 经济型酒店 | 舒适型酒店 | 豪华酒店 | 民宿
  preferences: string[] // 历史文化 | 自然风光 | 美食 | 购物 | 艺术 | 休闲
  free_text_input: string
}

// 后端统一响应包装
export interface TripPlanResponse {
  success: boolean
  message: string
  data?: TripPlan // 仅 success=true 时有值
}

