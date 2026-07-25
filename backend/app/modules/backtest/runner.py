from datetime import datetime, timezone
from decimal import Decimal
from app.modules.backtest.engine import BacktestResult, TradeSide
from app.modules.market_data.provider import OHLCVBar
from app.modules.technical_analysis.indicators import compute_indicators
from app.modules.signals.engine import Signal, SignalDirection


def run_backtest(
    symbol: str,
    bars: list[OHLCVBar],
    initial_capital: float = 100000.0,
    position_size_pct: float = 0.2,
    commission: float = 0.0,
    slippage: float = 0.001,
) -> BacktestResult:
    if len(bars) < 50:
        return BacktestResult(
            total_return=0, total_return_pct=0, num_trades=0,
            winning_trades=0, losing_trades=0, win_rate=0,
            profit_factor=0, sharpe_ratio=None, sortino_ratio=None,
            max_drawdown_pct=0, initial_capital=initial_capital,
            final_equity=initial_capital,
        )

    cash = initial_capital
    shares = 0
    equity_curve: list[dict] = []
    trades: list[dict] = []
    prev_signal_direction = SignalDirection.HOLD

    closes = [b.close for b in bars]
    highs = [b.high for b in bars]
    lows = [b.low for b in bars]
    volumes = [b.volume for b in bars]

    for i in range(50, len(bars)):
        window_close = closes[i - 50:i + 1]
        window_high = highs[i - 50:i + 1]
        window_low = lows[i - 50:i + 1]
        window_vol = volumes[i - 50:i + 1]

        indicators = compute_indicators(window_close, window_high, window_low, window_vol)

        rsi_val = indicators.get("rsi_14")
        macd_l = indicators.get("macd_line")
        macd_s = indicators.get("macd_signal")
        sma_20 = indicators.get("sma_20")
        sma_50 = indicators.get("sma_50")
        latest_close = indicators.get("latest_close")

        direction = SignalDirection.HOLD
        if rsi_val is not None and macd_l is not None and macd_s is not None:
            if rsi_val < 30 and macd_l > macd_s:
                direction = SignalDirection.BUY
            elif rsi_val > 70 and macd_l < macd_s:
                direction = SignalDirection.SELL

        bar = bars[i]
        price = float(bar.close)
        entry_price = price * (1 + slippage)

        if direction == SignalDirection.BUY and prev_signal_direction != SignalDirection.BUY and cash > 0:
            amount = cash * position_size_pct
            qty = int(amount / entry_price)
            cost = qty * entry_price * (1 + commission / 100)
            if qty > 0 and cost <= cash:
                cash -= cost
                shares += qty
                trades.append({
                    "timestamp": bar.timestamp.isoformat(),
                    "side": "BUY",
                    "price": round(price, 2),
                    "quantity": qty,
                    "cost": round(cost, 2),
                })

        elif direction == SignalDirection.SELL and shares > 0:
            exit_price = price * (1 - slippage)
            proceeds = shares * exit_price * (1 - commission / 100)
            profit = proceeds - 0
            trades.append({
                "timestamp": bar.timestamp.isoformat(),
                "side": "SELL",
                "price": round(price, 2),
                "quantity": shares,
                "proceeds": round(proceeds, 2),
            })
            cash += proceeds
            shares = 0

        prev_signal_direction = direction

        equity = cash + shares * float(bar.close)
        equity_curve.append({
            "timestamp": bar.timestamp.isoformat(),
            "equity": round(equity, 2),
            "price": float(bar.close),
        })

    if shares > 0:
        final_price = float(bars[-1].close)
        cash += shares * final_price
        shares = 0

    final_equity = cash

    equity_values = [e["equity"] for e in equity_curve]
    returns_series = []
    for i in range(1, len(equity_values)):
        if equity_values[i - 1] > 0:
            returns_series.append((equity_values[i] - equity_values[i - 1]) / equity_values[i - 1])

    total_return = final_equity - initial_capital
    total_return_pct = (total_return / initial_capital) * 100

    winning = sum(1 for t in trades if t.get("side") == "SELL" and t.get("proceeds", 0) > 0)
    losing = sum(1 for t in trades if t.get("side") == "SELL" and t.get("proceeds", 0) <= 0)
    win_rate = winning / max(winning + losing, 1)

    gross_profit = sum(t.get("proceeds", 0) for t in trades if t.get("side") == "SELL" and t.get("proceeds", 0) > 0)
    gross_loss = abs(sum(t.get("proceeds", 0) for t in trades if t.get("side") == "SELL" and t.get("proceeds", 0) < 0))
    profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else 0.0

    from app.modules.backtest.engine import _sharpe_ratio, _sortino_ratio
    sharpe = _sharpe_ratio(returns_series) if returns_series else None
    sortino = _sortino_ratio(returns_series) if returns_series else None

    peak = equity_values[0]
    max_dd = 0.0
    for v in equity_values:
        if v > peak:
            peak = v
        dd = (peak - v) / peak * 100 if peak > 0 else 0
        if dd > max_dd:
            max_dd = dd

    return BacktestResult(
        total_return=total_return,
        total_return_pct=total_return_pct,
        num_trades=len(trades),
        winning_trades=winning,
        losing_trades=losing,
        win_rate=win_rate,
        profit_factor=profit_factor,
        sharpe_ratio=sharpe,
        sortino_ratio=sortino,
        max_drawdown_pct=max_dd,
        initial_capital=initial_capital,
        final_equity=final_equity,
        equity_curve=equity_curve,
        trades=trades,
    )
