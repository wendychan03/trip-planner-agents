# 后端开发学习路线

## 项目概述

FastAPI + HelloAgents 多智能体框架的旅行规划后端。核心架构是 **4 层分层设计**：

- **配置层**（config）—— 所有模块的基础
- **服务层**（services）—— 封装外部能力（LLM、高德地图、Unsplash）
- **路由层**（routes）—— 暴露 REST API 接口
- **智能体层**（agents）—— 多 Agent 协作编排，核心业务逻辑

两条主要调用链：

1. **旅行规划链**：`run.py` → `main.py` 注册路由 → `trip.py` 接收请求 → `trip_planner_agent.py` 编排 4 个 Agent 按顺序执行 → 返回 JSON 计划
2. **地图服务链**：`run.py` → `main.py` 注册路由 → `map.py`/`poi.py` 接收请求 → `amap_service.py` 直接调用 MCP 工具 → 返回结果

---

## 阶段 1：配置管理

**文件**：`backend/app/config.py`

**学习要点**：

- `pydantic-settings` 的 `BaseSettings` 会自动从 `.env` 文件读取配置，字段名和环境变量名自动匹配，不需要手动调用 `os.getenv()`
- 如果字段名和环境变量名不一致，用 `Field(validation_alias=...)` 做映射
- `get_settings()` 是整个项目里被调用最频繁的函数，每个服务模块都通过它获取配置。它同样使用单例模式，保证全局配置一致
- `validate_config()` 在 `main.py` 的 startup 事件里被调用，如果缺少关键 API Key（高德、LLM），直接阻止服务启动。这比运行时才发现缺少配置要好得多
- `get_cors_origins_list()` 负责把逗号分隔的 CORS 字符串拆成列表。CORS 配置非常严格，前端地址必须精确匹配，多一个斜杠都会导致跨域失败

**为什么先学这个**：配置是一切的基础。每一个后续模块的代码里你都会看到 `settings = get_settings()`，先搞清楚有哪些配置项、它们怎么被加载的，后面读代码会顺畅很多。

---

## 阶段 2：FastAPI 应用工厂

**文件**：`backend/app/api/main.py`

**学习要点**：

理解 FastAPI 的组装流程。这个文件是后端的"骨架"，它负责：

- 创建 `FastAPI()` 实例，指定标题、版本、描述（这些会显示在 Swagger 文档顶部）
- 挂载 CORS 中间件。中间件的执行顺序是**倒序**的，所以 CORS 应该最先添加，这样跨域预检请求（OPTIONS）能在任何业务逻辑之前处理掉
- 通过 `app.include_router(router, prefix="/api")` 注册三个业务路由模块。注意路由前缀是**拼接**关系：如果 `trip.py` 的 router 设了 `prefix="/trip"`，这里再设 `prefix="/api"`，最终路径就是 `/api/trip/...`
- startup 事件里只做配置校验和打印横幅，**不要在这里做耗时操作**（比如加载模型或初始化 MCP 连接），否则服务会迟迟起不来，K8s 的 readiness probe 也会超时
- shutdown 事件只做清理通知

`APIRouter` 的分模块设计是关键：每个业务模块（trip、poi、map）有自己独立的 router，在 `main.py` 里统一注册。这样做的好处是新增功能不需要改 `main.py` 的结构，只需要添加一行 `include_router`。

---

## 阶段 3：Pydantic 数据模型

**文件**：`backend/app/models/schemas.py`

**学习要点**：

Pydantic 模型定义了整个后端的数据"契约"。理解以下几点：

- **请求模型和响应模型要分开定义**。比如 `TripRequest` 是前端发过来的入参，`TripPlanResponse` 是后端返回的出参，它们包含的字段完全不同，不要共用
- **嵌套模型**是 Pydantic 的核心能力。`TripPlan` 包含 `List[DayPlan]`，`DayPlan` 又包含 `List[Attraction]`、`List[Meal]`、一个 `Hotel` 对象。这种层层嵌套的结构让 JSON 数据有了类型安全
- `Field(description=...)` 有双重用���：既生成 Swagger 文档的字段说明，也帮助 Agent 在运行时理解每个字段的含义
- 在路由装饰器里声明 `response_model=TripPlanResponse` 后，FastAPI 会自动做三件事：校验输出数据是否符合模型定义、过滤掉模型里没定义的额外字段、为 Swagger 生成完整的响应文档

**注意**：Pydantic v2 和 v1 的 API 不兼容，比如 `schema_extra` 改成了 `json_schema_extra`。这个项目用的是 v2，查文档时要确认版本。

---

## 阶段 4：服务层 —— 外部集成

服务层封装了所有和外部系统打交道的能力，统一使用**单例模式**。单例模式的原因各不相同，但都合理：LLM 连接创建有开销，MCP 子进程启动成本更大，Unsplash 则比较轻量——但为了一致性，三者都用了单例。

### 4a. LLM 服务

