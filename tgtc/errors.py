# -*- coding: utf-8 -*-
"""tgtc-sdk 异常体系：错误码 → 明确异常，开发者不用猜响应结构。"""


class TGTCError(Exception):
    """SDK 基类异常。所有异常均继承此类的 message 为服务端返回的中文说明。"""


class TGTCAuthError(TGTCError):
    """鉴权失败（401）：API Key 缺失或无效。"""


class TGTCParamError(TGTCError):
    """请求参数错误（400/422）：CA 格式、链名或字段/类别组合不合法。"""


class TGTCNotFoundError(TGTCError):
    """数据不存在（404）：代币数据缺失或暂不可用。"""


class TGTCQuotaError(TGTCError):
    """调用次数不足（429）：本次调用所需扣次超过剩余次数。"""


class TGTCUnavailableError(TGTCError):
    """服务暂不可用（503）：服务初始化中或维护中。"""


def _map_error(status_code: int, detail: str) -> TGTCError:
    """HTTP 状态码 → 异常实例。未知状态码归入 TGTCError。"""
    if status_code == 401:
        return TGTCAuthError(detail)
    if status_code in (400, 422):
        return TGTCParamError(detail)
    if status_code == 404:
        return TGTCNotFoundError(detail)
    if status_code == 429:
        return TGTCQuotaError(detail)
    if status_code == 503:
        return TGTCUnavailableError(detail)
    return TGTCError(f"服务返回异常状态码 {status_code}：{detail}")
