"""POI图片API路由 — 仅保留Unsplash图片搜索"""
from fastapi import APIRouter, HTTPException
from ...services.unsplash_service import get_unsplash_service

router = APIRouter(prefix="/poi", tags=["POI"])


@router.get(
    "/photo",
    summary="获取景点图片",
    description="根据景点名称从Unsplash获取图片"
)
async def get_attraction_photo(name: str):
    """根据景点名称获取Unsplash图片URL"""
    try:
        unsplash = get_unsplash_service()
        photo_url = unsplash.get_photo_url(f"{name} China landmark")

        if not photo_url:
            photo_url = unsplash.get_photo_url(name)

        return {
            "success": True,
            "message": "获取图片成功",
            "data": {
                "name": name,
                "photo_url": photo_url
            }
        }

    except Exception as e:
        print(f"❌ 获取景点图片失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"获取景点图片失败: {str(e)}"
        )
