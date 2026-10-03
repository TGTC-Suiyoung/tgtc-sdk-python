# -*- coding: utf-8 -*-
"""TGTC 客户端：X-API-Key 鉴权 + 全产品端点封装。

覆盖端点：代币聚合 / 榜单 / 交易流 / 信号流 / 钱包分析 / 推特检测 / CA 舆情 / AI 翻译。
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

from .errors import TGTCError, TGTCParamError, TGTCQuotaError, _map_error, _parse_remaining
from .models import Result, TokenResult

DEFAULT_BASE_URL = "https://www.tgtcbot.com"
TOKEN_PATH = "/api/v1/aggregation/token"
TRENDING_PATH = "/api/v1/token/trending"
HOT_PATH = "/api/v1/token/hot"
TRADES_PATH = "/api/v1/track/trades"
SIGNALS_PATH = "/api/v1/market/signals"
WALLET_PATH = "/api/v1/wallet/{action}"
TWITTER_PATH = "/api/v1/twitter/{action}"
SENTIMENT_PATH = "/api/v1/twitter/sentiment"
TRANSLATE_PATH = "/api/v1/translate/{action}"

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
    def _call(self, path: str, payload: dict, result_cls=Result):
        """请求端点并构造响应信封（计费明细来自响应头）。"""
        body, meta = self._post(path, payload)
        return result_cls(data=body,
                          remaining=meta["remaining"],
                          used=meta["used"],
                          cache_hit=meta["cache_hit"],
                          delay_sec=body.get("data_delay_sec"),
                          degraded=body.get("degraded_sources"))

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
        if categories and fields:
            raise TGTCParamError("categories 与 fields 不能同时使用，请二选一")
        payload = {"ca": ca, "chain": chain}
        if categories:
            payload["categories"] = [str(c) for c in categories]
        if fields:
            payload["fields"] = [str(f) for f in fields]
        return self._call(TOKEN_PATH, payload, TokenResult)

    def trending(self, chain: str = "bsc", kind: str = "new",
                 limit: int = 20, fields: Optional[List[str]] = None) -> Result:
        """代币榜单（新创建 / 新发射 / 即将毕业）。

        参数:
            kind: new（新创建）/ launch（新发射）/ graduating（即将毕业）
            limit: 返回条数 1~100
        """
        payload = {"chain": chain, "kind": kind, "limit": limit}
        if fields:
            payload["fields"] = [str(f) for f in fields]
        return self._call(TRENDING_PATH, payload)

    def hot(self, chain: str = "bsc", interval: str = "1h",
            limit: int = 50, fields: Optional[List[str]] = None) -> Result:
        """热门搜索榜单。

        参数:
            interval: 统计区间 1m / 5m / 1h / 6h / 24h
            limit: 返回条数 1~100
        """
        payload = {"chain": chain, "interval": interval, "limit": limit}
        if fields:
            payload["fields"] = [str(f) for f in fields]
        return self._call(HOT_PATH, payload)

    def trades(self, chain: str = "bsc", actor: str = "smartmoney",
               side: Optional[str] = None, limit: int = 50,
               fields: Optional[List[str]] = None) -> Result:
        """聪明钱 / KOL 实时交易流。

        参数:
            actor: smartmoney（聪明钱）/ kol（KOL）
            side: buy / sell 方向过滤（可选）
            limit: 返回条数 1~200
        """
        payload = {"chain": chain, "actor": actor, "limit": limit}
        if side:
            payload["side"] = side
        if fields:
            payload["fields"] = [str(f) for f in fields]
        return self._call(TRADES_PATH, payload)

    def signals(self, chain: str = "bsc",
                signal_types: Optional[List[int]] = None,
                limit: int = 50, fields: Optional[List[str]] = None) -> Result:
        """市场信号流（新币/异动/聪明钱行为等信号，缺省返回全部支持类型）。

        参数:
            signal_types: 信号类型 ID 列表（可选，如 [20]）
            limit: 返回条数 1~200
        """
        payload = {"chain": chain, "limit": limit}
        if signal_types:
            payload["signal_types"] = [int(s) for s in signal_types]
        if fields:
            payload["fields"] = [str(f) for f in fields]
        return self._call(SIGNALS_PATH, payload)

    def wallet(self, action: str, wallet: str, chain: str = "bsc",
               period: str = "7d", token: Optional[str] = None,
               limit: int = 20, cursor: Optional[str] = None,
               fields: Optional[List[str]] = None) -> Result:
        """钱包分析。

        参数:
            action: profile（画像）/ stats（统计）/ profits（盈亏）/
                    activity（活动记录，支持 cursor 翻页）/ created（创建代币）/ balance（持仓余额）
            wallet: 钱包地址（0x 开头 40 位十六进制）
            period: 统计区间 1d / 7d / 30d
            token: 指定代币地址（balance 必填）
            cursor: activity 翻页游标（服务端响应返回）
            limit: 返回条数 1~100
        """
        payload = {"chain": chain, "wallet": wallet, "period": period, "limit": limit}
        if token:
            payload["token"] = token
        if cursor:
            payload["cursor"] = cursor
        if fields:
            payload["fields"] = [str(f) for f in fields]
        return self._call(WALLET_PATH.format(action=action), payload)

    def twitter(self, action: str, username: Optional[str] = None,
                user_id: Optional[str] = None, query: Optional[str] = None,
                count: Optional[int] = None, cursor: Optional[str] = None,
                tweet_id: Optional[str] = None,
                tweet_ids: Optional[List[str]] = None,
                include_replies: bool = False,
                sort: Optional[str] = None) -> Result:
        """推特检测。

        参数:
            action: user.info / user.tweets / user.timeline / user.followers /
                    user.followings / user.search / tweet.search / tweet.detail /
                    tweet.replies / tweet.quotes / tweet.retweets / tweet.thread
            username: 目标用户名（user.* 系列必填）
            user_id: 目标用户 ID（与 username 二选一）
            query: 搜索关键词（user.search / tweet.search 必填）
            count: 返回条数 1~100
            cursor: 翻页游标（服务端响应返回）
            tweet_id: 目标推文 ID（tweet.* 系列）
            tweet_ids: 批量推文 ID（tweet.detail 支持）
            include_replies: 是否含回复
            sort: tweet.replies 排序 Relevance / Latest / Likes
        """
        payload = {}
        for k, v in (("username", username), ("user_id", user_id), ("query", query),
                     ("count", count), ("cursor", cursor), ("tweet_id", tweet_id),
                     ("sort", sort)):
            if v is not None:
                payload[k] = v
        if tweet_ids:
            payload["tweet_ids"] = [str(t) for t in tweet_ids]
        if include_replies:
            payload["include_replies"] = True
        return self._call(TWITTER_PATH.format(action=action), payload)

    def sentiment(self, ca: str, chain: str = "bsc") -> Result:
        """CA 舆情分析：热度评级 + AI 解读 + 提及推文数据。

        参数:
            ca: 合约地址
        """
        return self._call(SENTIMENT_PATH, {"ca": ca, "chain": chain})

    def translate(self, action: str, text: str) -> Result:
        """AI 翻译 / 长文本摘要（输出中文）。

        参数:
            action: translate（翻译）/ summarize（摘要）
            text: 待处理文本，最长 2000 字符
        """
        return self._call(TRANSLATE_PATH.format(action=action), {"text": text})
