"""Finnhub fundamentals service — company profile, financials."""
import logging
import httpx
from app.core.config import get_settings

settings = get_settings()
logger = logging.getLogger("finnhub_fundamentals")

BASE_URL = "https://finnhub.io/api/v1"


class FinnhubFundamentalsClient:
    def __init__(self):
        self._api_key = settings.FINNHUB_API_KEY.strip()
        self._configured = bool(self._api_key)
        self._http = httpx.Client(timeout=10.0)

    @property
    def is_configured(self) -> bool:
        return self._configured

    def get_company_profile(self, symbol: str) -> dict | None:
        if not self._configured:
            return None
        try:
            resp = self._http.get(
                f"{BASE_URL}/stock/profile2",
                params={"symbol": symbol, "token": self._api_key},
            )
            resp.raise_for_status()
            data = resp.json()
            if not data or not data.get("name"):
                return None
            return {
                "name": data.get("name"),
                "country": data.get("country"),
                "currency": data.get("currency"),
                "exchange": data.get("exchange"),
                "finnhub_industry": data.get("finnhubIndustry"),
                "market_capitalization": data.get("marketCapitalization"),  # in millions
                "ipo": data.get("ipo"),
                "logo": data.get("logo"),
                "weburl": data.get("weburl"),
                "phone": data.get("phone"),
                "share_outstanding": data.get("shareOutstanding"),
            }
        except Exception as e:
            logger.error(f"Company profile failed for {symbol}: {e}")
            return None

    def get_basic_financials(self, symbol: str) -> dict | None:
        """Get basic financial metrics from Finnhub."""
        if not self._configured:
            return None
        try:
            resp = self._http.get(
                f"{BASE_URL}/stock/metric",
                params={"symbol": symbol, "metric": "all", "token": self._api_key},
            )
            resp.raise_for_status()
            data = resp.json()
            metric = data.get("metric", {})
            if not metric:
                return None
            return {
                "pe_annual": metric.get("peAnnual"),
                "pe_basic_excl_extra_ttm": metric.get("peBasicExclExtraTTM"),
                "eps_basic_excl_extra_ttm": metric.get("epsBasicExclExtraTTM"),
                "dividend_yield_indicated_annual": metric.get("dividendYieldIndicatedAnnual"),
                "book_value_per_share_annual": metric.get("bookValuePerShareAnnual"),
                "total_debt_total_equity_annual": metric.get("totalDebt/totalEquityAnnual"),
                "return_on_equity_ttm": metric.get("roeTTM"),
                "return_on_assets_ttm": metric.get("roaTTM"),
                "net_profit_margin_ttm": metric.get("netProfitMarginTTM"),
                "revenue_per_share_ttm": metric.get("revenuePerShareTTM"),
                "cash_flow_per_share_annual": metric.get("cashFlowPerShareAnnual"),
                "current_ratio_annual": metric.get("currentRatioAnnual"),
                "pb_annual": metric.get("pbAnnual"),
                "eps_growth_5y": metric.get("epsGrowth5Y"),
                "revenue_growth_5y": metric.get("revenueGrowth5Y"),
                "ebit_per_share_ttm": metric.get("ebitPerShareTTM"),
                "gross_margin_ttm": metric.get("grossMarginTTM"),
                "operating_margin_ttm": metric.get("operatingMarginTTM"),
                "total_assets_annual": metric.get("totalAssetsAnnual"),
                "total_debt_annual": metric.get("totalDebtAnnual"),
                "revenue_ttm": metric.get("revenueTTM"),
                "52_week_high": metric.get("52WeekHigh"),
                "52_week_low": metric.get("52WeekLow"),
                "52_week_high_date": metric.get("52WeekHighDate"),
                "52_week_low_date": metric.get("52WeekLowDate"),
            }
        except Exception as e:
            logger.error(f"Financial metrics failed for {symbol}: {e}")
            return None

    def get_peers(self, symbol: str) -> list[str]:
        """Get peer companies for a symbol."""
        if not self._configured:
            return []
        try:
            resp = self._http.get(
                f"{BASE_URL}/stock/peers",
                params={"symbol": symbol, "token": self._api_key},
            )
            resp.raise_for_status()
            return resp.json() or []
        except Exception as e:
            logger.error(f"Peers failed for {symbol}: {e}")
            return []


_client: "FinnhubFundamentalsClient | None" = None


def get_fundamentals_client() -> FinnhubFundamentalsClient:
    global _client
    if _client is None:
        _client = FinnhubFundamentalsClient()
    return _client
