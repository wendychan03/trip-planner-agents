"""启动脚本"""

import uvicorn
from app.config import get_settings # 导入配置读取函数

if __name__ == "__main__":
    settings = get_settings()

    # 用 uvicorn 启动 FastAPI 应用，让它在 settings.host 这个地址的 settings.port 这个端口上等待请求
    uvicorn.run(
        "app.api.main:app",  # 模块路径:FastAPI实例 — 对应 app/api/main.py 里的 app
        host=settings.host,
        port=settings.port,
        reload=True,  # 代码变更时自动重启，生产环境应设为 False
        log_level=settings.log_level.lower()
    )

