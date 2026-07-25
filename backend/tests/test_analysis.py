import pytest
from decimal import Decimal
from app.modules.technical_analysis.indicators import sma, ema, rsi, compute_indicators
from app.modules.market_data.mock_provider import get_market_data_provider


def test_sma_calculation():
    values = [10.0, 20.0, 30.0, 40.0, 50.0]
    result = sma(values, 3)
    assert result[0] is None
    assert result[1] is None
    assert result[2] == 20.0  # (10+20+30)/3
    assert result[3] == 30.0  # (20+30+40)/3
    assert result[4] == 40.0  # (30+40+50)/3


def test_ema_calculation():
    values = [10.0, 12.0, 14.0]
    result = ema(values, 3)
    assert len(result) == 3


def test_rsi_oversold():
    import numpy as np
    values = list(range(100, 50, -2))
    result = rsi(values, 14)
    last_rsi = next((v for v in reversed(result) if v is not None), None)
    assert last_rsi is not None
    assert last_rsi < 30


def test_rsi_overbought():
    values = list(range(50, 100, 2))
    result = rsi(values, 14)
    last_rsi = next((v for v in reversed(result) if v is not None), None)
    assert last_rsi is not None
    assert last_rsi > 70


def test_compute_indicators_with_data():
    provider = get_market_data_provider()
    bars = provider.get_history("RELIANCE")
    closes = [b.close for b in bars]
    highs = [b.high for b in bars]
    lows = [b.low for b in bars]
    volumes = [b.volume for b in bars]

    ind = compute_indicators(closes, highs, lows, volumes)
    assert ind["sma_20"] is not None
    assert ind["rsi_14"] is not None
    assert "macd_line" in ind


def test_analysis_endpoint():
    from tests.conftest import client
    resp = client.get("/analysis/TCS?days=100")
    assert resp.status_code == 200
    data = resp.json()
    assert data["symbol"] == "TCS"
    assert "indicators" in data
    assert "signal" in data
    assert "explanation" in data
    assert data["signal"]["direction"] in ["BUY", "SELL", "HOLD"]


def test_analysis_insufficient_data():
    from tests.conftest import client
    resp = client.get("/analysis/TCS?days=5")
    assert resp.status_code == 422
