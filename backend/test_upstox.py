import sys
sys.path.insert(0,'/app')
from app.modules.market_data.upstox_provider import get_upstox_provider, SYMBOL_TO_KEY
from app.core.config import get_settings
import httpx

s=get_settings()
token=s.UPSTOX_ACCESS_TOKEN.strip()
print("TOKEN_LEN:", len(token))

key=SYMBOL_TO_KEY.get("TCS")
print("TCS_KEY:", key)
url=f"https://api.upstox.com/v2/market-quote/quotes?instrument_key={key.replace('|','%7C')}"
resp=httpx.get(url,headers={"Authorization":"Bearer "+token,"Accept":"application/json"},timeout=15)
print("STATUS:", resp.status_code)
data=resp.json()
entry=data.get("data",{}).get(key)
if entry:
    print("TCS_RAW_LTP:", entry.get("last_price"))
    print("TCS_OHLC_CLOSE:", entry.get("ohlc",{}).get("close"))
    print("TCS_TIMESTAMP:", entry.get("timestamp"))
else:
    print("NO_ENTRY keys:", list(data.get("data",{}).keys())[:3])

# Also test provider
p=get_upstox_provider()
print("CONFIGURED:", p._configured)
q=p.get_quote("TCS")
if q:
    print("PROVIDER_LTP:", float(q.last_price))
else:
    print("PROVIDER returned None")
