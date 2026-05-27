"""多智能体旅行规划系统 — 基于LangChain 1.0"""
import asyncio
import json
from typing import Dict, Any
from langchain.agents import create_agent
from langchain_core.messages import HumanMessage
from ..services.llm_service import get_llm
from ..services.amap_service import get_amap_tools
from ..models.schemas import TripRequest, TripPlan, DayPlan, Attraction, Meal, Location, Hotel
from ..config import get_settings

# ============ Agent提示词（简化版，无需 TOOL_CALL 格式） ============
# OpenAI（以及所有兼容接口）的 Chat API 支持一个叫 function calling（也叫 tool calling）的功能。
# 工具的名字、描述、参数 schema 是作为 API 请求的一个独立字段 tools 传给模型的，而不是写在提示词里的文本。
# 模型收到这个请求后，直接在 API 响应里返回结构化的 JSON，而不是输出文本。
ATTRACTION_AGENT_PROMPT = """你是景点搜索专家。使用高德地图工具搜索指定城市的景点。

规则：
1. 必须使用工具搜索，不要编造景点信息
2. 返回景点名称、地址、坐标、类别和简要描述
3. 根据用户偏好筛选合适的景点类型
"""

WEATHER_AGENT_PROMPT = """你是天气查询专家。使用工具查询指定城市的天气信息。

规则：
1. 必须使用工具查询天气，不要编造信息
2. 返回每天的天气、温度、风力等信息
"""

HOTEL_AGENT_PROMPT = """你是酒店推荐专家。使用工具搜索指定城市的酒店。

规则：
1. 必须使用工具搜索酒店，不要编造信息
2. 返回酒店名称、地址、价格、评分等信息
3. 根据用户偏好推荐合适档次的酒店
"""

PLANNER_AGENT_PROMPT = """你是行程规划专家。根据景点、天气、酒店信息，生成详细的旅行计划。

请严格按照以下JSON格式返回旅行计划：
```json
{
  "city": "城市名称",
  "start_date": "YYYY-MM-DD",
  "end_date": "YYYY-MM-DD",
  "days": [
    {
      "date": "YYYY-MM-DD",
      "day_index": 0,
      "description": "第1天行程概述",
      "transportation": "交通方式",
      "accommodation": "住宿类型",
      "hotel": {
        "name": "酒店名称",
        "address": "酒店地址",
        "location": {"longitude": 116.397128, "latitude": 39.916527},
        "price_range": "300-500元",
        "rating": "4.5",
        "distance": "距离景点2公里",
        "type": "经济型酒店",
        "estimated_cost": 400
      },
      "attractions": [
        {
          "name": "景点名称",
          "address": "详细地址",
          "location": {"longitude": 116.397128, "latitude": 39.916527},
          "visit_duration": 120,
          "description": "景点详细描述",
          "category": "景点类别",
          "ticket_price": 60
        }
      ],
      "meals": [
        {"type": "breakfast", "name": "早餐推荐", "description": "早餐描述", "estimated_cost": 30},
        {"type": "lunch", "name": "午餐推荐", "description": "午餐描述", "estimated_cost": 50},
        {"type": "dinner", "name": "晚餐推荐", "description": "晚餐描述", "estimated_cost": 80}
      ]
    }
  ],
  "weather_info": [
    {
      "date": "YYYY-MM-DD",
      "day_weather": "晴",
      "night_weather": "多云",
      "day_temp": 25,
      "night_temp": 15,
      "wind_direction": "南风",
      "wind_power": "1-3级"
    }
  ],
  "overall_suggestions": "总体建议",
  "budget": {
    "total_attractions": 180,
    "total_hotels": 1200,
    "total_meals": 480,
    "total_transportation": 200,
    "total": 2060
  }
}
```

**规则:**
1. weather_info数组必须包含每一天的天气信息
2. 温度必须是纯数字(不要带°C等单位)
3. 每天安排2-3个景点
4. 考虑景点之间的距离和游览时间
5. 每天必须包含早中晚三餐
6. 必须包含预算信息
"""




