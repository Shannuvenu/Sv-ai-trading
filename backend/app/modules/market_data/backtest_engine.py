"""
Backtest engine — runs Pine strategies against historical OHLCV.
No future-data look-ahead. Uses existing Pine interpreter.
Produces reproducible trade metrics.

CORRECTNESS RULES:
- Entry: BUY signal on candle[i] → execute on same candle's close
- Exit: SELL signal on candle[i] → execute on same candle's close
- Stop Loss: checked EVERY candle against candle.low. If low <= SL, exit at SL price.
- Take Profit: checked EVERY candle against candle.high. If high >= TP, exit at TP price.
- Same-candle SL+TP: stop-loss wins (conservative — assume worst case first)
- Commission: charged on both entry (cost * rate) and exit (proceeds * rate)
- Position sizing: max_trade_value = capital * position_size_pct / 100, qty = floor(max_trade_value / price)
"""
import logging
import math
import statistics
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

    interpreter = PineInterpreter(ohlc)
    result = interpreter.execute(script)
    if result.errors:
        return {"error": result.errors[0], "trades": [], "metrics": {}}

    shapes = result.shapes
    if not shapes:
        return {"error": "No plotshape() signals found in script", "trades": [], "metrics": {}}

    times = ohlc["time"]
    closes = ohlc["close"]
    highs = ohlc["high"]
    lows = ohlc["low"]

    # Extract buy/sell signal indices from Pine output
    buy_indices = set()
    sell_indices = set()
    for shape in shapes:
        title = (shape.get("title") or "").lower()
        for i, pt in enumerate(shape.get("data", [])):
            if pt.get("value"):
                if "buy" in title or "long" in title or "entry" in title:
                    buy_indices.add(i)
                elif "sell" in title or "short" in title or "exit" in title:
                    sell_indices.add(i)
                else:
                    buy_indices.add(i)  # default first shape = buy

    if not buy_indices and not sell_indices:
        return {"error": "No buy/sell signals generated", "trades": [], "metrics": {}}

    # Run chronological simulation
    capital = initial_capital
    position = 0
    entry_price = 0
    entry_fees = 0
    sl_price = 0
    tp_price = 0
    trades = []
    equity_curve = []

    for i in range(n):
        curr_close = closes[i]
        curr_high = highs[i]
        curr_low = lows[i]

        # Track equity
        pos_value = position * curr_close if position > 0 else 0
        equity_curve.append({"time": times[i], "equity": capital + pos_value})

        # Check stop-loss and take-profit on EVERY candle while holding
        if position > 0:
            sl_hit = sl_price > 0 and curr_low <= sl_price
            tp_hit = tp_price > 0 and curr_high >= tp_price

            if sl_hit and tp_hit:
                # Conservative rule: stop-loss wins in same-candle scenario
                exit_price = sl_price
                exit_reason = "STOP_LOSS"
            elif sl_hit:
                exit_price = sl_price
                exit_reason = "STOP_LOSS"
            elif tp_hit:
                exit_price = tp_price
                exit_reason = "TAKE_PROFIT"
            else:
                exit_price = None
                exit_reason = None

            if exit_price is not None:
                proceeds = position * exit_price
                exit_comm = proceeds * (commission_pct / 100)
                capital += (proceeds - exit_comm)
                gross_pnl = (exit_price - entry_price) * position
                net_pnl = gross_pnl - entry_fees - exit_comm
                trades[-1].update({
                    "exit_time": times[i],
                    "exit_price": round(exit_price, 2),
                    "exit_fees": round(exit_comm, 2),
                    "total_fees": round(entry_fees + exit_comm, 2),
                    "gross_pnl": round(gross_pnl, 2),
                    "net_pnl": round(net_pnl, 2),
                    "return_pct": round((exit_price - entry_price) / entry_price * 100, 2) if entry_price > 0 else 0,
                    "exit_reason": exit_reason,
                })
                position = 0
                entry_price = 0
                entry_fees = 0
                sl_price = 0
                tp_price = 0

        # Check Pine signals (only if flat or opposite direction)
        if i in buy_indices and position == 0:
            price = curr_close
            max_trade = capital * (position_size_pct / 100)
            qty = int(max_trade / price)
            if qty <= 0:
                continue
            cost = qty * price
            comm = cost * (commission_pct / 100)
            capital -= (cost + comm)
            position = qty
            entry_price = price
            entry_fees = comm
            sl_price = price * (1 - stop_loss_pct / 100)
            tp_price = price * (1 + take_profit_pct / 100)
            trades.append({
                "id": len(trades) + 1,
                "side": "BUY",
                "entry_time": times[i],
                "entry_price": round(price, 2),
                "quantity": qty,
                "stop_loss": round(sl_price, 2),
                "take_profit": round(tp_price, 2),
                "entry_fees": round(comm, 2),
            })

        elif i in sell_indices and position > 0:
            price = curr_close
            proceeds = position * price
            exit_comm = proceeds * (commission_pct / 100)
            capital += (proceeds - exit_comm)
            gross_pnl = (price - entry_price) * position
            net_pnl = gross_pnl - entry_fees - exit_comm
            trades[-1].update({
                "exit_time": times[i],
                "exit_price": round(price, 2),
                "exit_fees": round(exit_comm, 2),
                "total_fees": round(entry_fees + exit_comm, 2),
                "gross_pnl": round(gross_pnl, 2),
                "net_pnl": round(net_pnl, 2),
                "return_pct": round((price - entry_price) / entry_price * 100, 2) if entry_price > 0 else 0,
                "exit_reason": "SIGNAL",
            })
            position = 0
            entry_price = 0
            entry_fees = 0
            sl_price = 0
            tp_price = 0

    # Close remaining position at last candle close
    if position > 0:
        last_price = closes[-1]
        proceeds = position * last_price
        exit_comm = proceeds * (commission_pct / 100)
        capital += (proceeds - exit_comm)
        gross_pnl = (last_price - entry_price) * position
        net_pnl = gross_pnl - entry_fees - exit_comm
        trades[-1].update({
            "exit_time": times[-1],
            "exit_price": round(last_price, 2),
            "exit_fees": round(exit_comm, 2),
            "total_fees": round(entry_fees + exit_comm, 2),
            "gross_pnl": round(gross_pnl, 2),
            "net_pnl": round(net_pnl, 2),
            "return_pct": round((last_price - entry_price) / entry_price * 100, 2) if entry_price > 0 else 0,
            "exit_reason": "END_OF_DATA",
        })

    # Metrics
    completed_trades = [t for t in trades if "exit_price" in t]
    winning = [t for t in completed_trades if t["net_pnl"] > 0]
    losing = [t for t in completed_trades if t["net_pnl"] <= 0]
    total_trades = len(completed_trades) or 1

    gross_profit = sum(t["net_pnl"] for t in winning) if winning else 0
    gross_loss = abs(sum(t["net_pnl"] for t in losing)) if losing else 0
    profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else (None if gross_profit == 0 else None)

    peak = initial_capital
    max_dd = 0.0
    for eq in equity_curve:
        if eq["equity"] > peak:
            peak = eq["equity"]
        dd = (peak - eq["equity"]) / peak * 100 if peak > 0 else 0
        if dd > max_dd:
            max_dd = dd

    returns = []
    for j in range(1, len(equity_curve)):
        prev = equity_curve[j - 1]["equity"]
        curr = equity_curve[j]["equity"]
        if prev > 0:
            returns.append((curr - prev) / prev)
    sharpe = None
    if len(returns) > 10:
        avg = statistics.mean(returns)
        std = statistics.stdev(returns)
        if std > 0:
            sharpe = round((avg * math.sqrt(252)) / std, 3)

    return {
        "symbol": "N/A",
        "timeframe": "N/A",
        "initial_capital": round(initial_capital, 2),
        "final_capital": round(capital, 2),
        "net_pnl": round(capital - initial_capital, 2),
        "total_return_pct": round((capital - initial_capital) / initial_capital * 100, 2) if initial_capital > 0 else 0,
        "total_trades": len(completed_trades),
        "winning_trades": len(winning),
        "losing_trades": len(losing),
        "win_rate": round(len(winning) / total_trades * 100, 1) if total_trades > 0 else 0,
        "avg_win": round(sum(t["net_pnl"] for t in winning) / len(winning), 2) if winning else 0,
        "avg_loss": round(sum(t["net_pnl"] for t in losing) / len(losing), 2) if losing else 0,
        "largest_win": round(max((t["net_pnl"] for t in completed_trades), default=0), 2),
        "largest_loss": round(min((t["net_pnl"] for t in completed_trades), default=0), 2),
        "profit_factor": round(profit_factor, 2) if profit_factor is not None else None,
        "max_drawdown_pct": round(max_dd, 2),
        "sharpe_ratio": sharpe,
        "trades": trades,
        "equity_curve": equity_curve[::max(1, len(equity_curve) // 200)],
        "error": None,
    }
