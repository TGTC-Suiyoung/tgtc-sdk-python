# -*- coding: utf-8 -*-
"""TGTC 客户端：X-API-Key 鉴权 + token 端点封装。

v0.1 只覆盖 token（代币聚合）端点；后续端点按同样模式追加方法即可。
架构要点：
  · 计费透明——每次调用返回剩余次数（remaining）与本次扣次（used）
  · 错误映射——HTTP 状态码转明确异常（见 errors.py）
  · 重试策略——5xx / 网络错误指数退避重试（带 jitter）；429 是余额不足，
    重试无意义，直接抛 TGTCQuotaError（携带剩余次数）
  · 零侵入——SDK 只面向 /api/v1 产品接口，不直连任何数据源
"""

from __future__ import annotations

import random
import time
from typing import List, Optional

import requests

from .errors import TGTCError, TGTCQuotaError, _map_error, _parse_remaining
from .models import TokenResult

DEFAULT_BASE_URL = "https://www.tgtcbot.com"
TOKEN_PATH = "/api/v1/aggregation/token"

# 可选类别（缺省由服务端按产品默认执行）
CATEGORIES = ("basic", "structure", "holders", "security", "social", "traders")

# 重试策略默认值：最多 3 次尝试（1 次原始 + 2 次重试），退避基数 0.5s
DEFAULT_MAX_RETRIES = 2
DEFAULT_RETRY_BACKOFF = 0.5


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
                 timeout: float = 30.0,
                 max_retries: int = DEFAULT_MAX_RETRIES,
                 retry_backoff: float = DEFAULT_RETRY_BACKOFF) -> None:
        if not api_key:
            raise TGTCError("缺少 API Key：请在个人中心创建 Key 后传入 api_key")
        self._base_url = (base_url or DEFAULT_BASE_URL).rstrip("/")
        self._timeout = timeout
        self._max_retries = max(0, int(max_retries))
        self._retry_backoff = max(0.0, float(retry_backoff))
        self._session = requests.Session()
        self._session.headers["X-API-Key"] = api_key

    # ── 内部请求管道 ──────────────────────────────────────────
    def _post(self, path: str, payload: dict) -> tuple[dict, dict]:
        """POST JSON 到产品接口；返回 (响应体, 计费明细)。异常已映射为明确类型。

        重试规则：5xx / 网络错误 → 指数退避重试（最多 max_retries 次）；
        429（余额不足）→ 不重试，直接抛 TGTCQuotaError。
        """
        attempts = self._max_retries + 1  # 1 次原始 + max_retries 次重试
        for attempt in range(1, attempts + 1):
            try:
                resp = self._session.post(self._base_url + path,
                                          json=payload, timeout=self._timeout)
            except requests.RequestException as e:
                if attempt < attempts:
                    time.sleep(self._backoff(attempt))
                    continue
                raise TGTCError(f"网络请求失败：{e}") from e
            # 429：余额不足，重试无意义——直抛并带上剩余次数
            if resp.status_code == 429:
                detail = self._detail_of(resp)
                raise TGTCQuotaError(detail, remaining=_parse_remaining(detail))
            # 5xx：服务端抖动，退避重试
            if resp.status_code >= 500 and attempt < attempts:
                time.sleep(self._backoff(attempt))
                continue
            if resp.status_code >= 400:
                raise _map_error(resp.status_code, self._detail_of(resp),
                                 headers=resp.headers)
            try:
                body = resp.json() if resp.content else {}
            except ValueError:
                body = {}
            if not isinstance(body, dict):
                raise TGTCError(f"响应格式异常：{body!r}")
            meta = {
                "remaining": resp.headers.get("X-RateLimit-Remaining"),
                "used": resp.headers.get("X-RateLimit-Used"),
                "cache_hit": resp.headers.get("X-Cache") == "HIT",
            }
            return body, meta
        raise TGTCError("请求失败（已按策略重试）")  # 理论不可达

    def _backoff(self, attempt: int) -> float:
        """指数退避 + 随机 jitter：0.5s / 1s / 2s… × (1 + 0~0.5)。"""
        base = self._retry_backoff * (2 ** (attempt - 1))
        return base * (1 + random.uniform(0, 0.5))

    @staticmethod
    def _detail_of(resp) -> str:
        try:
            body = resp.json() if resp.content else {}
        except ValueError:
            body = {}
        return str(body.get("detail") or body or resp.reason) if body else str(resp.reason or "")

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
