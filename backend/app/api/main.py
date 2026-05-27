"""FastAPI 应用工厂 — 创建实例、挂载中间件、注册路由、绑定生命周期钩子"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from ..config import get_settings, validate_config, print_config
from .routes import trip, poi

# 获取配置
settings = get_settings()

# ============================================================
# 1. 创建 FastAPI 实例
# ============================================================
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="基于HelloAgents框架的智能旅行规划助手API",
    docs_url="/docs",          # Swagger UI 文档入口
    redoc_url="/redoc"         # ReDoc 文档入口
)

# ============================================================
# 2. 挂载 CORS 中间件 — 允许跨域请求
#    浏览器同源策略会拦截不同端口/域名的请求，后端必须声明允许
# ============================================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_origins_list(),  # 允许的前端地址列表
    allow_credentials=True,                          # 允许携带 Cookie/Authorization
    allow_methods=["*"],                             # 允许所有 HTTP 方法
    allow_headers=["*"],                             # 允许所有请求头
)

# ============================================================
# 3. 注册业务路由 — 各模块的 APIRouter 挂载到 /api 前缀下
# ============================================================
app.include_router(trip.router, prefix="/api")       # 行程规划
app.include_router(poi.router, prefix="/api")        # 景点图片（Unsplash）


# ============================================================
# 4. 生命周期钩子
# ============================================================

@app.on_event("startup")
async def startup_event():
    """startup 钩子：服务器就绪后、接收请求前执行，用于校验配置"""
    """服务器就绪后执行：打印横幅 → 打印配置 → 校验 API Key（失败则阻止启动）"""
    print("\n" + "="*60)
    print(f"🚀 {settings.app_name} v{settings.app_version}")
    print("="*60)

    print_config()
    try:        
        validate_config()             # 校验关键 API Key，失败则阻止启动
        print("\n✅ 配置验证通过")
    except ValueError as e:
        print(f"\n❌ 配置验证失败:\n{e}")
        print("\n请检查.env文件并确保所有必要的配置项都已设置")
        raise

    print("\n" + "="*60)
    print("📚 API文档: http://localhost:8000/docs")
    print("📖 ReDoc文档: http://localhost:8000/redoc")
    print("="*60 + "\n")


@app.on_event("shutdown")
async def shutdown_event():
    """shutdown 钩子：服务器收到 SIGTERM/SIGINT 时执行"""
    print("\n" + "="*60)
    print("👋 应用正在关闭...")
    print("="*60 + "\n")


# ============================================================
# 5. 兜底端点 — 不走 /api 前缀
# ============================================================

@app.get("/")
async def root():
    """根路径：返回应用基本信息"""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "status": "running",
        "docs": "/docs",
        "redoc": "/redoc"
    }


@app.get("/health")
async def health():
    """健康检查：供 K8s/Docker/负载均衡器探活"""
    return {
        "status": "healthy",
        "service": settings.app_name,
        "version": settings.app_version
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.api.main:app",
        host=settings.host,
        port=settings.port,
        reload=True
    )

