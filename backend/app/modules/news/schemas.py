from pydantic import BaseModel
from datetime import datetime


class NewsArticleResponse(BaseModel):
    id: int
    category: str
    symbol: str | None
    headline: str
    summary: str | None
    source: str | None
    url: str | None
    image_url: str | None
    published_at: datetime | None

    model_config = {"from_attributes": True}


class NewsListResponse(BaseModel):
    items: list[NewsArticleResponse]
    page: int
    page_size: int
    total: int