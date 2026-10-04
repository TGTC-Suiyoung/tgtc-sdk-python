# -*- coding: utf-8 -*-
"""tgtc-sdk：TGTC 数据 API 的 Python 客户端。

v0.2.1 覆盖全部产品端点：代币聚合 / 榜单 / 交易流 / 信号流 / 钱包分析 /
推特检测 / CA 舆情 / AI 翻译与摘要。计费透明（每次返回剩余次数与扣次明细）、
5xx/网络错误自动退避重试、429（余额不足）抛结构化异常携带剩余次数、
connect/read 分离超时 + User-Agent 标识。
"""

from .client import CATEGORIES, DEFAULT_BASE_URL, SDK_VERSION, TGTC
from .errors import (TGTCError, TGTCAuthError, TGTCParamError, TGTCNotFoundError,
                     TGTCQuotaError, TGTCUnavailableError, TGTCServerError)
from .models import Result, TokenResult

__version__ = SDK_VERSION
__all__ = [
    "TGTC", "Result", "TokenResult",
    "TGTCError", "TGTCAuthError", "TGTCParamError", "TGTCNotFoundError",
    "TGTCQuotaError", "TGTCUnavailableError", "TGTCServerError",
    "CATEGORIES", "DEFAULT_BASE_URL", "SDK_VERSION",
]
