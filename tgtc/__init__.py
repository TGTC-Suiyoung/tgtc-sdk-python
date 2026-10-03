# -*- coding: utf-8 -*-
"""tgtc-sdk：TGTC 数据 API 的 Python 客户端。

v0.1.1 覆盖 token（代币聚合）端点：计费透明（每次返回剩余次数与扣次明细）、
5xx/网络错误自动退避重试、429（余额不足）抛结构化异常携带剩余次数。
"""

from .client import CATEGORIES, DEFAULT_BASE_URL, TGTC
from .errors import (TGTCError, TGTCAuthError, TGTCParamError, TGTCNotFoundError,
                     TGTCQuotaError, TGTCUnavailableError, TGTCServerError)
from .models import TokenResult

__version__ = "0.1.1"
__all__ = [
    "TGTC", "TokenResult",
    "TGTCError", "TGTCAuthError", "TGTCParamError", "TGTCNotFoundError",
    "TGTCQuotaError", "TGTCUnavailableError", "TGTCServerError",
    "CATEGORIES", "DEFAULT_BASE_URL",
]
