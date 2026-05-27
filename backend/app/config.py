"""配置管理模块 — 用 pydantic-settings 的 BaseSettings 从 .env 自动加载配置"""

import os
from pathlib import Path
from typing import List
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# # 1. 加载 .env 文件 — 将 KEY=VALUE 注入 os.environ
# load_dotenv()                                                      # 项目自己的 .env
# helloagents_env = Path(__file__).parent.parent.parent.parent / "HelloAgents" / ".env"
# if helloagents_env.exists():
#     load_dotenv(helloagents_env, override=False)                      # 不覆盖已有的，项目 .env 优先级更高


class Settings(BaseSettings):
    """
    BaseSettings 自动匹配环境变量到字段：
    优先级：构造传参 > 系统环境变量 > .env 文件 > 类默认值
    类型自动转换（如 port: int 声明后，str "8000" → int 8000）
    """

    # 应用基本配置
    app_name: str = "LangChain智能旅行助手"
    app_version: str = "1.0.0"
    debug: bool = False

    # 服务器配置 — host: 监听地址，port: 监听端口
    host: str = "0.0.0.0"
    port: int = 8000

    # CORS 跨域 — 允许的前端地址，逗号分隔，运行时拆成列表
    cors_origins: str = "http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173,http://127.0.0.1:3000"

    # 高德地图 API — 用于地理编码、POI 搜索、路线规划
    amap_api_key: str = ""

    # Unsplash API — 用于获取目的地风景图片
    unsplash_access_key: str = ""
    # unsplash_secret_key: str = ""

    # # LLM 大模型配置 — OpenAI 兼容接口
    # openai_api_key: str = ""
    # openai_base_url: str = "https://api.openai.com/v1"     # 可换成国内代理地址
    # openai_model: str = "gpt-4"
    llm_api_key: str = ""
    llm_base_url: str = "https://api.openai.com/v1"
    llm_model_id: str = "gpt-4"


    # 日志级别
    log_level: str = "INFO"

    class Config:
        env_file = ".env"            # 指定从哪个文件读
        case_sensitive = False       # 不区分大小写，OPENAI_API_KEY ↔ openai_api_key
        extra = "ignore"             # 遇到未定义的环境变量不报错，直接忽略

    def get_cors_origins_list(self) -> List[str]:
        """将逗号分隔的字符串拆成列表，供 FastAPI CORS 中间件使用"""
        return [origin.strip() for origin in self.cors_origins.split(',')]


# 2. 全局单例 — 整个应用共享一个配置实例
settings = Settings()


def get_settings() -> Settings:
    """获取配置实例（供 run.py 等处调用）"""
    return settings


def validate_config():
    """启动时校验关键配置是否齐全"""
    errors = []
    warnings = []

    if not settings.amap_api_key:
        errors.append("AMAP_API_KEY未配置")             # 高德地图是核心功能，缺失就报错

    # # 兼容两种命名习惯：LLM_API_KEY 或 OPENAI_API_KEY
    # llm_api_key = os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY")
    # if not llm_api_key:
    #     warnings.append("LLM_API_KEY或OPENAI_API_KEY未配置,LLM功能可能无法使用")
    if not settings.llm_api_key:
        warnings.append("LLM_API_KEY未配置,LLM功能可能无法使用")
    if errors:
        error_msg = "配置错误:\n" + "\n".join(f"  - {e}" for e in errors)
        raise ValueError(error_msg)

    if warnings:
        print("\n⚠️  配置警告:")
        for w in warnings:
            print(f"  - {w}")

    return True


def print_config():
    """打印当前配置（敏感信息只显示已配置/未配置）"""
    print(f"应用名称: {settings.app_name}")
    print(f"版本: {settings.app_version}")
    print(f"服务器: {settings.host}:{settings.port}")
    print(f"高德地图API Key: {'已配置' if settings.amap_api_key else '未配置'}")

    # # LLM 优先读环境变量，其次用类默认值
    # llm_api_key = os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY")
    # llm_base_url = os.getenv("LLM_BASE_URL") or settings.openai_base_url
    # llm_model = os.getenv("LLM_MODEL_ID") or settings.openai_model

    # print(f"LLM API Key: {'已配置' if llm_api_key else '未配置'}")
    # print(f"LLM Base URL: {llm_base_url}")
    # print(f"LLM Model: {llm_model}")
    # print(f"日志级别: {settings.log_level}")

    # 改后：直接用 settings 的属性
    print(f"LLM API Key: {'已配置' if settings.llm_api_key else '未配置'}")
    print(f"LLM Base URL: {settings.llm_base_url}")
    print(f"LLM Model: {settings.llm_model_id}")


### 为什么这样改？
# `BaseSettings` 在创建时已经自动从环境变量和 `.env` 文件加载了所有值到字段上。
# `validate_config()` 和 `print_config()` 里用 `os.getenv()` 重复读环境变量是多余的，直接用 `settings.字段名` 就行。