**文件**：`backend/app/services/llm_service.py`

- `HelloAgentsLLM()` 会自动从 `os.environ` 读取 `OPENAI_API_KEY`、`OPENAI_BASE_URL`、`OPENAI_MODEL` 等环境变量，不需要手动传参
- `get_llm()` 维护全局唯一的 LLM 实例，所有 Agent 共享同一个连接
- `reset_llm()` 提供重置能力，测试或需要热切换模型时使用

**重点理解**：这个 LLM 实例会被注入到所有 4 个 Agent 中，是每个 Agent 的"大脑"。Agent 的智能程度取决于两个东西：这个 LLM 模型的能力 + system_prompt 的设计质量。

### 4b. 高德地图 MCP 服务

**文件**：`backend/app/services/amap_service.py`

这是整个项目里**最需要花时间理解的模块**，因为它引入了 MCP 协议。

**MCP（模型上下文协议）是什么**：一个标准化的"工具调用协议"。简单说，`amap-mcp-server` 是一个独立的 Python 进程，它封装了高德地图的各种 API。`MCPTool` 通过启动这个子进程，用 stdin/stdout 和它通信，把高德地图的能力（搜索 POI、查天气、规划路线、地理编码）暴露为 Agent 可调用的工具。

**关键设计点**：

- `auto_expand=True` 的作用：`amap-mcp-server` 内部有多个工具（`maps_text_search`、`maps_weather`、`maps_direction_walking_by_address` 等）。`auto_expand=True` 把它们展开为独立工具，Agent 可以按名称直接调用某一个。如果设为 False，就只能把整个 MCP Server 当作一个黑盒工具来用
- **两层单例**：`get_amap_mcp_tool()` 管理 MCP 子进程（启动子进程开销很大，**必须**全局只启动一次），`get_amap_service()` 管理 `AmapService` 对象。第一次调用时完成 MCP 握手（list_tools），后续直接复用
- `plan_route()` 方法里的 `tool_map` 字典是**策略模式**的简单实现：根据 `route_type`（walking/driving/transit）选择不同的 MCP 工具函数，比写一串 if-else 更清晰
- MCP 工具调用统一的格式是 `self.mcp_tool.run({"action": "call_tool", "tool_name": "xxx", "arguments": {...}})`

**当前代码的一个关键待办**：`search_poi`、`get_weather`、`plan_route` 等方法目前只 `print` 了 MCP 返回的原始数据，但**返回的是空列表 `[]` 或空字典 `{}`**。MCP 返回的是 JSON 字符串，需要加上解析逻辑把字符串转成结构化的 Pydantic 对象。这也是你后续可以动手完善的地方。

### 4c. Unsplash 图片服务

**文件**：`backend/app/services/unsplash_service.py`

- 这是最传统的 REST API 调用方式，直接 `requests.get()` 调 Unsplash 的搜索接口
- 和 MCP 方式形成对比：对于简单的外部 API，不需要额外的子进程，直接 HTTP 调用即可
- `poi.py` 路由里做了降级策略：先用 `"{景点名} China landmark"` 搜索，搜不到再用纯景点名搜索

---

## 阶段 5：API 路由层

路由层是 HTTP 请求和业务逻辑之间的桥梁。每个路由文件都是一个独立的 `APIRouter`，有自己的 prefix 和 tags。

### 5a. 旅行规划路由

**文件**：`backend/app/api/routes/trip.py`

**核心流程**（这是整个后端最重要的请求处理链路）：

```
POST /api/trip/plan
  → FastAPI 用 TripRequest 模型校验 JSON body（字段不合法直接返回 422）
  → get_trip_planner_agent() 获取 Agent 单例（首次调用会初始化 4 个 Agent + MCP 连接）
  → agent.plan_trip(request) 执行 4 Agent 协作管道
  → 结果包装成 TripPlanResponse 返回
```

**设计细节**：

- `response_model=TripPlanResponse` 保证了输出格式的自动校验
- 异常处理模式很重要：`try/except` 捕获所有异常 → `traceback.print_exc()` 打印完整堆栈到控制台 → `raise HTTPException(status_code=500)` 返回标准错误给前端。控制台日志给开发者看，HTTP 响应给前端看，两者分离
- `/trip/health` 端点检查 Agent 是否可用 + 工具数量，返回 503 如果 Agent 不可用，供容器编排系统做健康探测

### 5b. 地图和 POI 路由

**文件**：`backend/app/api/routes/map.py`、`backend/app/api/routes/poi.py`

这些路由**不经过 Agent 层**，直接调用 `AmapService` 的方法。为什么？因为它们只做单一的数据查询（搜一个 POI、查一下天气），不需要 LLM 参与理解和整合，Agent 层在此就是过度设计。

- Query 参数通过 `Query(..., description="...")` 声明，`...` 表示必填
- 和 trip 路由不同的地方：map/poi 路由在 `@router.get/post` 上没有声明全局 `response_model`（poi.py 有些端点返回的是动态 dict），灵活性更高但文档和校验更弱

