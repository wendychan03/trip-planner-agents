

"""高德地图MCP服务 — 基于langchain-mcp-adapters"""
from langchain_mcp_adapters.client import MultiServerMCPClient
from ..config import get_settings

# 全局单例
_amap_tools = None
_client = None

async def get_amap_tools():
    """
    获取高德地图MCP工具列表 单例模式 。

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
                "env": {
                    "AMAP_MAPS_API_KEY": settings.amap_api_key,
                    "LOG_LEVEL": "ERROR",            # 抑制调试输出，避免污染stdout
                    "PYTHONUNBUFFERED": "1",         # 禁用Python输出缓冲
                },
            }
        })
        _amap_tools = await _client.get_tools() # 返回 LangChain BaseTool 列表
        # tools 可以直接传给 create_agent(tools=tools)

        print(f"✅ 高德地图MCP工具初始化成功")
        print(f"   工具数量: {len(_amap_tools)}")
        for tool in _amap_tools:
            print(f"   - {tool.name}: {tool.description}")

    return _amap_tools

# **删掉的内容**：`AmapService` 类、`get_amap_service()` 函数、所有手动拼参数的方法（`search_poi`、`get_weather`、`plan_route` 等）。

# ### 为什么可以删掉 AmapService？

# 在 LangChain 1.0 的 `create_agent` 中，工具调用是自动的：

# ```
# 用户: "搜索北京的景点"
#   → create_agent 把 maps_text_search 工具的 schema 发给 LLM
#   → LLM 返回 tool_call: {name: "maps_text_search", args: {keywords: "景点", city: "北京"}}
#   → create_agent 自动调用工具，拿到结果
#   → 结果返回给 LLM，LLM 生成最终回复
# ```

# 整个过程不需要你不再需要手动封装每个 MCP 工具调用、手动拼参数、手动解析返回值。所以你不需要 `AmapService` 那个中间层了。


# class AmapService:
#     """高德地图服务封装类"""
    
#     def __init__(self):
#         """初始化服务"""
#         self.mcp_tool = get_amap_mcp_tool()
    
#     def search_poi(self, keywords: str, city: str, citylimit: bool = True) -> List[POIInfo]:
#         """
#         搜索POI
        
#         Args:
#             keywords: 搜索关键词
#             city: 城市
#             citylimit: 是否限制在城市范围内
            
#         Returns:
#             POI信息列表
#         """
#         try:
#             # 调用MCP工具
#             result = self.mcp_tool.run({
#                 "action": "call_tool",
#                 "tool_name": "maps_text_search",
#                 "arguments": {
#                     "keywords": keywords,
#                     "city": city,
#                     "citylimit": str(citylimit).lower()
#                 }
#             })
            
#             # 解析结果
#             # 注意: MCP工具返回的是字符串,需要解析
#             # 这里简化处理,实际应该解析JSON
#             print(f"POI搜索结果: {result[:200]}...")  # 打印前200字符
            
#             # TODO: 解析实际的POI数据
#             return []
            
#         except Exception as e:
#             print(f"❌ POI搜索失败: {str(e)}")
#             return []
    
#     def get_weather(self, city: str) -> List[WeatherInfo]:
#         """
#         查询天气
        
#         Args:
#             city: 城市名称
            
#         Returns:
#             天气信息列表
#         """
#         try:
#             # 调用MCP工具
#             result = self.mcp_tool.run({
#                 "action": "call_tool",
#                 "tool_name": "maps_weather",
#                 "arguments": {
#                     "city": city
#                 }
#             })
            
#             print(f"天气查询结果: {result[:200]}...")
            
#             # TODO: 解析实际的天气数据
#             return []
            
#         except Exception as e:
#             print(f"❌ 天气查询失败: {str(e)}")
#             return []
    
#     def plan_route(
#         self,
#         origin_address: str,
#         destination_address: str,
#         origin_city: Optional[str] = None,
#         destination_city: Optional[str] = None,
#         route_type: str = "walking"
#     ) -> Dict[str, Any]:
#         """
#         规划路线
        
#         Args:
#             origin_address: 起点地址
#             destination_address: 终点地址
#             origin_city: 起点城市
#             destination_city: 终点城市
#             route_type: 路线类型 (walking/driving/transit)
            
#         Returns:
#             路线信息
#         """
#         try:
#             # 根据路线类型选择工具
#             tool_map = {
#                 "walking": "maps_direction_walking_by_address",
#                 "driving": "maps_direction_driving_by_address",
#                 "transit": "maps_direction_transit_integrated_by_address"
#             }
            
#             tool_name = tool_map.get(route_type, "maps_direction_walking_by_address")
            
#             # 构建参数
#             arguments = {
#                 "origin_address": origin_address,
#                 "destination_address": destination_address
#             }
            
#             # 公共交通需要城市参数
#             if route_type == "transit":
#                 if origin_city:
#                     arguments["origin_city"] = origin_city
#                 if destination_city:
#                     arguments["destination_city"] = destination_city
#             else:
#                 # 其他路线类型也可以提供城市参数提高准确性
#                 if origin_city:
#                     arguments["origin_city"] = origin_city
#                 if destination_city:
#                     arguments["destination_city"] = destination_city
            
#             # 调用MCP工具
#             result = self.mcp_tool.run({
#                 "action": "call_tool",
#                 "tool_name": tool_name,
#                 "arguments": arguments
#             })
            
#             print(f"路线规划结果: {result[:200]}...")
            
#             # TODO: 解析实际的路线数据
#             return {}
            
#         except Exception as e:
#             print(f"❌ 路线规划失败: {str(e)}")
#             return {}
    
#     def geocode(self, address: str, city: Optional[str] = None) -> Optional[Location]:
#         """
#         地理编码(地址转坐标)

#         Args:
#             address: 地址
#             city: 城市

#         Returns:
#             经纬度坐标
#         """
#         try:
#             arguments = {"address": address}
#             if city:
#                 arguments["city"] = city

#             result = self.mcp_tool.run({
#                 "action": "call_tool",
#                 "tool_name": "maps_geo",
#                 "arguments": arguments
#             })

#             print(f"地理编码结果: {result[:200]}...")

#             # TODO: 解析实际的坐标数据
#             return None

#         except Exception as e:
#             print(f"❌ 地理编码失败: {str(e)}")
#             return None

#     def get_poi_detail(self, poi_id: str) -> Dict[str, Any]:
#         """
#         获取POI详情

#         Args:
#             poi_id: POI ID

#         Returns:
#             POI详情信息
#         """
#         try:
#             result = self.mcp_tool.run({
#                 "action": "call_tool",
#                 "tool_name": "maps_search_detail",
#                 "arguments": {
#                     "id": poi_id
#                 }
#             })

#             print(f"POI详情结果: {result[:200]}...")

#             # 解析结果并提取图片
#             import json
#             import re

#             # 尝试从结果中提取JSON
#             json_match = re.search(r'\{.*\}', result, re.DOTALL)
#             if json_match:
#                 data = json.loads(json_match.group())
#                 return data

#             return {"raw": result}

#         except Exception as e:
#             print(f"❌ 获取POI详情失败: {str(e)}")
#             return {}


# # 创建全局服务实例
# _amap_service = None


# def get_amap_service() -> AmapService:
#     """获取高德地图服务实例(单例模式)"""
#     global _amap_service
    
#     if _amap_service is None:
#         _amap_service = AmapService()
    
#     return _amap_service

