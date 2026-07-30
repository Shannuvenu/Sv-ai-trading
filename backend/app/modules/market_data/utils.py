from sqlalchemy.orm import Session
from app.modules.market_data.provider import MarketDataProvider
from app.modules.market_data.mock_provider import get_market_data_provider


def resolve_market_provider(db: Session) -> MarketDataProvider:
    from app.core.config import get_settings
    settings = get_settings()
    provider_type = settings.MARKET_DATA_PROVIDER.strip()

    if provider_type == "upstox":
        from app.modules.market_data.upstox_provider import get_upstox_provider
        provider = get_upstox_provider()
        if provider and provider._configured:
            return provider

    if provider_type == "simulated":
        return get_market_data_provider()

    # Default: mock provider
    return get_market_data_provider()
