"""Unsplash图片服务"""

import requests
from typing import List, Optional
from ..config import get_settings

class UnsplashService:
    """Unsplash图片服务类"""
    
    def __init__(self):
        """初始化服务"""
        settings = get_settings()
        self.access_key = settings.unsplash_access_key
        self.base_url = "https://api.unsplash.com"
    
    def search_photos(self, query: str, per_page: int = 5) -> List[dict]:
        """
        搜索图片 — 直接调用 Unsplash REST API（HTTP GET），不经过 MCP 子进程。
        """
        try:
            url = f"{self.base_url}/search/photos"
            params = {
                "query": query,
                "per_page": per_page,
            }
            headers = {
                "Authorization": f"Client-ID {self.access_key}"
            }

            response = requests.get(url, params=params, headers=headers, timeout=10)
            response.raise_for_status()             # 状态码非 2xx 则抛异常

            data = response.json()
            results = data.get("results", [])       # 取 results 数组，没有则给空列表

            # 3. 只提取需要的 5 个字段，丢掉 likes、tags 等无用数据
            photos = []
            for photo in results:
                photos.append({
                    "id": photo.get("id"),
                    "url": photo.get("urls", {}).get("regular"),
                    "thumb": photo.get("urls", {}).get("thumb"),
                    "description": photo.get("description") or photo.get("alt_description"),
                    "photographer": photo.get("user", {}).get("name")
                })

            return photos

        except Exception as e:
            print(f"❌ Unsplash搜索失败: {str(e)}")
            return []
    
    def get_photo_url(self, query: str) -> Optional[str]:
        """
        获取单张图片URL

        Args:
            query: 搜索关键词

        Returns:
            图片URL
        """
        photos = self.search_photos(query, per_page=1)
        if photos:
            return photos[0].get("url")
        return None


# 全局服务实例
_unsplash_service = None #← import 时只是 None，不创建（0 开销）


def get_unsplash_service() -> UnsplashService:
    """获取Unsplash服务实例(单例模式)"""
    global _unsplash_service
    
    if _unsplash_service is None:
        _unsplash_service = UnsplashService()
    
    return _unsplash_service

# 这种写法的好处：
# 1. 懒加载 — import 模块时不创建，第一次调用 get_unsplash_service() 时才创建
# 2. 单例 — 整个应用只存在一个实例，避免重复读配置、重复建立连接
# 3. 封装 — 外部不需要知道 _unsplash_service 变量的存在，通过函数获取即可


# 调用例子（其他文件调函数拿实例——干净）
# from app.services.unsplash_service import get_unsplash_service # ← import 时只是 None，不创建（0 开销）
# service = get_unsplash_service() # → 第一次创建 UnsplashService
# service.search_photos("故宫")