# -*- coding: utf-8 -*-
"""TGTC 客户端：X-API-Key 鉴权 + token 端点封装。

v0.1 只覆盖 token（代币聚合）端点；后续端点按同样模式追加方法即可。
架构要点：
  · 计费透明——每次调用返回剩余次数（remaining）与本次扣次（used）
  · 错误映射——HTTP 状态码转明确异常（见 errors.py）
  · 零侵入——SDK 只面向 /api/v1 产品接口，不直连任何数据源
"""

from __future__ import annotations

from typing import List, Optional

import requests

from .errors import TGTCError, _map_error
from .models import TokenResult

DEFAULT_BASE_URL = "https://www.tgtcbot.com"
TOKEN_PATH = "/api/v1/aggregation/token"

# 可选类别（与后端 _CATEGORIES 一致）：缺省由服务端按产品默认执行
CATEGORIES = ("basic", "structure", "holders", "security", "social", "traders")


class TGTC:
    """TGTC 数据 API 客户端。

    用法::

        from tgtc import TGTC
        client = TGTC(api_key="你的 API Key")
        res = client.token("0x...")
        print(res.symbol, res.remaining)   # 符号 + 剩余次数
    """

    def __init__(self, api_key: Optional[str] = None,
                 base_url: str = DEFAULT_BASE_URL,
                 timeout: float = 30.0) -> None:
        if not api_key:
            raise TGTCError("缺少 API Key：请在个人中心创建 Key 后传入 api_key")
        self._base_url = (base_url or DEFAULT_BASE_URL).rstrip("/")
        self._timeout = timeout
        self._session = requests.Session()
        self._session.headers["X-API-Key"] = api_key

    # ── 内部请求管道 ──────────────────────────────────────────
    def _post(self, path: str, payload: dict) -> tuple[dict, dict]:
        """POST JSON 到产品接口；返回 (响应体, 计费明细)。异常已映射为明确类型。"""
        try:
            resp = self._session.post(self._base_url + path,
                                      json=payload, timeout=self._timeout)
        except requests.RequestException as e:
            raise TGTCError(f"网络请求失败：{e}") from e
        meta = {
            "remaining": resp.headers.get("X-RateLimit-Remaining"),
            "used": resp.headers.get("X-RateLimit-Used"),
            "cache_hit": resp.headers.get("X-Cache") == "HIT",
        }
        try:
            body = resp.json() if resp.content else {}
        except ValueError:
            body = {}
        if resp.status_code >= 400:
            raise _map_error(resp.status_code, str(body.get("detail") or body or resp.reason))
        if not isinstance(body, dict):
            raise TGTCError(f"响应格式异常：{body!r}")
        return body, meta

    # ── 产品端点 ─────────────────────────────────────────────
    def token(self, ca: str, chain: str = "bsc",
              categories: Optional[List[str]] = None,
              fields: Optional[List[str]] = None) -> TokenResult:
        """代币聚合查询（基本行情/持仓结构/安全审计/持有人/社交/聪明钱，按类别计费）。

        参数:
            ca: 合约地址（0x 开头 40 位十六进制）
            chain: 链名，当前仅支持 bsc
            categories: 可选类别子集；缺省由服务端按产品默认返回
            fields: 可选字段裁剪（与 categories 互斥，二选一）

        返回:
            TokenResult：data 为完整响应体，remaining/used 为本次计费明细
        """
        payload = {"ca": ca, "chain": chain}
        if categories:
            payload["categories"] = [str(c) for c in categories]
        if fields:
            payload["fields"] = [str(f) for f in fields]
        body, meta = self._post(TOKEN_PATH, payload)
        return TokenResult(data=body,
                            remaining=meta["remaining"],
                            used=meta["used"],
                            cache_hit=meta["cache_hit"],
                            delay_sec=body.get("data_delay_sec"),
                            degraded=body.get("degraded_sources"))
