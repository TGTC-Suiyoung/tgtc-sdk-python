# tgtc-sdk (Python)

TGTC 数据 API 的 Python 客户端。一行代码接入 BSC 代币数据：基本行情、持仓结构、安全审计、持有人、社交信息、聪明钱动向。

**计费透明**：每次调用都会返回剩余次数与本次扣次明细，余额一眼可见。

## 安装

```bash
pip install tgtc-sdk
```

需要先创建 API Key（TGTC Bot 个人中心 → 我的 API）。

## 快速开始

```python
from tgtc import TGTC

client = TGTC(api_key="你的 API Key")

# 代币聚合查询（默认返回完整产品类别）
res = client.token("0x...合约地址")

print(res.symbol)          # 代币符号
print(res.price)           # 当前价格
print(res.remaining)       # 剩余调用次数
print(res.used)            # 本次扣次
```

## 按类别/字段查询

```python
# 只要行情 + 安全审计，扣次更少
res = client.token(ca, categories=["basic", "security"])

# 精确字段裁剪（与 categories 二选一）
res = client.token(ca, fields=["symbol", "price", "honeypot", "buy_tax"])
```

可选类别：`basic`（基本行情）/ `structure`（持仓结构）/ `holders`（持有人）/ `security`（安全审计）/ `social`（社交信息）/ `traders`（聪明钱动向）。

## 计费明细

| 字段 | 说明 |
| --- | --- |
| `remaining` | 剩余调用次数 |
| `used` | 本次扣次（缓存命中为 0） |
| `cache_hit` | 是否命中缓存（命中不扣次） |
| `delay_sec` | 数据新鲜度（0 = 实时） |

## 错误处理

```python
from tgtc import TGTCError, TGTCQuotaError, TGTCAuthError

try:
    res = client.token(ca)
except TGTCAuthError:
    print("API Key 无效")
except TGTCQuotaError as e:
    print(f"调用次数不足，剩余 {e.remaining} 次，请充值")
except TGTCError as e:
    print("请求失败：", e)
```

| 异常 | 触发条件 |
| --- | --- |
| `TGTCAuthError` | API Key 缺失或无效 |
| `TGTCParamError` | 参数错误（CA 格式/类别组合） |
| `TGTCNotFoundError` | 代币数据不存在 |
| `TGTCQuotaError` | 调用次数不足（`e.remaining` 携带剩余次数，需充值） |
| `TGTCUnavailableError` | 服务初始化或维护中 |
| `TGTCServerError` | 服务端错误（自动重试后仍失败） |

## 重试策略

- **5xx / 网络错误**：自动指数退避重试（默认最多 2 次重试，带随机抖动，不雪崩），仍失败抛 `TGTCServerError`
- **429（余额不足）**：重试无意义，不重试，直接抛 `TGTCQuotaError` 并携带剩余次数
- **400 / 422 / 404**：参数或数据问题，不重试

可自定义：`TGTC(api_key=..., max_retries=3, retry_backoff=0.5)`。

## 路线图

- [x] token：代币聚合查询
- [ ] token/trending + token/hot：榜单
- [ ] twitter：推特检测/舆情
- [ ] track：交易流
- [ ] market：信号流
- [ ] wallet：钱包分析
- [ ] translate：翻译

## 文档

完整接口文档见 [TGTC API Docs](https://github.com/TGTC-Suiyoung/tgtc-api-docs)。
