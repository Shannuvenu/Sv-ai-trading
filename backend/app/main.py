import time
import asyncio
import threading
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import get_settings
from app.core.database import Base, engine, SessionLocal
from app.modules.users.routes import router as users_router
from app.modules.market_data.routes import router as market_router
from app.modules.market_data.ws_routes import router as market_ws_router
from app.modules.watchlist.routes import router as watchlist_router
from app.modules.portfolio.routes import router as portfolio_router
from app.modules.portfolio.analytics_routes import router as portfolio_analytics_router
from app.modules.technical_analysis.routes import router as analysis_router
from app.modules.backtest.routes import router as backtest_router
from app.modules.risk.routes import router as risk_router
from app.modules.alerts.routes import router as alerts_router
from app.modules.market_data.index_routes import router as index_router
from app.modules.calculators.routes import router as calc_router
from app.modules.ai_trader.routes import router as ai_router
from app.modules.news.routes import router as news_router
# from app.modules.ai_trader.ai_routes import router as ai_intelligence_router
from app.modules.market_data.fundamentals_routes import router as fundamentals_router
from app.modules.market_data.extended_routes import router as market_extended_router
from app.modules.market_data.chart_routes import router as chart_router
from app.modules.market_data.pine_routes import router as pine_router
from scripts.seed import seed_all

settings = get_settings()

app = FastAPI(title=settings.APP_NAME, version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(users_router)
app.include_router(market_router)
app.include_router(market_ws_router)
app.include_router(watchlist_router)
app.include_router(portfolio_router)
app.include_router(portfolio_analytics_router)
app.include_router(analysis_router)
app.include_router(backtest_router)
app.include_router(risk_router)
app.include_router(alerts_router)
app.include_router(index_router)
app.include_router(calc_router)
app.include_router(ai_router)
app.include_router(news_router)
# app.include_router(ai_intelligence_router)
app.include_router(fundamentals_router)
app.include_router(market_extended_router)
app.include_router(chart_router)
app.include_router(pine_router)


def _start_upstox_ws():
    if settings.MARKET_DATA_PROVIDER != "upstox":
        return
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    from app.modules.market_data.upstox_provider import get_upstox_provider
    provider = get_upstox_provider()
    if provider and provider._configured:
        loop.run_until_complete(provider.poll_loop())


@app.on_event("startup")
def startup():
    engine.dispose()
    max_retries = 30
    for i in range(max_retries):
        try:
            Base.metadata.create_all(bind=engine)
            db = SessionLocal()
            try:
                seed_all(db)
                print("Database initialized and seeded successfully.")
                break
            finally:
                db.close()
        except Exception as e:
            if i == max_retries - 1:
                raise
            print(f"Database connection attempt {i+1}/{max_retries} failed: {e}, retrying...")
            time.sleep(2)
            engine.dispose()

    # Upstox polling disabled - use on-demand quotes only
    # if settings.MARKET_DATA_PROVIDER == "upstox":
    #     t = threading.Thread(target=_start_upstox_ws, daemon=True)
    #     t.start()
    #     print("Upstox WebSocket feeder started in background.")


@app.get("/")
def root():
    return {"name": settings.APP_NAME, "status": "running"}


@app.get("/health")
def health():
    provider_type = settings.MARKET_DATA_PROVIDER
    provider_status = "configured" if settings.UPSTOX_ACCESS_TOKEN else "not_configured"
    return {
        "status": "healthy",
        "market_data_provider": provider_type,
        "upstox": provider_status,
    }
