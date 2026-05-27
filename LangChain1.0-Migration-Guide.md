# LangChain 1.0 迁移指南：从 HelloAgents 到 LangChain 1.0

## 目录

1. [前置知识：两个框架的核心差异](#1-前置知识两个框架的核心差异)
2. [迁移总览：改什么、不改什么](#2-迁移总览改什么不改什么)
3. [第一步：替换依赖](#3-第一步替换依赖)
4. [第二步：改造配置模块 config.py](#4-第二步改造配置模块-configpy)
5. [第三步：改造 LLM 服务 llm_service.py](#5-第三步改造-llm-服务-llm_servicepy)
6. [第四步：改造 MCP 工具 amap_service.py](#6-第四步改造-mcp-工具-amap_servicepy)
7. [第五步：重写 Agent 核心 trip_planner_agent.py](#7-第五步重写-agent-核心-trip_planner_agentpy)
8. [第六步：让 API 路由支持异步](#8-第六步让-api-路由支持异步)
9. [第七步：安装依赖并验证](#9-第七步安装依赖并验证)

---

## 1. 前置知识：两个框架的核心差异

### 1.1 当前项目用什么？怎么工作的？

你的项目现在用的是 **hello-agents**，一个封装了 LLM 调用和 Agent 逻辑的框架。核心概念有三个：

```
HelloAgentsLLM          →  封装了 OpenAI 兼容的大模型调用
SimpleAgent             →  一个"智能体"，有名字、有提示词、能调工具
MCPTool                 →  把 MCP 服务器（高德地图）包装成 Agent 可用的工具
```

**最关键的问题**：当前 Agent 是怎么调用工具的？

看 [trip_planner_agent.py](backend/app/agents/trip_planner_agent.py) 的提示词：

```python
# 当前做法：在提示词里教 LLM 拼字符串来"模拟"工具调用
ATTRACTION_AGENT_PROMPT = """
使用maps_text_search工具时,必须严格按照以下格式:
`[TOOL_CALL:amap_maps_text_search:keywords=景点关键词,city=城市名]`

示例:
用户: "搜索北京的历史文化景点"
你的回复: [TOOL_CALL:amap_maps_text_search:keywords=历史文化,city=北京]
"""
```

这是**文本格式的假 tool calling**——让 LLM 按照固定字符串格式输出，然后 hello-agents 框架解析这个字符串去真正调用工具。这种方式有两个问题：
- LLM 可能拼错格式，导致工具调用失败
- 浪费 token（提示词里大量篇幅在教格式）

### 1.2 LangChain 1.0 怎么做？

LangChain 1.0 使用**原生 function calling**——OpenAI/兼容接口本身就支持工具调用的结构化输出。LLM 不会输出文本格式的 `[TOOL_CALL:...]`，而是返回一个结构化的 `tool_calls` 对象。

```
HelloAgents 的做法：
  LLM 输出文本 "[TOOL_CALL:amap_maps_text_search:keywords=故宫,city=北京]"
  → 框架解析文本 → 提取工具名和参数 → 调用 MCP 工具

LangChain 1.0 的做法：
  LLM 直接返回 tool_calls: [{"name": "maps_text_search", "args": {"keywords": "故宫", "city": "北京"}}]
  → 框架自动调用工具 → 结果返回给 LLM → LLM 生成最终回复
```

### 1.3 核心概念对照表

| 概念 | HelloAgents | LangChain 1.0 |
|------|-------------|---------------|
| 大模型 | `HelloAgentsLLM()` | `ChatOpenAI(model, api_key, base_url)` |
| 智能体 | `SimpleAgent(name, llm, prompt)` | `create_agent(model, tools, system_prompt)` |
| 给 Agent 加工具 | `agent.add_tool(tool)` | `create_agent(model, tools=[t1, t2])` |
| MCP 工具 | `MCPTool(name, command, env)` | `MultiServerMCPClient({...}).get_tools()` |
| 运行 Agent | `agent.run("查询")` → 字符串 | `agent.invoke({"messages": [...]})` → 消息列表 |
| 工具调用方式 | 文本格式 `[TOOL_CALL:...]` | 原生 function calling |

---

## 2. 迁移总览：改什么、不改什么

### 2.1 需要改的文件（5个）

| 文件 | 改动程度 | 说明 |
|------|----------|------|
| `backend/requirements.txt` | 小改 | 换依赖包名 |
| `backend/app/config.py` | 小改 | 字段改名、删几行无用代码 |
| `backend/app/services/llm_service.py` | 中改 | 换一个类，接口差不多 |
| `backend/app/services/amap_service.py` | 中改 | MCP 客户端换库 |
| `backend/app/agents/trip_planner_agent.py` | **大改** | 整个 Agent 层重写 |

### 2.2 完全不需要改的部分

| 文件/目录 | 原因 |
|-----------|------|
| `backend/app/api/main.py` | FastAPI 应用工厂，跟 Agent 框架无关 |
| `backend/app/api/routes/trip.py` | 只需加一个 `await`（最后一步） |
| `backend/app/api/routes/poi.py` | 保持不变 |
| `backend/app/api/routes/map.py` | 保持不变 |
| `backend/app/models/schemas.py` | Pydantic 模型，跟框架无关 |
| `backend/app/services/unsplash_service.py` | 纯 HTTP 调用，不依赖任何 Agent 框架 |
| `backend/run.py` | uvicorn 启动，跟框架无关 |
| `frontend/` 整个目录 | 前端只调 HTTP API，后端怎么实现它不关心 |

### 2.3 迁移顺序

改动是有依赖关系的，必须按这个顺序来：

```
requirements.txt  →  config.py  →  llm_service.py  →  amap_service.py  →  trip_planner_agent.py  →  trip.py
     (1)               (2)             (3)                 (4)                     (5)                   (6)
```

---

## 3. 第一步：替换依赖

### 学什么？

Python 项目的依赖在 `requirements.txt` 里声明。我们要把 hello-agents 的包换成 LangChain 系列的包。

### 改什么？

**文件**：[backend/requirements.txt](backend/requirements.txt)

**删除这几行**：
```
hello-agents[protocols]>=0.2.4,<=0.2.9   ← 旧框架
fastmcp>=2.0.0                            ← hello-agents 的 MCP 依赖，不再需要
```

**新增这几行**：
```txt
# LangChain 1.0 框架
langchain>=1.0.0                # LangChain 核心（包含 create_agent）
langchain-openai>=1.0.0         # OpenAI 兼容的 Chat 模型
langchain-mcp-adapters>=0.2.0   # MCP 工具适配器（把 MCP 服务器变成 LangChain 工具）
```

**最终文件**将是：
```txt
# LangChain 1.0 框架
langchain>=1.0.0
langchain-openai>=1.0.0
langchain-mcp-adapters>=0.2.0

# FastAPI和相关依赖
fastapi>=0.115.0
uvicorn[standard]>=0.32.0
pydantic>=2.0.0
pydantic-settings>=2.0.0

# HTTP客户端
httpx>=0.27.0
aiohttp>=3.10.0

# 环境变量管理
python-dotenv>=1.0.0

# CORS支持
python-multipart>=0.0.9

# 日志
loguru>=0.7.0

# 其他工具
python-dateutil>=2.8.2
```

### 为什么这样改？

- `langchain` 是核心包，包含 `create_agent`——LangChain 1.0 创建 Agent 的唯一标准入口
- `langchain-openai` 提供 `ChatOpenAI`，兼容所有 OpenAI 接口的大模型（包括国内代理）
- `langchain-mcp-adapters` 提供 `MultiServerMCPClient`，取代原来的 `MCPTool`
- `fastmcp` 删掉是因为 `langchain-mcp-adapters` 内部已经处理了 MCP 协议

---

## 4. 第二步：改造配置模块 config.py

### 学什么？

配置模块负责从 `.env` 文件和环境变量读取配置。现在需要把字段名改得跟 LangChain 的习惯一致，并删除 hello-agents 特有的代码。

### 当前代码的问题

看 [config.py](backend/app/config.py) 当前代码：

```python
# 第 10-13 行：这段是专门加载 HelloAgents 目录下的 .env 的，现在不需要了
helloagents_env = Path(__file__).parent.parent.parent.parent / "HelloAgents" / ".env"
if helloagents_env.exists():
    load_dotenv(helloagents_env, override=False)

# 第 43-45 行：字段名叫 openai_xxx，但 .env 里实际用的是 LLM_ 前缀
openai_api_key: str = ""
openai_base_url: str = "https://api.openai.com/v1"
openai_model: str = "gpt-4"
```

### 改什么？

**文件**：[backend/app/config.py](backend/app/config.py)

**改动 1**：删除 HelloAgents 的 .env 加载（第 10-13 行）

删掉这几行：
```python
helloagents_env = Path(__file__).parent.parent.parent.parent / "HelloAgents" / ".env"
if helloagents_env.exists():
    load_dotenv(helloagents_env, override=False)
```

**改动 2**：重命名 LLM 配置字段（第 42-45 行附近）

```python
# 改前
openai_api_key: str = ""
openai_base_url: str = "https://api.openai.com/v1"
openai_model: str = "gpt-4"

# 改后
llm_api_key: str = ""
llm_base_url: str = "https://api.openai.com/v1"
llm_model: str = "gpt-4"
```

**为什么改名？** 因为你的 `.env.example` 里用的是 `LLM_API_KEY`、`LLM_BASE_URL`、`LLM_MODEL_ID`。pydantic-settings 的 `BaseSettings` 会自动匹配环境变量名（不区分大小写），`llm_api_key` 字段会自动匹配到环境变量 `LLM_API_KEY`。现在名字一致了，更清晰。

**改动 3**：删除 `unsplash_secret_key`（第 41 行）

```python
# 删掉这行，因为代码里从没用过
unsplash_secret_key: str = ""
```

**改动 4**：更新 `validate_config()` 函数

```python
# 改前
llm_api_key = os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY")

# 改后：直接用 settings 的属性
if not settings.llm_api_key:
    warnings.append("LLM_API_KEY未配置,LLM功能可能无法使用")
```

**改动 5**：更新 `print_config()` 函数

```python
# 改前
llm_api_key = os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY")
llm_base_url = os.getenv("LLM_BASE_URL") or settings.openai_base_url
llm_model = os.getenv("LLM_MODEL_ID") or settings.openai_model

# 改后：直接用 settings 的属性
print(f"LLM API Key: {'已配置' if settings.llm_api_key else '未配置'}")
print(f"LLM Base URL: {settings.llm_base_url}")
print(f"LLM Model: {settings.llm_model}")
```

### 为什么这样改？

`BaseSettings` 在创建时已经自动从环境变量和 `.env` 文件加载了所有值到字段上。`validate_config()` 和 `print_config()` 里用 `os.getenv()` 重复读环境变量是多余的，直接用 `settings.字段名` 就行。

---

## 5. 第三步：改造 LLM 服务 llm_service.py

### 学什么？

把 `HelloAgentsLLM` 换成 `ChatOpenAI`。两者都是对 OpenAI 兼容接口的封装，只是包名和初始化方式不同。

### 当前代码

[llm_service.py](backend/app/services/llm_service.py) 当前只有 37 行，逻辑很简单：

```python
from hello_agents import HelloAgentsLLM

def get_llm() -> HelloAgentsLLM:
    _llm_instance = HelloAgentsLLM()   # 自动从环境变量读配置
    return _llm_instance
```

### 改什么？

**文件**：[backend/app/services/llm_service.py](backend/app/services/llm_service.py)

**新代码**：

```python
"""LLM服务模块 — 基于LangChain 1.0的ChatOpenAI"""
from langchain_openai import ChatOpenAI
from ..config import get_settings

_llm_instance = None

def get_llm() -> ChatOpenAI:
    """获取LLM实例（单例模式）"""
    global _llm_instance

    if _llm_instance is None:
        settings = get_settings()
        _llm_instance = ChatOpenAI(
            model=settings.llm_model,
            api_key=settings.llm_api_key,
            base_url=settings.llm_base_url,
            temperature=0.7,
        )

    return _llm_instance

def reset_llm():
    """重置LLM实例（用于测试或重新配置）"""
    global _llm_instance
    _llm_instance = None
```

### 为什么这样改？

- `ChatOpenAI` 是 LangChain 官方提供的 OpenAI 兼容 Chat 模型类
- 参数几乎一样：`model`、`api_key`、`base_url`、`temperature`
- 单例模式保持不变——整个应用共用一个 LLM 实例
- `ChatOpenAI` 支持 `.bind_tools()`——这是 LangChain 实现 function calling 的基础

### 对比

| 对比项 | HelloAgentsLLM | ChatOpenAI |
|--------|---------------|------------|
| 导入 | `from hello_agents import HelloAgentsLLM` | `from langchain_openai import ChatOpenAI` |
| 创建 | `HelloAgentsLLM()` | `ChatOpenAI(model=..., api_key=..., base_url=...)` |
| 配置方式 | 自动读环境变量 | 显式传参（更可控） |
| tool calling | 不支持原生 | 支持 `.bind_tools()` |

---

## 6. 第四步：改造 MCP 工具 amap_service.py

### 学什么？

这是最关键的概念变化。当前项目用 `MCPTool` 创建 MCP 客户端，返回的是一个 hello-agents 格式的工具。LangChain 1.0 用 `MultiServerMCPClient`，返回的是 LangChain 格式的 `BaseTool` 实例，可以直接传给 `create_agent`。

### 两个 API 的对比

```python
# === 旧：HelloAgents ===
from hello_agents.tools import MCPTool

tool = MCPTool(
    name="amap",                        # 工具名称
    description="高德地图服务",           # 描述
    server_command=["uvx", "amap-mcp-server"],  # 如何启动 MCP 服务器
    env={"AMAP_MAPS_API_KEY": key},     # 传给服务器的环境变量
    auto_expand=True                    # 自动展开为多个工具
)
# tool 是一个 MCPTool 实例，需要用 agent.add_tool(tool) 加到 Agent 上

# === 新：LangChain 1.0 ===
from langchain_mcp_adapters.client import MultiServerMCPClient

client = MultiServerMCPClient({
    "amap": {                                          # 服务器别名
        "command": "uvx",                              # 启动命令
        "args": ["amap-mcp-server"],                   # 命令参数（替代了旧版的 server_command）
        "transport": "stdio",                          # 通信方式：标准输入输出
        "env": {"AMAP_MAPS_API_KEY": key}              # 环境变量
    }
})
tools = await client.get_tools()   # 返回 LangChain BaseTool 列表
# tools 可以直接传给 create_agent(tools=tools)
```

### 关键区别

1. **旧 API 是同步的**，`MCPTool(...)` 创建时就完成 MCP 握手
2. **新 API 是异步的**，`await client.get_tools()` 才能拿到工具列表
3. 旧版 `auto_expand=True` 把所有工具展开；新版默认就是展开的
4. 新版返回的是标准 LangChain `BaseTool`，不需要任何转换

### 当前代码结构

[amap_service.py](backend/app/services/amap_service.py) 当前有 270 行，包含：
- `get_amap_mcp_tool()` 函数——创建 MCPTool 单例
- `AmapService` 类——封装了 `search_poi()`、`get_weather()`、`plan_route()` 等方法
- 每个方法内部都手动拼装工具调用参数

**问题**：当前 `AmapService` 类的大部分方法都返回空列表或空字典（因为解析 MCP 返回结果的逻辑是 TODO 状态）。而且用 LangChain 1.0 后，工具调用由 `create_agent` 自动处理，不需要手动拼参数。

### 改什么？

**文件**：[backend/app/services/amap_service.py](backend/app/services/amap_service.py)

**策略**：简化！不再需要手动封装每个 MCP 工具调用。只需要一个函数，返回工具列表。

**新代码**：

```python
"""高德地图MCP服务 — 基于langchain-mcp-adapters"""
from langchain_mcp_adapters.client import MultiServerMCPClient
from ..config import get_settings

# 全局单例
_amap_tools = None
_client = None

async def get_amap_tools():
    """
    获取高德地图MCP工具列表（单例模式）。

    返回的是 LangChain BaseTool 列表，可以直接传给 create_agent(tools=...)。

    注意：这是一个 async 函数，因为 MultiServerMCPClient.get_tools() 是异步的。
    """
    global _amap_tools, _client

    if _amap_tools is None:
        settings = get_settings()

        if not settings.amap_api_key:
            raise ValueError("高德地图API Key未配置,请在.env文件中设置AMAP_API_KEY")

        _client = MultiServerMCPClient({
            "amap": {
                "command": "uvx",
                "args": ["amap-mcp-server"],
                "transport": "stdio",
                "env": {"AMAP_MAPS_API_KEY": settings.amap_api_key}
            }
        })
        _amap_tools = await _client.get_tools()

        print(f"✅ 高德地图MCP工具初始化成功")
        print(f"   工具数量: {len(_amap_tools)}")
        for tool in _amap_tools:
            print(f"   - {tool.name}: {tool.description}")

    return _amap_tools
```

**删掉的内容**：`AmapService` 类、`get_amap_service()` 函数、所有手动拼参数的方法（`search_poi`、`get_weather`、`plan_route` 等）。

### 为什么可以删掉 AmapService？

在 LangChain 1.0 的 `create_agent` 中，工具调用是自动的：

```
用户: "搜索北京的景点"
  → create_agent 把 maps_text_search 工具的 schema 发给 LLM
  → LLM 返回 tool_call: {name: "maps_text_search", args: {keywords: "景点", city: "北京"}}
  → create_agent 自动调用工具，拿到结果
  → 结果返回给 LLM，LLM 生成最终回复
```

整个过程不需要你手动拼参数、手动解析返回值。所以你不需要 `AmapService` 那个中间层了。

### 你可能会问：那 poi.py 和 map.py 的路由怎么办？

这两个文件（[poi.py](backend/app/api/routes/poi.py) 和 [map.py](backend/app/api/routes/map.py)）引用了 `get_amap_service()`。有两个处理方式：

**方案 A（推荐）**：先让这两个路由暂时不可用（它们本来 return 的就是空数据），等 Agent 层迁移完再重构。

**方案 B**：在 amap_service.py 里保留一个简化版的 `AmapService`。

我建议**方案 A**——因为这两个路由的核心逻辑（解析 MCP 结果）本来就是 TODO 状态，先专注于把 Agent 层迁移过去。

---

## 7. 第五步：重写 Agent 核心 trip_planner_agent.py

### 学什么？

这是最大的变化。当前代码用 4 个 `SimpleAgent` + 文本格式的工具调用。LangChain 1.0 用 `create_agent` + 原生 function calling。

### 7.1 先理解当前代码的结构

[ttrip_planner_agent.py](backend/app/agents/trip_planner_agent.py) 的核心流程：

```
plan_trip(request)
  │
  ├─ 步骤1: attraction_agent.run(查询)
  │    └─ LLM 输出: "[TOOL_CALL:amap_maps_text_search:keywords=历史文化,city=北京]"
  │    └─ hello-agents 解析 → 调用 MCP → 把结果返回给 LLM
  │    └─ LLM 生成最终文本回复
  │
  ├─ 步骤2: weather_agent.run(查询)
  │    └─ 同上流程
  │
  ├─ 步骤3: hotel_agent.run(查询)
  │    └─ 同上流程
  │
  └─ 步骤4: planner_agent.run(汇总查询)
       └─ LLM 生成 JSON 格式的旅行计划
       └─ _parse_response() 提取 JSON → TripPlan
```

### 7.2 LangChain 1.0 的新流程

```
async plan_trip(request)
  │
  ├─ 步骤1: await attraction_agent.ainvoke({"messages": [查询]})
  │    └─ create_agent 自动完成：发工具 schema → LLM → 调 MCP → 回传结果 → LLM 回复
  │    └─ 从 result["messages"][-1].content 提取文本
  │
  ├─ 步骤2: await weather_agent.ainvoke({"messages": [查询]})
  │
  ├─ 步骤3: await hotel_agent.ainvoke({"messages": [查询]})
  │
  └─ 步骤4: await planner_agent.ainvoke({"messages": [汇总查询]})
       └─ 解析 JSON → TripPlan
```

### 7.3 create_agent 的工作原理

```python
from langchain.agents import create_agent
from langchain_core.messages import HumanMessage

# 1. 创建一个 Agent
agent = create_agent(
    model=llm,                       # ChatOpenAI 实例
    tools=amap_tools,                # MCP 工具列表
    system_prompt="你是景点搜索专家"   # 系统提示词（替代旧的 system_prompt 参数）
)

# 2. 调用 Agent（异步）
result = await agent.ainvoke({
    "messages": [
        HumanMessage(content="搜索北京的景点")
    ]
})

# 3. 提取结果
# result 是一个字典，包含完整的消息历史
# result["messages"] 是一个消息列表：
#   [HumanMessage, AIMessage(tool_calls), ToolMessage, AIMessage(content="最终回复")]
# 最后一条 AI 消息就是最终回复
final_answer = result["messages"][-1].content
```

### 7.4 提示词的变化

**旧提示词**（大量篇幅教 LLM 拼 TOOL_CALL 格式）：
```python
ATTRACTION_AGENT_PROMPT = """你是景点搜索专家。

**重要提示:**
你必须使用工具来搜索景点!不要自己编造景点信息!

**工具调用格式:**
使用maps_text_search工具时,必须严格按照以下格式:
`[TOOL_CALL:amap_maps_text_search:keywords=景点关键词,city=城市名]`

**示例:**
用户: "搜索北京的历史文化景点"
你的回复: [TOOL_CALL:amap_maps_text_search:keywords=历史文化,city=北京]
...
"""
```

**新提示词**（简洁，原生 function calling 不需要教格式）：
```python
ATTRACTION_AGENT_PROMPT = """你是景点搜索专家。你的任务是根据城市和用户偏好搜索合适的景点。

规则：
1. 使用工具搜索景点，不要编造信息
2. 返回景点名称、地址、坐标、类别和简要描述
3. 根据用户偏好筛选合适的景点
"""
```

### 7.5 新的完整代码

```python
"""多智能体旅行规划系统 — 基于LangChain 1.0"""
import json
from typing import Dict, Any
from langchain.agents import create_agent
from langchain_core.messages import HumanMessage
from ..services.llm_service import get_llm
from ..services.amap_service import get_amap_tools
from ..models.schemas import TripRequest, TripPlan, DayPlan, Attraction, Meal, Location, Hotel
from ..config import get_settings

# ============ Agent提示词（简化版，无需 TOOL_CALL 格式） ============

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

    async def _run_agent(self, agent, query: str) -> str:
        """
        运行一个Agent并返回文本结果。

        LangChain 的 agent.invoke() 返回完整的消息历史，
        我们只需要最后一条 AI 消息的文本内容。
        """
        result = await agent.ainvoke({
            "messages": [HumanMessage(content=query)]
        })
        # 从消息历史中提取最后一条 AI 消息
        messages = result["messages"]
        for msg in reversed(messages):
            if hasattr(msg, "content") and msg.content and msg.type == "ai":
                return msg.content
        return ""

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
        """解析Agent响应中的JSON"""
        try:
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

            data = json.loads(json_str)
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



### 7.6 关键变化总结

| 对比点 | 旧代码 | 新代码 |
|--------|--------|--------|
| Agent创建 | 构造函数里同步创建4个SimpleAgent | `_init_agents()` 异步创建（因为MCP工具加载是异步的） |
| 提示词 | 大量 `[TOOL_CALL:...]` 格式说明 | 纯自然语言，不需要教格式 |
| 运行Agent | `agent.run(query)` → 字符串 | `await agent.ainvoke({"messages": [...]})` → 消息列表 |
| 提取结果 | 直接就是字符串 | 需要从 `result["messages"][-1].content` 取 |
| 查询构建 | `_build_attraction_query` 里手动拼 TOOL_CALL | 纯自然语言查询 |
| MCP工具 | 构造函数里同步创建 | 异步加载 `await get_amap_tools()` |

---

## 8. 第六步：让 API 路由支持异步

### 改什么？

**文件**：[backend/app/api/routes/trip.py](backend/app/api/routes/trip.py)

只有一行变化——在 `plan_trip` 函数里给 `agent.plan_trip(request)` 加上 `await`：

```python
# 改前（第 59 行）
trip_plan = agent.plan_trip(request)

# 改后
trip_plan = await agent.plan_trip(request)
```

因为 `MultiAgentTripPlanner.plan_trip()` 现在是 `async def`，调用方必须 `await`。FastAPI 原生支持 async 路由，所以不需要其他改动。

---

## 9. 第七步：安装依赖并验证

### 9.1 安装新依赖

```bash
cd backend
source .venv/bin/activate

# 卸载旧框架
pip uninstall hello-agents fastmcp -y

# 安装 LangChain 1.0
pip install "langchain>=1.0.0" "langchain-openai>=1.0.0" "langchain-mcp-adapters>=0.2.0"
```

### 9.2 验证步骤

**验证 1：导入检查**
```bash
python -c "from langchain.agents import create_agent; from langchain_openai import ChatOpenAI; print('✅ LangChain 1.0 导入成功')"
```

**验证 2：配置检查**
```bash
python -c "from app.config import get_settings; s = get_settings(); print(f'Model: {s.llm_model}'); print(f'Base URL: {s.llm_base_url}')"
```

**验证 3：LLM 连接检查**
```bash
python -c "
from app.services.llm_service import get_llm
llm = get_llm()
print(f'✅ LLM 初始化成功: {llm.model_name}')
"
```

**验证 4：MCP 工具加载检查**
```bash
python -c "
import asyncio
from app.services.amap_service import get_amap_tools

async def test():
    tools = await get_amap_tools()
    print(f'✅ MCP工具加载成功, 共 {len(tools)} 个工具')
    for t in tools:
        print(f'   - {t.name}')

asyncio.run(test())
"
```

**验证 5：启动服务端到端测试**
```bash
# 终端1：启动后端
cd backend && python run.py

# 终端2：发一个测试请求
curl -X POST http://localhost:8000/api/trip/plan \
  -H "Content-Type: application/json" \
  -d '{
    "city": "北京",
    "start_date": "2025-06-01",
    "end_date": "2025-06-03",
    "travel_days": 3,
    "transportation": "公共交通",
    "accommodation": "经济型酒店",
    "preferences": ["历史文化"]
  }'
```

---

## 总结

整个迁移的核心思路就是一句话：**把文本格式的假 tool calling 换成 LangChain 的原生 function calling**。

```
改前：LLM → 输出文本 "TOOL_CALL:xxx" → 框架解析文本 → 调工具
改后：LLM → 输出结构化 tool_calls → 框架自动调工具
```

迁移过程中 **FastAPI 路由、Pydantic 模型、前端、Unsplash 服务完全不动**——它们跟 Agent 框架没有直接依赖关系。
