from sqlalchemy.orm import Session
from app.modules.market_data.provider import MarketDataProvider
from app.modules.market_data.mock_provider import get_market_data_provider, MockMarketDataProvider
from app.modules.market_data.db_provider import DatabaseMarketDataProvider


def resolve_market_provider(db: Session) -> MarketDataProvider:
    provider = DatabaseMarketDataProvider(db)
    instruments = provider.get_all_instruments()
    if not instruments:
        return get_market_data_provider()
    return provider