---

## 阶段 6：多智能体编排 —— 核心大脑

**文件**：`backend/app/agents/trip_planner_agent.py`

这是整个后端**最有价值的代码**，也是你需要投入最多时间理解的部分。

### 6a. 4 Agent 管道的设计思路

旅行规划是一个**需要多种能力协作**的任务，所以而不是让一个 Agent 做所有事，而是把任务拆给了 4 个专家 Agent：

```
景点搜索 Agent（有 MCP 工具） → 天气查询 Agent（有 MCP 工具）
    → 酒店推荐 Agent（有 MCP 工具） → 行程规划 Agent（纯 LLM，无工具）
```

- **前 3 个 Agent** 配有 MCP 工具（高德地图搜索/天气），负责从外部获取真实数据
- **第 4 个 Agent** 不配任何工具，只负责把前 3 个的结果整合成结构化的 JSON 旅行计划
- 这种"工具 Agent + 思考 Agent"的分工模式在 Agent 开发中非常常见

数据流是链式的：前 3 个 Agent 的输出文本作为第 4 个 Agent 的输入（通过 `_build_planner_query` 方法拼接成一段完整的 prompt）。

### 6b. system_prompt 设计

每个 Agent 的 system_prompt 都遵循相同的结构：**角色定义 + 工具调用格式 + 具体示例 + 约束条件**。

为什么每个 Agent 的 prompt 都要包含工具调用示例？因为 LLM 的"格式跟随"能力很强：给它一个具体的调用格式模板，它就会按模板输出。示例越接近实际使用场景，Agent 调用工具的成功率越高。反之，如果只做抽象描述（"请使用工具搜索景点"），LLM 大概率会自由发挥，产生不规范的输出。

Planer Agent 的 prompt 里直接嵌入了完整的 JSON Schema，并加了严格的约束条件（"温度必须是纯数字"、"每天必须包含早中晚三餐"）。这是因为 LLM 生成结构化 JSON 时容易犯三个错误：加注释（JSON 不支持）、用 `°C` 等非数字字符、漏掉必填字段。通过 prompt 约束可以减少这些错误。

### 6c. JSON 解析的容错设计

Agent 的输出是**自由文本**，不是结构化 JSON。`_parse_response()` 方法做了三层提取：

1. 找 ` ```json ``` ` 代码块（最理想的情况）
2. 找 ` ``` ``` ` 通用代码块（LLM 用了代码块但没标语言）
3. 直接找 `{...}` 裸 JSON（LLM 直接输出 JSON，没包代码块）

三层都失败 → 走 fallback。这个渐进降级策略保证了鲁棒性。

### 6d. 容错机制

`_create_fallback_plan()` 是整个系统的"安全网"。当 Agent 调用失败或 JSON 解析失败时，它根据请求里的基本信息（城市、日期、天数）生成一个模板化的旅行计划。虽然内容不丰富，但结构完整、字段齐全，保证了 API 不会返回 500 错误。

**设计原则**：对外接口永远不要因为内部 AI 的不确定性而崩溃。fallback 计划是业务可用性的底线保障。

### 6e. 单例模式

`get_trip_planner_agent()` 通过全局变量确保整个进程只有一份 `MultiAgentTripPlanner` 实例。原因：初始化时需要创建 4 个 Agent + 启动 MCP 子进程 + 配置 LLM，开销很大。如果每个请求都 new 一个，响应时间会非常长。

**但需注意**：单例意味着 Agent 的状态（包括 MCP 连接）在进程生命周期内不会刷新。如果 MCP 子进程挂了，或者需要切换 LLM 模型，目前只能重启服务。

---

## 开发顺序总结

推荐的代码阅读顺序就是上面的 6 个阶段：

```
config.py  →  main.py  →  schemas.py  →  services/*  →  routes/*  →  agents/*
  (配置)       (骨架)       (数据)         (外部能力)      (接口)        (核心逻辑)
```

从外到内，从基础设施到核心逻辑。每个阶段都可以独立运行和测试：

- 读完阶段 1-3，可以启动服务看 Swagger 文档
- 读完阶段 4，可以单独调 map/poi 接口看 MCP 工具的效果
- 读完阶段 5-6，可以调 `/api/trip/plan` 看完整的多 Agent 协作流程

如果你想动手修改代码，建议的优先级：

1. **优先修 `amap_service.py` 里的 TODO**：解析 MCP 返回的 JSON 字符串，填入结构化 Pydantic 对象。这是目前功能上最大的缺口，也是理解 MCP 协议最好的练习
2. **优化 Agent 的 system_prompt**：根据实际运行效果调整提示词，提高 Agent 输出质量
3. **扩展 Agent 管道**：在 4 个 Agent 之外添加新的专家（比如交通规划专家、餐饮推荐专家）
