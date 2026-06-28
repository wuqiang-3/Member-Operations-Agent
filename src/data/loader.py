"""
数据加载器 — 从本地 JSON 加载 Mock 数据
生产阶段替换为南讯 ECRP / 数云 CDP 适配器
"""
import json
import os
from typing import Any


_DATA_DIR = os.path.dirname(os.path.abspath(__file__))

_cache: dict[str, list[dict[str, Any]]] = {}


def _load_json(filename: str) -> list[dict[str, Any]]:
    """带缓存的数据加载"""
    if filename in _cache:
        return _cache[filename]

    path = os.path.join(_DATA_DIR, filename)
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    _cache[filename] = data
    return data


def get_members(brand_id: str | None = None) -> list[dict[str, Any]]:
    """获取会员数据，可选按品牌筛选"""
    members = _load_json("mock_members.json")
    if brand_id:
        members = [m for m in members if m["brand_id"] == brand_id]
    return members


def get_campaigns(brand_id: str | None = None) -> list[dict[str, Any]]:
    """获取历史活动数据"""
    campaigns = _load_json("mock_campaigns.json")
    if brand_id:
        campaigns = [c for c in campaigns if c["brand_id"] == brand_id]
    return campaigns


def get_brands() -> list[dict[str, Any]]:
    """获取品牌列表"""
    return _load_json("mock_brands.json")


def get_brand_by_id(brand_id: str) -> dict[str, Any] | None:
    """按 ID 获取品牌"""
    for b in get_brands():
        if b["brand_id"] == brand_id:
            return b
    return None


def get_brand_by_name(name: str) -> dict[str, Any] | None:
    """按名称模糊匹配品牌"""
    for b in get_brands():
        if name in b["name"] or name in b["brand_id"]:
            return b
    return None
