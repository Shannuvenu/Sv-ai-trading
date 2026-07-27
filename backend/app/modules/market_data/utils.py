from sqlalchemy.orm import Session
from app.modules.market_data.provider import MarketDataProvider
from app.modules.market_data.mock_provider import get_market_data_provider
from app.modules.market_data.db_provider import DatabaseMarketDataProvider


def resolve_market_provider(db: Session) -> MarketDataProvider:
    from app.core.config import get_settings
    settings = get_settings()
    provider_type = settings.MARKET_DATA_PROVIDER.strip()

    if provider_type == "upstox":
        from app.modules.market_data.upstox_provider import get_upstox_provider
        provider = get_upstox_provider()
        if provider and provider._configured:
            # Try Upstox first; fall back to DB if quote fails
            test_quote = provider.get_quote("TCS")
            if test_quote is not None:
                return provider

    if provider_type == "simulated":
        return get_market_data_provider()

    # Default: DB-backed provider
    provider = DatabaseMarketDataProvider(db)
    instruments = provider.get_all_instruments()
    if not instruments:
        return get_market_data_provider()
    return provider
