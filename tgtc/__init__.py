# -*- coding: utf-8 -*-
"""tgtc-sdk：TGTC 数据 API 的 Python 客户端。

v0.1 覆盖 token（代币聚合）端点，计费透明（每次返回剩余次数与扣次明细）。
"""

from .client import CATEGORIES, DEFAULT_BASE_URL, TGTC
from .errors import (TGTCError, TGTCAuthError, TGTCParamError, TGTCNotFoundError,
                     TGTCQuotaError, TGTCUnavailableError)
from .models import TokenResult

__version__ = "0.1.0"
__all__ = [
    "TGTC", "TokenResult",
    "TGTCError", "TGTCAuthError", "TGTCParamError", "TGTCNotFoundError",
    "TGTCQuotaError", "TGTCUnavailableError",
    "CATEGORIES", "DEFAULT_BASE_URL",
]
