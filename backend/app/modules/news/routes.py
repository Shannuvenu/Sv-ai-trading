import logging
from datetime import datetime, timezone
import redis as sync_redis
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.core.database import get_db
from app.core.config import get_settings
from app.core.security import get_current_user
from app.modules.users.models import User
from app.modules.news.models import NewsArticle
from app.modules.news.finnhub_client import get_finnhub_client
from app.modules.news.schemas import NewsListResponse

router = APIRouter(prefix="/news", tags=["News"])
logger = logging.getLogger("news_routes")
settings = get_settings()

_redis = sync_redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)

COMPANY_NEWS_TTL = 1800  # 30 min
MARKET_NEWS_TTL = 900    # 15 min


def _parse_ts(unix_ts):
    if not unix_ts:
        return None
    return datetime.fromtimestamp(unix_ts, tz=timezone.utc)


def _upsert_articles(db: Session, raw_items: list[dict], category: str, symbol: str | None):
    for item in raw_items:
        fh_id = item.get("id")
        if fh_id and db.query(NewsArticle).filter(NewsArticle.finnhub_id == fh_id).first():
            continue
        db.add(NewsArticle(
            finnhub_id=fh_id,
            category=category,
            symbol=symbol,
            headline=item.get("headline") or "",
            summary=item.get("summary"),
            source=item.get("source"),
            url=item.get("url"),
            image_url=item.get("image"),
            published_at=_parse_ts(item.get("datetime")),
        ))
    db.commit()


def _refresh_if_stale(db: Session, cache_key: str, ttl: int, fetch_fn, category: str, symbol: str | None = None):
    if _redis.get(cache_key):
        return
    raw = fetch_fn()
    if raw:
        _upsert_articles(db, raw, category, symbol)
    _redis.setex(cache_key, ttl, "1")


@router.get("/company/{symbol}", response_model=NewsListResponse)
def get_company_news(
    symbol: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    symbol = symbol.upper()
    client = get_finnhub_client()
    _refresh_if_stale(
        db, f"news:cache:company:{symbol}", COMPANY_NEWS_TTL,
        lambda: client.get_company_news(symbol), "company", symbol,
    )
    q = db.query(NewsArticle).filter(NewsArticle.symbol == symbol).order_by(NewsArticle.published_at.desc())
    total = q.count()
    items = q.offset((page - 1) * page_size).limit(page_size).all()
    return NewsListResponse(items=items, page=page, page_size=page_size, total=total)


@router.get("/market", response_model=NewsListResponse)
def get_market_news(
    category: str = Query("general"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    client = get_finnhub_client()
    _refresh_if_stale(
        db, f"news:cache:market:{category}", MARKET_NEWS_TTL,
        lambda: client.get_market_news(category), "market", None,
    )
    q = db.query(NewsArticle).filter(NewsArticle.category == "market").order_by(NewsArticle.published_at.desc())
    total = q.count()
    items = q.offset((page - 1) * page_size).limit(page_size).all()
    return NewsListResponse(items=items, page=page, page_size=page_size, total=total)


@router.get("/search", response_model=NewsListResponse)
def search_news(
    q: str = Query(..., min_length=2),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    like = f"%{q}%"
    query = db.query(NewsArticle).filter(
        or_(NewsArticle.headline.ilike(like), NewsArticle.summary.ilike(like))
    ).order_by(NewsArticle.published_at.desc())
    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()
    return NewsListResponse(items=items, page=page, page_size=page_size, total=total)