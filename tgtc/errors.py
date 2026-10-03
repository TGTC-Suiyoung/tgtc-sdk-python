# -*- coding: utf-8 -*-
"""tgtc-sdk 异常体系：错误码 → 明确异常，开发者不用猜响应结构。

设计要点（对应产品契约）：
  · 429 = 余额不足，重试无意义 → TGTCQuotaError 携带剩余次数，SDK 不重试
  · 5xx = 服务端抖动，可重试 → TGTCServerError（SDK 已自动退避重试后仍失败才抛出）
  · 503 = 服务初始化/维护 → TGTCUnavailableError（可短暂等待后重试）
"""


class TGTCError(Exception):
    """SDK 基类异常。所有异常均继承此类的 message 为服务端返回的中文说明。"""


class TGTCAuthError(TGTCError):
    """鉴权失败（401）：API Key 缺失或无效。"""


class TGTCParamError(TGTCError):
    """请求参数错误（400/422）：CA 格式、链名或字段/类别组合不合法。"""


class TGTCNotFoundError(TGTCError):
    """数据不存在（404）：代币数据缺失或暂不可用。"""


class TGTCQuotaError(TGTCError):
    """调用次数不足（429）。余额不足，重试无意义——请充值后再调用。

    属性:
        remaining: 解析出的剩余次数（服务端 detail 未携带时为 None）
        retry_after: 建议等待秒数（服务端未返回 Retry-After 时为 None）
    """

    def __init__(self, detail: str = "", remaining=None, retry_after=None):
        super().__init__(detail)
        self.remaining = remaining
        self.retry_after = retry_after


class TGTCUnavailableError(TGTCError):
    """服务暂不可用（503）：服务初始化中或维护中，可稍后重试。"""


class TGTCServerError(TGTCError):
    """服务端错误（5xx）。SDK 已自动退避重试（最多 max_retries 次），仍失败抛出。

    属性:
        retry_after: 服务端返回的 Retry-After 秒数（未返回时为 None）
    """

    def __init__(self, detail: str = "", retry_after=None):
        super().__init__(detail)
        self.retry_after = retry_after


def _map_error(status_code: int, detail: str, headers=None,
               remaining: int = None) -> TGTCError:
    """HTTP 状态码 → 异常实例。未知状态码归入 TGTCError。

    headers: 原始响应头（解析 Retry-After / X-RateLimit-Remaining）
    remaining: 429 时预解析的剩余次数（调用方可从 detail 正则提取）
    """
    headers = headers or {}
    if status_code == 401:
        return TGTCAuthError(detail)
    if status_code in (400, 422):
        return TGTCParamError(detail)
    if status_code == 404:
        return TGTCNotFoundError(detail)
    if status_code == 429:
        retry_after = headers.get("Retry-After")
        return TGTCQuotaError(detail,
                              remaining=remaining if remaining is not None
                              else _parse_remaining(detail),
                              retry_after=float(retry_after) if retry_after else None)
    if status_code == 503:
        retry_after = headers.get("Retry-After")
        return TGTCUnavailableError(detail) if not retry_after \
            else TGTCUnavailableError(f"{detail}（建议 {float(retry_after):.0f} 秒后重试）")
    if 500 <= status_code < 600:
        retry_after = headers.get("Retry-After")
        return TGTCServerError(detail,
                               retry_after=float(retry_after) if retry_after else None)
    return TGTCError(f"服务返回异常状态码 {status_code}：{detail}")


def _parse_remaining(detail: str):
    """从服务端 429 detail 文本解析剩余次数（如「剩余 2」→ 2）；解析不到返回 None。"""
    if not detail:
        return None
    import re
    m = re.search(r"剩余\s*(\d+)", str(detail))
    return int(m.group(1)) if m else None
