# -*- coding: utf-8 -*-
"""tgtc-sdk 结构化返回。v0.1 覆盖 token 端点；其余端点复用 Result 基类扩展。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class Result:
    """通用响应信封：数据 + 计费明细（来自响应头，与服务端扣次一致）。"""

    data: Dict[str, Any]
    remaining: Optional[int] = None      # 剩余次数（X-RateLimit-Remaining）
    used: Optional[int] = None           # 本次扣次（X-RateLimit-Used）
    cache_hit: bool = False              # 命中缓存 = 本次免费（X-Cache: HIT）
    delay_sec: Optional[int] = None      # 数据新鲜度（data_delay_sec，0 = 实时）
    degraded: Optional[list] = None      # 数据源降级标记（degraded_sources，空 = 全量正常）

    def __post_init__(self) -> None:
        self.remaining = int(self.remaining) if self.remaining is not None else None
        self.used = int(self.used) if self.used is not None else None
        self.delay_sec = int(self.delay_sec) if self.delay_sec is not None else None

    @property
    def ok(self) -> bool:
        """请求是否成功（非异常返回即为成功）。"""
        return True


@dataclass
class TokenResult(Result):
    """token 端点结构化返回。常用字段提供 property 快捷访问，其余字段走 data 字典。"""

    @property
    def ca(self) -> Optional[str]:
        return self.data.get("ca")

    @property
    def symbol(self) -> Optional[str]:
        return self.data.get("symbol")

    @property
    def name(self) -> Optional[str]:
        return self.data.get("name")

    @property
    def price(self) -> Optional[float]:
        return self.data.get("price")

    @property
    def mcap(self) -> Optional[float]:
        return self.data.get("mcap")

    @property
    def liquidity(self) -> Optional[float]:
        return self.data.get("liquidity")

    @property
    def volume_24h(self) -> Optional[float]:
        return self.data.get("volume_24h")

    @property
    def holder_count(self) -> Optional[int]:
        return self.data.get("holder_count")

    @property
    def categories(self) -> list:
        return list(self.data.get("categories") or [])

    @property
    def disclaimer(self) -> Optional[str]:
        return self.data.get("disclaimer")
