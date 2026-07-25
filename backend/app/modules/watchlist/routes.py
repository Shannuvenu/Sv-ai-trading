from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user
from app.modules.users.models import User
from app.modules.watchlist.models import Watchlist, WatchlistItem
from app.modules.watchlist.schemas import (
    WatchlistCreate,
    WatchlistUpdate,
    WatchlistResponse,
    WatchlistListResponse,
    WatchlistItemCreate,
    WatchlistItemResponse,
)

router = APIRouter(prefix="/watchlists", tags=["Watchlists"])


@router.post("", response_model=WatchlistResponse, status_code=status.HTTP_201_CREATED)
def create_watchlist(
    payload: WatchlistCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    wl = Watchlist(user_id=current_user.id, name=payload.name)
    db.add(wl)
    db.commit()
    db.refresh(wl)
    return wl


@router.get("", response_model=list[WatchlistListResponse])
def list_watchlists(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    watchlists = db.query(Watchlist).filter(Watchlist.user_id == current_user.id).all()
    return [
        WatchlistListResponse(
            id=w.id,
            user_id=w.user_id,
            name=w.name,
            item_count=len(w.items),
            created_at=w.created_at,
            updated_at=w.updated_at,
        )
        for w in watchlists
    ]


@router.get("/{watchlist_id}", response_model=WatchlistResponse)
def get_watchlist(
    watchlist_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    wl = db.query(Watchlist).filter(Watchlist.id == watchlist_id).first()
    if not wl:
        raise HTTPException(status_code=404, detail="Watchlist not found")
    if wl.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    return wl


@router.patch("/{watchlist_id}", response_model=WatchlistResponse)
def update_watchlist(
    watchlist_id: int,
    payload: WatchlistUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    wl = db.query(Watchlist).filter(Watchlist.id == watchlist_id).first()
    if not wl:
        raise HTTPException(status_code=404, detail="Watchlist not found")
    if wl.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    wl.name = payload.name
    db.commit()
    db.refresh(wl)
    return wl


@router.delete("/{watchlist_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_watchlist(
    watchlist_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    wl = db.query(Watchlist).filter(Watchlist.id == watchlist_id).first()
    if not wl:
        raise HTTPException(status_code=404, detail="Watchlist not found")
    if wl.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    db.delete(wl)
    db.commit()


@router.post("/{watchlist_id}/items", response_model=WatchlistItemResponse, status_code=status.HTTP_201_CREATED)
def add_watchlist_item(
    watchlist_id: int,
    payload: WatchlistItemCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    wl = db.query(Watchlist).filter(Watchlist.id == watchlist_id).first()
    if not wl:
        raise HTTPException(status_code=404, detail="Watchlist not found")
    if wl.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    existing = db.query(WatchlistItem).filter(
        WatchlistItem.watchlist_id == watchlist_id,
        WatchlistItem.symbol == payload.symbol.upper(),
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Symbol already in watchlist")

    item = WatchlistItem(watchlist_id=watchlist_id, symbol=payload.symbol.upper())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.delete("/{watchlist_id}/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_watchlist_item(
    watchlist_id: int,
    item_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    wl = db.query(Watchlist).filter(Watchlist.id == watchlist_id).first()
    if not wl:
        raise HTTPException(status_code=404, detail="Watchlist not found")
    if wl.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    item = db.query(WatchlistItem).filter(
        WatchlistItem.id == item_id,
        WatchlistItem.watchlist_id == watchlist_id,
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    db.delete(item)
    db.commit()
