from fastapi import APIRouter, HTTPException
from app.modules.market_data.indices import fetch_index_quotes, NSE_INDICES

router = APIRouter(prefix="/market/indices", tags=["Indices"])


@router.get("")
def list_indices():
    quotes = fetch_index_quotes()
    return quotes if quotes else [
        {"symbol": k, "name": v["name"], "last_price": 0, "change": 0, "change_pct": 0, "source": "UNAVAILABLE"}
        for k, v in NSE_INDICES.items()
    ]


@router.get("/{index_name}")
def get_index(index_name: str):
    key = index_name.upper()
    if key not in NSE_INDICES:
        raise HTTPException(status_code=404, detail=f"Index {index_name} not found")
    quotes = fetch_index_quotes()
    for q in quotes:
        if q["symbol"] == key:
            return q
    raise HTTPException(status_code=503, detail="Index data unavailable")
