# tgtc-sdk (Python)

**[English](README.md)**

TGTC 数据 API 的官方 Python 客户端。一行代码接入 BSC 代币数据：行情、持仓结构、安全审计、持有人、社交信息、聪明钱动向、钱包分析、推特检测、AI 翻译。

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

## 端点一览

| 方法 | 端点 | 返回内容 |
| --- | --- | --- |
| `token(ca, categories=..., fields=...)` | `POST /api/v1/aggregation/token` | 代币全量情报：行情 / 持仓 / 安全 / 持有人 / 社交 / 聪明钱 |
| `trending(kind="new", limit=20)` | `POST /api/v1/token/trending` | 新创建 / 新发射 / 即将毕业 榜单 |
| `hot(interval="1h", limit=50)` | `POST /api/v1/token/hot` | 热门搜索榜单 |
| `trades(actor="smartmoney", side=..., limit=50)` | `POST /api/v1/track/trades` | 聪明钱 / KOL 实时交易流 |
| `signals(signal_types=[20], limit=50)` | `POST /api/v1/market/signals` | 市场信号流（新币/异动/聪明钱行为） |
| `wallet(action, wallet, period="7d", ...)` | `POST /api/v1/wallet/{action}` | 钱包分析：profile / stats / profits / activity / created / balance |
| `twitter(action, username=..., ...)` | `POST /api/v1/twitter/{action}` | 推特检测：user.info / tweets / timeline / followers / search / tweet.* |
| `sentiment(ca)` | `POST /api/v1/twitter/sentiment` | CA 舆情：热度评级 + AI 解读 + 提及数据 |
| `translate(action, text)` | `POST /api/v1/translate/{action}` | AI 翻译 / 摘要（输出中文） |

### 示例

```python
# 榜单 — 新发射代币
for item in client.trending(kind="launch", limit=10).data.get("items", []):
    print(item.get("symbol"), item.get("price"))

# 聪明钱买入交易流
for t in client.trades(actor="smartmoney", side="buy", limit=10).data.get("items", []):
    print(t.get("token"), t.get("price"))

# 钱包画像
w = client.wallet("profile", wallet="0x...钱包地址")
print(w.data.get("pnl_7d"), w.remaining)

# CA 舆情
s = client.sentiment("0x...合约地址")
print(s.data.get("heat_tier"))

# 翻译
r = client.translate("translate", text="gm everyone")
print(r.data.get("text"))
```

所有端点均支持可选 `fields=[...]` 精确裁剪响应（扣次随选择减少）。

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

## 文档

完整接口文档见 [TGTC API Docs](https://github.com/TGTC-Suiyoung/tgtc-api-docs)。
