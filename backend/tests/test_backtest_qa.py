"""Backtest financial-correctness QA tests."""
from app.modules.market_data.backtest_engine import run_backtest


def _d(opens, highs=None, lows=None):
    oc = [opens[0]] * 60
    hc = [(highs[0] if highs else opens[0] + 1)] * 60
    lc = [(lows[0] if lows else opens[0] - 1)] * 60
    for i in range(min(len(opens), 60)):
        oc[-1 - i] = opens[-(1 + i)]
    if highs:
        for i in range(min(len(highs), 60)):
            hc[-1 - i] = highs[-(1 + i)]
    if lows:
        for i in range(min(len(lows), 60)):
            lc[-1 - i] = lows[-(1 + i)]
    return {"open": oc, "high": hc, "low": lc, "close": oc, "volume": [10**6]*60, "time": [f"T{i:02d}" for i in range(60)]}


FS = "indicator(\"F\")\nbuy=close>0\nsell=close<0\nplotshape(buy)\nplotshape(sell)"
BS = "indicator(\"BT\")\nbuy=crossover(ema(close,20),ema(close,50))\nsell=crossunder(ema(close,20),ema(close,50))\nplotshape(buy)\nplotshape(sell)"


def test_sl():
    r = run_backtest(_d([100, 100], [101, 101], [99, 94]), FS, stop_loss_pct=5, take_profit_pct=99, commission_pct=0)
    assert any(t.get("exit_reason") == "STOP_LOSS" for t in r["trades"])


def test_tp():
    r = run_backtest(_d([100, 100], [101, 106], [99, 99]), FS, take_profit_pct=5, stop_loss_pct=99, commission_pct=0)
    assert any(t.get("exit_reason") == "TAKE_PROFIT" for t in r["trades"])


def test_same_candle():
    r = run_backtest(_d([100, 100], [106, 106], [94, 99]), FS, stop_loss_pct=5, take_profit_pct=5, commission_pct=0)
    sl = [t for t in r["trades"] if t.get("exit_reason") == "STOP_LOSS"]
    tp = [t for t in r["trades"] if t.get("exit_reason") == "TAKE_PROFIT"]
    assert len(sl) >= 1


def test_commission():
    r = run_backtest(_d([100, 110]), FS, commission_pct=1.0, stop_loss_pct=99)
    t = r["trades"][0]
    assert t["total_fees"] > 0
    assert abs(t["gross_pnl"] - t["net_pnl"] - t["total_fees"]) < 0.01


def test_sizing():
    r = run_backtest(_d([100, 110]), FS, initial_capital=100000, position_size_pct=10, stop_loss_pct=99, commission_pct=0)
    cost = r["trades"][0]["entry_price"] * r["trades"][0]["quantity"]
    assert cost <= 10010


def test_no_signal():
    r = run_backtest(_d([100]*60), "indicator(\"none\")\nplot(close)")
    assert r.get("trades") is not None


def test_lookahead():
    a = _d([100]*50 + [105]*50)
    b = _d([100]*50 + [105]*50 + [200]*50)
    assert run_backtest(a, BS)["total_trades"] == run_backtest(b, BS)["total_trades"]


def test_real():
    from app.modules.market_data.upstox_provider import get_upstox_provider
    p = get_upstox_provider()
    if not p or not p._configured: return
    bars = p.get_history("RELIANCE", days=200)
    ohlc = {"open": [float(b.open) for b in bars], "high": [float(b.high) for b in bars], "low": [float(b.low) for b in bars], "close": [float(b.close) for b in bars], "volume": [int(b.volume) for b in bars], "time": [b.timestamp.isoformat() for b in bars]}
    r = run_backtest(ohlc, BS)
    assert r["error"] is None

