"""
Backtest engine — runs Pine strategies against historical OHLCV.
No future-data look-ahead. Uses existing Pine interpreter.
Produces reproducible trade metrics.
"""
import logging
import math
from datetime import datetime, timezone
from app.modules.market_data.pine_interpreter import PineInterpreter

logger = logging.getLogger("backtest_engine")


def run_backtest(
    ohlc: dict,
    script: str,
    initial_capital: float = 100000.0,
    position_size_pct: float = 20.0,
    stop_loss_pct: float = 3.0,
    take_profit_pct: float = 6.0,
    commission_pct: float = 0.1,
) -> dict:
    """
    Run a backtest against historical OHLCV data.

    ohlc: {"open":[..],"high":[..],"low":[..],"close":[..],"volume":[..],"time":[..str..]}
    script: Pine script string with indicator() or strategy()
    """
    n = len(ohlc["close"])
    if n < 50:
        return {"error": "Insufficient data (need 50+ candles)", "trades": [], "metrics": {}}

    # Step 1: Run Pine interpreter to get signals
    interpreter = PineInterpreter(ohlc)
    result = interpreter.execute(script)
    if result.errors:
        return {"error": result.errors[0], "trades": [], "metrics": {}}

    # Step 2: Extract buy/sell signals from shapes
    shapes = result.shapes  # each shape has .data with {time, value: bool} per candle
    if not shapes:
        return {"error": "No plotshape() signals found in script", "trades": [], "metrics": {}}

    # Normalize: find all buy signals and sell signals
    times = ohlc["time"]
    closes = ohlc["close"]
    highs = ohlc["high"]
    lows = ohlc["low"]
    opens_raw = ohlc["open"]

    buy_indices = set()
    sell_indices = set()
    for shape in shapes:
        for i, pt in enumerate(shape.get("data", [])):
            if pt.get("value"):
                title = (shape.get("title") or "").lower()
                if "buy" in title or "long" in title or "entry" in title:
                    buy_indices.add(i)
                elif "sell" in title or "short" in title or "exit" in title:
                    sell_indices.add(i)
                else:
                    buy_indices.add(i)  # default: first shape = buy

    all_signal_indices = sorted(buy_indices | sell_indices)
    if not all_signal_indices:
        return {"error": "No buy/sell signals generated", "trades": [], "metrics": {}}

    # Step 3: Simulate trades chronologically
    capital = initial_capital
    position = 0  # 0 = flat, 1 = holding
    entry_price = 0
    trades = []
    equity_curve = []

    for i in range(n):
        equity_curve.append({
            "time": times[i],
            "equity": capital + (position * closes[i] if position > 0 else 0),
        })

        if i not in buy_indices and i not in sell_indices:
            continue
        if i not in all_signal_indices:
            continue

        is_buy = i in buy_indices
        is_sell = i in sell_indices

        if is_buy and position == 0:
            # Execute buy
            price = closes[i]  # buy at close
            trade_capital = capital * (position_size_pct / 100)
            qty = int(trade_capital / price)
            if qty <= 0:
                continue
            cost = qty * price
            commission = cost * (commission_pct / 100)
            capital -= (cost + commission)
            position = qty
            entry_price = price
            sl = entry_price * (1 - stop_loss_pct / 100)
            tp = entry_price * (1 + take_profit_pct / 100)
            trades.append({
                "id": len(trades) + 1,
                "symbol": "N/A",
                "side": "BUY",
                "entry_time": times[i],
                "entry_price": round(price, 2),
                "quantity": qty,
                "stop_loss": round(sl, 2),
                "take_profit": round(tp, 2),
                "fees": round(commission, 2),
            })

        elif is_sell and position > 0:
            # Execute sell
            price = closes[i]
            proceeds = position * price
            commission = proceeds * (commission_pct / 100)
            capital += (proceeds - commission)
            pnl = (price - entry_price) * position
            net_pnl = pnl - commission
            return_pct = ((price - entry_price) / entry_price * 100) if entry_price > 0 else 0
            trades[-1].update({
                "exit_time": times[i],
                "exit_price": round(price, 2),
                "gross_pnl": round(pnl, 2),
                "fees": round(commission, 2),
                "net_pnl": round(net_pnl, 2),
                "return_pct": round(return_pct, 2),
                "exit_reason": "SIGNAL",
            })
            position = 0
            entry_price = 0

    # Close any remaining open position at last price
    if position > 0:
        last_price = closes[-1]
        proceeds = position * last_price
        commission = proceeds * (commission_pct / 100)
        capital += (proceeds - commission)
        pnl = (last_price - entry_price) * position
        net_pnl = pnl - commission
        trades[-1].update({
            "exit_time": times[-1],
            "exit_price": round(last_price, 2),
            "gross_pnl": round(pnl, 2),
            "fees": round(commission, 2),
            "net_pnl": round(net_pnl, 2),
            "return_pct": round(((last_price - entry_price) / entry_price * 100), 2) if entry_price > 0 else 0,
            "exit_reason": "END_OF_DATA",
        })

    # Metrics
    final_capital = capital
    net_pnl = final_capital - initial_capital
    total_return_pct = (net_pnl / initial_capital * 100) if initial_capital > 0 else 0
    completed_trades = [t for t in trades if "exit_price" in t]
    winning = [t for t in completed_trades if t["net_pnl"] > 0]
    losing = [t for t in completed_trades if t["net_pnl"] <= 0]
    total_trades = len(completed_trades) or 1
    win_rate = len(winning) / total_trades * 100 if total_trades > 0 else 0
    gross_profit = sum(t["net_pnl"] for t in winning) if winning else 0
    gross_loss = abs(sum(t["net_pnl"] for t in losing)) if losing else 0
    profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else (999 if gross_profit > 0 else 0)

    # Max drawdown
    peak = initial_capital
    max_dd = 0.0
    for eq in equity_curve:
        if eq["equity"] > peak:
            peak = eq["equity"]
        dd = (peak - eq["equity"]) / peak * 100 if peak > 0 else 0
        if dd > max_dd:
            max_dd = dd

    # Sharpe
    import statistics
    daily_returns = []
    for i in range(1, len(equity_curve)):
        prev = equity_curve[i - 1]["equity"]
        curr = equity_curve[i]["equity"]
        if prev > 0:
            daily_returns.append((curr - prev) / prev)
    sharpe = None
    if len(daily_returns) > 10:
        avg = statistics.mean(daily_returns)
        std = statistics.stdev(daily_returns)
        if std > 0:
            sharpe = round((avg * math.sqrt(252)) / std, 3)

    return {
        "symbol": "N/A",
        "timeframe": "N/A",
        "initial_capital": initial_capital,
        "final_capital": round(final_capital, 2),
        "net_pnl": round(net_pnl, 2),
        "total_return_pct": round(total_return_pct, 2),
        "total_trades": len(completed_trades),
        "winning_trades": len(winning),
        "losing_trades": len(losing),
        "win_rate": round(win_rate, 1),
        "avg_win": round(sum(t["net_pnl"] for t in winning) / len(winning), 2) if winning else 0,
        "avg_loss": round(sum(t["net_pnl"] for t in losing) / len(losing), 2) if losing else 0,
        "largest_win": round(max((t["net_pnl"] for t in completed_trades), default=0), 2),
        "largest_loss": round(min((t["net_pnl"] for t in completed_trades), default=0), 2),
        "profit_factor": round(profit_factor, 2) if profit_factor < 999 else None,
        "max_drawdown_pct": round(max_dd, 2),
        "sharpe_ratio": sharpe,
        "trades": trades,
        "equity_curve": equity_curve[::max(1, len(equity_curve) // 200)],
        "error": None,
    }