class MultiAgentTripPlanner:
    """多智能体旅行规划系统（LangChain 1.0版）"""

    def __init__(self):
        """初始化——注意：只保存配置，不创建Agent"""
        print("🔄 开始初始化多智能体旅行规划系统...")

        settings = get_settings()
        self.llm = get_llm()
        self.settings = settings

        # Agent 实例在 _init_agents() 中异步创建
        self.attraction_agent = None
        self.weather_agent = None
        self.hotel_agent = None
        self.planner_agent = None
        self._initialized = False

        print("✅ 多智能体系统配置完成（Agent将在首次调用时异步初始化）")

    async def _init_agents(self):
        """异步初始化Agent（因为MCP工具加载是异步的）"""
        if self._initialized:
            return

        print("  - 加载MCP工具...")
        amap_tools = await get_amap_tools()
        print(f"  - 获取到 {len(amap_tools)} 个工具")

        # 将工具分为两类：搜索类（给景点/酒店Agent）和所有工具（给规划Agent）
        # 实际上所有Agent都给全部工具，靠 system_prompt 限制行为

        print("  - 创建景点搜索Agent...")
        self.attraction_agent = create_agent(
            model=self.llm,
            tools=amap_tools,
            system_prompt=ATTRACTION_AGENT_PROMPT
        )

        print("  - 创建天气查询Agent...")
        self.weather_agent = create_agent(
            model=self.llm,
            tools=amap_tools,
            system_prompt=WEATHER_AGENT_PROMPT
        )

        print("  - 创建酒店推荐Agent...")
        self.hotel_agent = create_agent(
            model=self.llm,
            tools=amap_tools,
            system_prompt=HOTEL_AGENT_PROMPT
        )

        print("  - 创建行程规划Agent...")
        self.planner_agent = create_agent(
            model=self.llm,
            tools=amap_tools,          # 规划Agent也可以调工具补充信息
            system_prompt=PLANNER_AGENT_PROMPT
        )

        self._initialized = True
        print("✅ 所有Agent创建完成")

    async def plan_trip(self, request: TripRequest) -> TripPlan:
        """
        使用多智能体协作生成旅行计划

        Args:
            request: 旅行请求

        Returns:
            旅行计划
        """
        try:
            # 确保 Agent 已初始化
            await self._init_agents()

            print(f"\n{'='*60}")
            print(f"🚀 开始多智能体协作规划旅行...")
            print(f"目的地: {request.city}")
            print(f"日期: {request.start_date} 至 {request.end_date}")
            print(f"天数: {request.travel_days}天")
            print(f"偏好: {', '.join(request.preferences) if request.preferences else '无'}")
            print(f"{'='*60}\n")

            # 步骤1: 景点搜索Agent搜索景点
            print("📍 步骤1: 搜索景点...")
            attraction_query = self._build_attraction_query(request)
            attraction_response = await self._run_agent(
                self.attraction_agent, attraction_query
            )
            print(f"景点搜索结果: {attraction_response[:200]}...\n")

            # 步骤2: 天气查询Agent查询天气
            print("🌤️  步骤2: 查询天气...")
            weather_query = f"请查询{request.city}未来{request.travel_days}天的天气信息"
            weather_response = await self._run_agent(
                self.weather_agent, weather_query
            )
            print(f"天气查询结果: {weather_response[:200]}...\n")

            # 步骤3: 酒店推荐Agent搜索酒店
            print("🏨 步骤3: 搜索酒店...")
            hotel_query = f"请搜索{request.city}的{request.accommodation}酒店"
            hotel_response = await self._run_agent(
                self.hotel_agent, hotel_query
            )
            print(f"酒店搜索结果: {hotel_response[:200]}...\n")

            # 步骤4: 行程规划Agent整合信息生成计划
            print("📋 步骤4: 生成行程计划...")
            planner_query = self._build_planner_query(
                request, attraction_response, weather_response, hotel_response
            )
            planner_response = await self._run_agent(
                self.planner_agent, planner_query
            )
            print(f"行程规划结果: {planner_response[:300]}...\n")

            # 解析最终计划
            trip_plan = self._parse_response(planner_response, request)

            print(f"{'='*60}")
            print(f"✅ 旅行计划生成完成!")
            print(f"{'='*60}\n")

            return trip_plan

        except Exception as e:
            print(f"❌ 生成旅行计划失败: {str(e)}")
            import traceback
            traceback.print_exc()
            return self._create_fallback_plan(request)

    async def _run_agent(self, agent, query: str, max_retries: int = 3) -> str:
        """
        运行一个Agent并返回文本结果（带自动重试，应对API网关间歇性503）。

        LangChain 的 agent.invoke() 返回完整的消息历史，
        我们只需要最后一条 AI 消息的文本内容。
        """
        last_error = None
        for attempt in range(max_retries):
            try:
                result = await agent.ainvoke({
                    "messages": [HumanMessage(content=query)]
                })
                # 从消息历史中提取最后一条 AI 消息
                messages = result["messages"]
                for msg in reversed(messages):
                    if hasattr(msg, "content") and msg.content and msg.type == "ai":
                        return msg.content
                return ""
            except Exception as e:
                last_error = e
                if attempt < max_retries - 1:
                    wait = 2 ** attempt  # 1s, 2s, 4s...
                    print(f"⚠️  Agent调用失败（第{attempt+1}次），{wait}秒后重试: {str(e)[:100]}")
                    await asyncio.sleep(wait)
        raise last_error

    def _build_attraction_query(self, request: TripRequest) -> str:
        """构建景点搜索查询（不再需要拼 TOOL_CALL 格式）"""
        if request.preferences:
            keywords = "、".join(request.preferences)
        else:
            keywords = "热门景点"

        return f"请搜索{request.city}的{keywords}相关景点，列出至少5个景点，包括名称、地址、坐标和简要描述。"

    def _build_planner_query(self, request: TripRequest, attractions: str, weather: str, hotels: str) -> str:
        """构建行程规划查询"""
        query = f"""请根据以下信息生成{request.city}的{request.travel_days}天旅行计划:

**基本信息:**
- 城市: {request.city}
- 日期: {request.start_date} 至 {request.end_date}
- 天数: {request.travel_days}天
- 交通方式: {request.transportation}
- 住宿: {request.accommodation}
- 偏好: {', '.join(request.preferences) if request.preferences else '无'}

**景点信息:**
{attractions}

**天气信息:**
{weather}

**酒店信息:**
{hotels}

**要求:**
1. 每天安排2-3个景点
2. 每天必须包含早中晚三餐
3. 每天推荐一个具体的酒店(从酒店信息中选择)
4. 考虑景点之间的距离和交通方式
5. 返回完整的JSON格式数据
6. 景点的经纬度坐标要真实准确
"""
        if request.free_text_input:
            query += f"\n**额外要求:** {request.free_text_input}"

        return query

    # _parse_response、_create_fallback_plan 方法保持不变
    # （从旧代码直接复制过来即可）

    def _parse_response(self, response: str, request: TripRequest) -> TripPlan:
        """解析Agent响应中的JSON（自动修复格式错误）"""
        from json_repair import repair_json

        try:
            # 从响应中提取 JSON 文本
            if "```json" in response:
                json_start = response.find("```json") + 7
                json_end = response.find("```", json_start)
                json_str = response[json_start:json_end].strip()
            elif "```" in response:
                json_start = response.find("```") + 3
                json_end = response.find("```", json_start)
                json_str = response[json_start:json_end].strip()
            elif "{" in response and "}" in response:
                json_start = response.find("{")
                json_end = response.rfind("}") + 1
                json_str = response[json_start:json_end]
            else:
                raise ValueError("响应中未找到JSON数据")

            # 用 json_repair 自动修复缺逗号、多余逗号等常见格式问题
            fixed = repair_json(json_str)
            data = json.loads(fixed)
            return TripPlan(**data)

        except Exception as e:
            print(f"⚠️  解析响应失败: {str(e)}")
            return self._create_fallback_plan(request)

    def _create_fallback_plan(self, request: TripRequest) -> TripPlan:
        """创建备用计划（与旧代码相同）"""
        from datetime import datetime, timedelta

        start_date = datetime.strptime(request.start_date, "%Y-%m-%d")

        days = []
        for i in range(request.travel_days):
            current_date = start_date + timedelta(days=i)
            day_plan = DayPlan(
                date=current_date.strftime("%Y-%m-%d"),
                day_index=i,
                description=f"第{i+1}天行程",
                transportation=request.transportation,
                accommodation=request.accommodation,
                attractions=[
                    Attraction(
                        name=f"{request.city}景点{j+1}",
                        address=f"{request.city}市",
                        location=Location(longitude=116.4 + i*0.01 + j*0.005, latitude=39.9 + i*0.01 + j*0.005),
                        visit_duration=120,
                        description=f"这是{request.city}的著名景点",
                        category="景点"
                    )
                    for j in range(2)
                ],
                meals=[
                    Meal(type="breakfast", name=f"第{i+1}天早餐", description="当地特色早餐"),
                    Meal(type="lunch", name=f"第{i+1}天午餐", description="午餐推荐"),
                    Meal(type="dinner", name=f"第{i+1}天晚餐", description="晚餐推荐")
                ]
            )
            days.append(day_plan)

        return TripPlan(
            city=request.city,
            start_date=request.start_date,
            end_date=request.end_date,
            days=days,
            weather_info=[],
            overall_suggestions=f"这是为您规划的{request.city}{request.travel_days}日游行程,建议提前查看各景点的开放时间。"
        )


# 全局多智能体系统实例
_multi_agent_planner = None

def get_trip_planner_agent() -> MultiAgentTripPlanner:
    """获取多智能体旅行规划系统实例（单例模式）"""
    global _multi_agent_planner
    if _multi_agent_planner is None:
        _multi_agent_planner = MultiAgentTripPlanner()
    return _multi_agent_planner
