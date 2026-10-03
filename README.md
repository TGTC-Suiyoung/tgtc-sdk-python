# tgtc-sdk (Python)

**[中文](README.zh-CN.md)**

Official Python client for the TGTC data API. One line of code gets you BSC token intel — quotes, holders, security audit, socials, smart-money moves, wallets, tweets and more.

**Transparent billing**: every call returns your remaining calls and the units this request cost.

## Install

```bash
pip install tgtc-sdk
```

You'll need an API Key (TGTC Bot profile center → My API).

## Quick start

```python
from tgtc import TGTC

client = TGTC(api_key="your-api-key")

# Token aggregation (full product categories by default)
res = client.token("0x...contract address")

print(res.symbol)          # token symbol
print(res.price)           # current price
print(res.remaining)       # remaining calls
print(res.used)            # units this request cost
```

## Endpoints

| Method | Endpoint | What you get |
| --- | --- | --- |
| `token(ca, categories=..., fields=...)` | `POST /api/v1/aggregation/token` | Full token intel: quotes / structure / security / holders / socials / smart money |
| `trending(kind="new", limit=20)` | `POST /api/v1/token/trending` | Newly created / launched / graduating tokens |
| `hot(interval="1h", limit=50)` | `POST /api/v1/token/hot` | Hot search rankings |
| `trades(actor="smartmoney", side=..., limit=50)` | `POST /api/v1/track/trades` | Smart-money / KOL live trades |
| `signals(signal_types=[20], limit=50)` | `POST /api/v1/market/signals` | Market signals (new listings, anomalies, smart-money behavior) |
| `wallet(action, wallet, period="7d", ...)` | `POST /api/v1/wallet/{action}` | Wallet analysis: profile / stats / profits / activity / created / balance |
| `twitter(action, username=..., ...)` | `POST /api/v1/twitter/{action}` | Twitter: user.info / tweets / timeline / followers / search / tweet.* |
| `sentiment(ca)` | `POST /api/v1/twitter/sentiment` | CA sentiment: heat rating + AI insight + mentions |
| `translate(action, text)` | `POST /api/v1/translate/{action}` | AI translate / summarize (outputs Chinese) |

### Examples

```python
# Token rankings — newly launched
for item in client.trending(kind="launch", limit=10).data.get("items", []):
    print(item.get("symbol"), item.get("price"))

# Smart-money buy trades
for t in client.trades(actor="smartmoney", side="buy", limit=10).data.get("items", []):
    print(t.get("token"), t.get("price"))

# Wallet profile
w = client.wallet("profile", wallet="0x...wallet")
print(w.data.get("pnl_7d"), w.remaining)

# CA sentiment
s = client.sentiment("0x...contract")
print(s.data.get("heat_tier"))

# Translate
r = client.translate("translate", text="gm everyone")
print(r.data.get("text"))
```

Every endpoint accepts optional `fields=[...]` to trim the response (and pay less for less).

## Billing transparency

| Field | Meaning |
| --- | --- |
| `remaining` | Remaining calls after this request |
| `used` | Units this request cost (0 on cache hit) |
| `cache_hit` | True if served from cache (no charge) |
| `delay_sec` | Data freshness (0 = live) |

## Error handling

```python
from tgtc import TGTCError, TGTCQuotaError, TGTCAuthError

try:
    res = client.token(ca)
except TGTCAuthError:
    print("invalid API key")
except TGTCQuotaError as e:
    print(f"out of calls — remaining {e.remaining}, please top up")
except TGTCError as e:
    print("request failed:", e)
```

| Exception | When |
| --- | --- |
| `TGTCAuthError` | Missing / invalid API Key |
| `TGTCParamError` | Bad parameters (CA format / category combos) |
| `TGTCNotFoundError` | Token data not found |
| `TGTCQuotaError` | Out of calls (`e.remaining` shows what's left — top up) |
| `TGTCUnavailableError` | Service starting up or in maintenance |
| `TGTCServerError` | Server error (raised after automatic retries) |

## Retry policy

- **5xx / network errors**: automatic exponential backoff with jitter (default up to 2 retries), raised as `TGTCServerError` after exhausting retries
- **429 (out of calls)**: no retry — it would never succeed; raises `TGTCQuotaError` with remaining calls
- **400 / 422 / 404**: no retry (client or data issue)

Customize: `TGTC(api_key=..., max_retries=3, retry_backoff=0.5)`.

## Docs

Full API reference: [TGTC API Docs](https://github.com/TGTC-Suiyoung/tgtc-api-docs)
