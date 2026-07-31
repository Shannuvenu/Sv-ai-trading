"""AI Trader — deterministic strategy library using existing indicators."""
from decimal import Decimal
from typing import Optional

STRATEGIES = {
    "momentum": {
        "name": "Momentum Breakout",
        "description": "Enter when MACD is positive, RSI between 45-70, and price above SMA20",
        "timeframe": "1D",
        "min_candles": 50,
    },
    "breakout": {
        "name": "Bollinger Band Breakout",
        "description": "Enter when price breaks above upper BB with volume confirmation",
        "timeframe": "1D",
        "min_candles": 50,
    },
    "trend_follow": {
        "name": "Trend Following",
        "description": "Enter when SMA20 > SMA50 and price > SMA20, exit when SMA20 < SMA50",
        "timeframe": "1D",
        "min_candles": 50,
    },
    "mean_reversion": {
        "name": "RSI Mean Reversion",
        "description": "BUY when RSI < 35 (oversold), SELL when RSI > 65 (overbought)",
        "timeframe": "1D",
        "min_candles": 50,
    },
    "ma_crossover": {
        "name": "EMA Crossover",
        "description": "BUY when EMA20 crosses above EMA50, SELL when EMA20 crosses below EMA50",
        "timeframe": "1D",
        "min_candles": 50,
    },
    "volume_surge": {
        "name": "Volume Surge",
        "description": "Enter when volume > 1.5x SMA20 volume AND price > SMA20",
        "timeframe": "1D",
        "min_candles": 50,
    },
}


def evaluate_strategy(strategy_name: str, indicators: dict, latest_close: float) -> dict:
    """Evaluate a strategy on the given indicators. Returns BUY/SELL/HOLD with reasoning."""
    rsi = indicators.get("rsi_14")
    macd_line = indicators.get("macd_line")
    macd_signal = indicators.get("macd_signal")
    sma_20 = indicators.get("sma_20")
    sma_50 = indicators.get("sma_50")
    bb_upper = indicators.get("bb_upper")
    bb_middle = indicators.get("bb_middle")
    bb_lower = indicators.get("bb_lower")
    latest_vol = indicators.get("latest_volume") or 0
    vol_sma = indicators.get("volume_sma_20") or 1
    n = indicators.get("n", 0)

    if n < 50:
        return {"direction": "HOLD", "score": 0.0, "reason": "Insufficient data"}

    direction = "HOLD"
    score = 0.5
    reasons = []

    if strategy_name == "momentum":
        if macd_line is not None and macd_signal is not None and sma_20 is not None and rsi is not None:
            if macd_line > macd_signal and latest_close > sma_20 and 45 <= rsi <= 70:
                direction = "BUY"; score = 0.75
                reasons.append("MACD positive slope, price above SMA20, RSI healthy")
            elif macd_line < macd_signal and latest_close < sma_20:
                direction = "SELL"; score = 0.65
                reasons.append("MACD negative slope, price below SMA20")

    elif strategy_name == "breakout":
        if bb_upper is not None and latest_close is not None and vol_sma > 0:
            vol_ratio = latest_vol / vol_sma
            if latest_close > bb_upper and vol_ratio > 1.3:
                direction = "BUY"; score = 0.80
                reasons.append(f"Price above BB upper ({bb_upper:.1f}) with {vol_ratio:.1f}x volume")
            elif latest_close < bb_lower:
                direction = "SELL"; score = 0.60
                reasons.append("Price below BB lower band")

    elif strategy_name == "trend_follow":
        if sma_20 is not None and sma_50 is not None:
            if sma_20 > sma_50 and latest_close > sma_20:
                direction = "BUY"; score = 0.70
                reasons.append("SMA20 > SMA50, uptrend confirmed")
            elif sma_20 < sma_50 and latest_close < sma_20:
                direction = "SELL"; score = 0.65
                reasons.append("SMA20 < SMA50, downtrend")

    elif strategy_name == "mean_reversion":
        if rsi is not None:
            if rsi < 35:
                direction = "BUY"; score = 0.65
                reasons.append(f"RSI oversold at {rsi:.1f}")
            elif rsi > 65:
                direction = "SELL"; score = 0.65
                reasons.append(f"RSI overbought at {rsi:.1f}")

    elif strategy_name == "ma_crossover":
        if macd_line is not None and macd_signal is not None and rsi is not None:
            if macd_line > macd_signal:
                direction = "BUY"; score = 0.65
                reasons.append("MACD crossed above signal")
            else:
                direction = "SELL"; score = 0.55
                reasons.append("MACD below signal")

    elif strategy_name == "volume_surge":
        if vol_sma > 0 and sma_20 is not None:
            vol_ratio = latest_vol / vol_sma
            if vol_ratio > 1.5 and latest_close > sma_20:
                direction = "BUY"; score = 0.70
                reasons.append(f"Volume {vol_ratio:.1f}x average, price above SMA20")
            elif vol_ratio > 1.5 and latest_close < sma_20:
                direction = "SELL"; score = 0.55
                reasons.append(f"Volume {vol_ratio:.1f}x average, price below SMA20")

    return {"direction": direction, "score": round(score, 2), "reason": "; ".join(reasons) if reasons else "No clear signal"}
