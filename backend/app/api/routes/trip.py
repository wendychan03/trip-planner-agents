"""
旅行规划API路由

路由匹配过程：
  前端用 axios 发请求: POST /api/trip/plan
            ↓
  main.py:   /api 前缀匹配 → 交给 trip.router
            ↓
  trip.py:   /trip 前缀匹配 → 找到 @router.post("/plan")
            ↓
  FastAPI:   用 TripRequest 校验 JSON body
            ↓
  调用 plan_trip(request) → 返回 TripPlanResponse
"""

from fastapi import APIRouter, HTTPException
from ...models.schemas import (
    TripRequest,
    TripPlanResponse,
    ErrorResponse
)
from ...agents.trip_planner_agent import get_trip_planner_agent

router = APIRouter(prefix="/trip", tags=["旅行规划"])
# 小型 FastAPI 实例，prefix="/trip" → 本文件所有路径自动加 /trip 前缀
# tags=["旅行规划"] → Swagger UI 中按"旅行规划"分组显示

# POST :我想提交数据，让服务器处理、创建或生成结果（有副作用、有请求体、非幂等）
@router.post(
    "/plan",                                 # 拼成 POST /trip/plan（再由 main.py 的 /api 前缀 → /api/trip/plan）
    response_model=TripPlanResponse,         # 返回数据自动按此模型校验，并生成 Swagger 响应文档
    summary="生成旅行计划",                   # Swagger 标题
    description="根据用户输入的旅行需求,生成详细的旅行计划"
)
async def plan_trip(request: TripRequest):
    """
    生成旅行计划

    Args:
        request: 旅行请求参数

    Returns:
        旅行计划响应
    """
    try:
        print(f"\n{'='*60}")
        print(f"📥 收到旅行规划请求:")
        print(f"   城市: {request.city}")
        print(f"   日期: {request.start_date} - {request.end_date}")
        print(f"   天数: {request.travel_days}")
        print(f"{'='*60}\n")

        # 获取Agent实例
        print("🔄 获取多智能体系统实例...")
        agent = get_trip_planner_agent()

        # 生成旅行计划
        print("🚀 开始生成旅行计划...")
        trip_plan = agent.plan_trip(request)

        print("✅ 旅行计划生成成功,准备返回响应\n")

        return TripPlanResponse(
            success=True,
            message="旅行计划生成成功",
            data=trip_plan
        )

    except Exception as e:
        print(f"❌ 生成旅行计划失败: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"生成旅行计划失败: {str(e)}"
        )

# GET : 我想拿已有的数据（无副作用、无请求体、幂等）
@router.get(
    "/health",
    summary="健康检查",
    description="检查旅行规划服务是否正常"
)
async def health_check():
    """健康检查"""
    try:
        # 检查Agent是否可用
        agent = get_trip_planner_agent()
        
        return {
            "status": "healthy",
            "service": "trip-planner",
            "agent_name": agent.agent.name,
            "tools_count": len(agent.agent.list_tools())
        }
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"服务不可用: {str(e)}"
        )

