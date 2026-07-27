"""
WebSocket endpoint for frontend to receive real-time market data.
Browser connects here, subscribes to symbols, receives normalized JSON updates.
"""
import asyncio
import json
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = logging.getLogger("ws_market")

router = APIRouter()


class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []
        self._subscribed_symbols: set[str] = set()
        self._poll_task: asyncio.Task | None = None

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        if len(self.active_connections) == 1:
            self._start_polling()

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        if len(self.active_connections) == 0:
            self._stop_polling()

    async def broadcast(self, message: dict):
        dead = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                dead.append(connection)
        for d in dead:
            self.active_connections.remove(d)

    def _start_polling(self):
        if self._poll_task is None or self._poll_task.done():
            self._poll_task = asyncio.create_task(self._poll_loop())

    def _stop_polling(self):
        if self._poll_task:
            self._poll_task.cancel()
            self._poll_task = None

    async def _poll_loop(self):
        from app.modules.market_data.upstox_provider import get_upstox_provider
        from app.modules.market_data.upstox_instruments import UPSTOX_INSTRUMENTS

        provider = get_upstox_provider()
        if not provider or not provider._configured:
            return

        symbols = [i["symbol"] for i in UPSTOX_INSTRUMENTS]
        while True:
            try:
                for symbol in symbols:
                    quote = provider.get_quote(symbol)
                    if quote:
                        await self.broadcast({
                            "type": "quote",
                            "symbol": symbol,
                            "last_price": float(quote.last_price),
                            "change": float(quote.change),
                            "change_pct": float(quote.change_pct),
                            "volume": quote.volume,
                            "timestamp": quote.timestamp.isoformat(),
                            "source": "UPSTOX",
                        })
                await asyncio.sleep(2)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Poll error: {e}")
                await asyncio.sleep(5)


manager = ConnectionManager()


@router.websocket("/ws/market")
async def market_websocket(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)
            if msg.get("action") == "subscribe" and "symbols" in msg:
                symbols = msg["symbols"]
                await websocket.send_json({
                    "type": "subscribed",
                    "symbols": symbols,
                    "source": "UPSTOX",
                })
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception:
        manager.disconnect(websocket)
