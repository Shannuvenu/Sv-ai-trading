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
    commission_pct: float = 0.0,
    slippage_pct: float = 0.001,
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
    entry_price = 0.0
    equity_curve: list[dict] = []
    trades: list[dict] = []
    position = False

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
        latest_close = indicators.get("latest_close")

        bar = bars[i]
        price = float(bar.close)

        direction = SignalDirection.HOLD
        buy_signal = False
        sell_signal = False

        if rsi_val is not None and macd_l is not None and macd_s is not None:
            # BUY: momentum improving (MACD crossing positive OR rising), RSI not overbought
            if macd_l > macd_s and rsi_val < 55:
                buy_signal = True
            # SELL: momentum weakening (MACD crossing negative OR falling), RSI not oversold
            elif macd_l < macd_s and rsi_val > 50:
                sell_signal = True

            # Secondary condition: price crosses SMA 20
            if sma_20 is not None and latest_close is not None:
                if latest_close > sma_20 and macd_l > macd_s:
                    buy_signal = True
                elif latest_close < sma_20 and macd_l < macd_s:
                    sell_signal = True

        # Compute slippaged price for execution
        slippage_factor = slippage_pct
        comm_factor = commission_pct / 100.0 if commission_pct > 1 else commission_pct

        if buy_signal and not position and cash > 0:
            ep = price * (1 + slippage_factor)
            amount = cash * position_size_pct
            qty = int(amount / ep)
            cost = qty * ep * (1 + comm_factor)
            if qty > 0 and cost <= cash:
                cash -= cost
                shares = qty
                entry_price = price
                position = True
                trades.append({
                    "timestamp": bar.timestamp.isoformat(),
                    "side": "BUY",
                    "price": round(price, 2),
                    "quantity": qty,
                    "cost": round(cost, 2),
                })

        elif sell_signal and position and shares > 0:
            xp = price * (1 - slippage_factor)
            proceeds = shares * xp * (1 - comm_factor)
            trades.append({
                "timestamp": bar.timestamp.isoformat(),
                "side": "SELL",
                "price": round(price, 2),
                "quantity": shares,
                "proceeds": round(proceeds, 2),
            })
            cash += proceeds
            shares = 0
            position = False
            entry_price = 0.0

        equity = cash + shares * price
        equity_curve.append({
            "timestamp": bar.timestamp.isoformat(),
            "equity": round(equity, 2),
            "price": price,
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

    sell_trades = [t for t in trades if t.get("side") == "SELL"]
    winning = sum(1 for t in sell_trades if t.get("proceeds", 0) > 0)
    losing = sum(1 for t in sell_trades if t.get("proceeds", 0) <= 0)
    win_rate = winning / max(len(sell_trades), 1)

    gross_profit = sum(t.get("proceeds", 0) for t in sell_trades if t.get("proceeds", 0) > 0)
    gross_loss = abs(sum(t.get("proceeds", 0) for t in sell_trades if t.get("proceeds", 0) < 0))
    profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else (float('inf') if gross_profit > 0 else 0.0)
    if profit_factor == float('inf'):
        profit_factor = 999.99

    from app.modules.backtest.engine import _sharpe_ratio, _sortino_ratio
    sharpe = _sharpe_ratio(returns_series) if len(returns_series) >= 2 else None
    sortino = _sortino_ratio(returns_series) if len(returns_series) >= 2 else None

    peak = equity_values[0] if equity_values else initial_capital
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
