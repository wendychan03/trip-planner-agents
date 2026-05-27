"""LLM服务模块 — 基于LangChain 1.0的ChatOpenAI"""
from langchain_openai import ChatOpenAI
# from hello_agents import HelloAgentsLLM
from ..config import get_settings


# 全局LLM实例
_llm_instance = None


def get_llm() ->  ChatOpenAI:
    """
    获取LLM实例(单例模式)
    
    Returns:
        整个应用共用一个 LLM 实例
    """
    global _llm_instance
    
    if _llm_instance is None:
        settings = get_settings()
        
        # # HelloAgentsLLM会自动从环境变量读取配置
        # # 包括OPENAI_API_KEY, OPENAI_BASE_URL, OPENAI_MODEL等
        # _llm_instance = HelloAgentsLLM()

        _llm_instance = ChatOpenAI(
            model=settings.llm_model_id,
            api_key=settings.llm_api_key,
            base_url=settings.llm_base_url,
            temperature=0.7,
            extra_body={"thinking": {"type": "disabled"}},  # 关闭DeepSeek思考模式，避免reasoning_content兼容问题
        )       
        
        # print(f"✅ LLM服务初始化成功")
        # print(f"   提供商: {_llm_instance.provider}")
        # print(f"   模型: {_llm_instance.model}")
        print(f"✅ LLM服务初始化成功")
        print(f"   提供商: {type(_llm_instance).__name__}")
        print(f"   模型: {_llm_instance.model_name}")
    
    return _llm_instance


def reset_llm():
    """重置LLM实例(用于测试或重新配置)"""
    global _llm_instance
    _llm_instance = None

