from pydantic import BaseModel
from datetime import datetime


class WatchlistItemCreate(BaseModel):
    symbol: str


class WatchlistItemResponse(BaseModel):
    id: int
    symbol: str
    added_at: datetime

    model_config = {"from_attributes": True}


class WatchlistCreate(BaseModel):
    name: str


class WatchlistUpdate(BaseModel):
    name: str


class WatchlistResponse(BaseModel):
    id: int
    user_id: int
    name: str
    items: list[WatchlistItemResponse] = []
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class WatchlistListResponse(BaseModel):
    id: int
    user_id: int
    name: str
    item_count: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
