from decimal import Decimal
from app.modules.signals.engine import generate_signal, Signal, SignalDirection


def make_indicators(**overrides):
    base = {
        "rsi_14": 50.0,
        "macd_line": 0.0,
        "macd_signal": 0.0,
        "sma_20": 100.0,
        "sma_50": 90.0,
        "latest_close": 105.0,
        "bb_upper": 110.0,
        "bb_lower": 90.0,
        "bb_middle": 100.0,
        "latest_volume": 1000000.0,
        "volume_sma_20": 1000000.0,
    }
    base.update(overrides)
    return base


def test_oversold_buy_signal():
    ind = make_indicators(rsi_14=25.0, macd_line=2.0, macd_signal=1.0)
    signal = generate_signal("TEST", ind)
    assert signal.direction == SignalDirection.BUY
    assert signal.confidence > 0.6


def test_overbought_sell_signal():
    ind = make_indicators(rsi_14=75.0, macd_line=-1.0, macd_signal=-0.5)
    signal = generate_signal("TEST", ind)
    assert signal.direction == SignalDirection.SELL
    assert signal.confidence > 0.6


def test_neutral_hold_signal():
    ind = make_indicators(rsi_14=50.0, macd_line=0.0, macd_signal=0.0, sma_20=100.0, sma_50=105.0, latest_close=102.0)
    signal = generate_signal("TEST", ind)
    assert signal.direction == SignalDirection.HOLD


def test_signal_has_reasoning():
    ind = make_indicators(rsi_14=28.0, macd_line=2.0, macd_signal=1.0)
    signal = generate_signal("RELIANCE", ind)
    assert len(signal.reasoning) > 0
    assert all(isinstance(r, str) for r in signal.reasoning)


def test_explanation_consistency():
    from app.modules.explainability.explainer import explain_signal
    ind = make_indicators(rsi_14=28.0, macd_line=2.0, macd_signal=1.0)
    signal = generate_signal("RELIANCE", ind)
    explanation = explain_signal(signal.to_dict())
    assert explanation["direction"] == signal.direction.value
    assert explanation["confidence"] == signal.confidence
    assert len(explanation["reasoning"]) > 0


def test_backtest_endpoint():
    from tests.conftest import client
    resp = client.post("/backtest?days=200", json={
        "symbol": "INFY", "initial_capital": 100000.0,
        "position_size_pct": 0.2, "commission": 0.1, "slippage": 0.001,
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "total_return_pct" in data
    assert "win_rate" in data
    assert "sharpe_ratio" in data
    assert "max_drawdown_pct" in data
    assert "equity_curve" in data
    assert len(data["equity_curve"]) > 0
