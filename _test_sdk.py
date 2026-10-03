# -*- coding: utf-8 -*-
"""tgtc-sdk 离线测试：mock requests，验证鉴权头/路径/参数构造/扣次解析/错误映射。

运行：python _test_sdk.py
"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

from unittest.mock import patch

from tgtc import (TGTC, TGTCAuthError, TGTCParamError, TGTCNotFoundError,
                  TGTCQuotaError, TGTCUnavailableError, TGTCError)

CA = "0x" + "a" * 40


class FakeResp:
    def __init__(self, status_code, json_body, headers=None):
        self.status_code = status_code
        self._body = json_body
        self.headers = headers or {}
        self.reason = ""

    def json(self):
        return self._body

    @property
    def content(self):
        return b"{}" if self._body else b""


def _make_client():
    return TGTC(api_key="test-key", base_url="https://api.test")

def test_payload_and_headers():
    captured = {}
    def fake_post(url, json=None, timeout=None):
        captured["url"] = url
        captured["json"] = json
        return FakeResp(200, {
            "ca": CA, "symbol": "TEST", "price": 0.1,
            "categories": ["basic"], "disclaimer": "x",
            "data_delay_sec": 0, "degraded_sources": [],
        }, {"X-RateLimit-Remaining": "97", "X-RateLimit-Used": "3", "X-Cache": "MISS"})
    c = _make_client()
    with patch.object(c._session, "post", side_effect=fake_post):
        res = c.token(CA, categories=["basic", "security"])
    assert captured["url"] == "https://api.test/api/v1/aggregation/token", captured["url"]
    assert captured["json"] == {"ca": CA, "chain": "bsc",
                                "categories": ["basic", "security"]}, captured["json"]
    assert c._session.headers["X-API-Key"] == "test-key"
    assert res.remaining == 97 and res.used == 3 and not res.cache_hit
    assert res.symbol == "TEST" and res.price == 0.1
    print("PASS payload/headers/credits")

def test_fields_mode():
    captured = {}
    def fake_post(url, json=None, timeout=None):
        captured["json"] = json
        return FakeResp(200, {"ca": CA, "symbol": "T", "data_delay_sec": 0,
                              "degraded_sources": []},
                        {"X-RateLimit-Remaining": "10", "X-RateLimit-Used": "1"})
    c = _make_client()
    with patch.object(c._session, "post", side_effect=fake_post):
        res = c.token(CA, fields=["symbol", "price"])
    assert captured["json"]["fields"] == ["symbol", "price"]
    assert "categories" not in captured["json"]
    assert res.ok
    print("PASS fields mode")

def test_cache_hit():
    def fake_post(url, json=None, timeout=None):
        return FakeResp(200, {"ca": CA, "symbol": "T", "data_delay_sec": 1,
                              "degraded_sources": ["twitter"]},
                        {"X-RateLimit-Remaining": "100", "X-RateLimit-Used": "0",
                         "X-Cache": "HIT"})
    c = _make_client()
    with patch.object(c._session, "post", side_effect=fake_post):
        res = c.token(CA)
    assert res.cache_hit and res.used == 0 and res.delay_sec == 1
    assert res.degraded == ["twitter"]
    print("PASS cache hit")

def test_error_mapping():
    cases = [
        (401, "缺少 X-API-Key 请求头", TGTCAuthError),
        (400, "CA 格式错误（需 0x 开头 40 位十六进制）", TGTCParamError),
        (422, "categories 与 fields 不能同时使用，请二选一", TGTCParamError),
        (404, "代币数据不存在或暂不可用", TGTCNotFoundError),
        (429, "调用次数不足（本次需 3 次，剩余 2）", TGTCQuotaError),
        (503, "服务初始化中，请稍后再试", TGTCUnavailableError),
        (500, "数据获取失败，请稍后重试", TGTCError),
    ]
    for code, detail, exc in cases:
        def fake_post(url, json=None, timeout=None):
            return FakeResp(code, {"detail": detail})
        c = _make_client()
        with patch.object(c._session, "post", side_effect=fake_post):
            try:
                c.token(CA)
            except exc as e:
                assert detail in str(e), (code, str(e))
            else:
                raise AssertionError(f"code {code} 未抛 {exc.__name__}")
    print("PASS error mapping (7 cases)")

def test_missing_key():
    try:
        TGTC()
    except TGTCError:
        pass
    else:
        raise AssertionError("未传 api_key 应报错")
    print("PASS missing key")

if __name__ == "__main__":
    test_payload_and_headers()
    test_fields_mode()
    test_cache_hit()
    test_error_mapping()
    test_missing_key()
    print("ALL_TESTS_PASSED")
