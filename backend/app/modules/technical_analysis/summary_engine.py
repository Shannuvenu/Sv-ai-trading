"""
Technical summary rating engine.
Produces summary ratings from real indicator values.
"""
from typing import Optional


def compute_summary(indicators: dict) -> dict:
    """Compute oscillators and moving averages summary from indicator values."""
    close = indicators.get("latest_close", 0)
    rsi = indicators.get("rsi_14")
    stoch = indicators.get("stoch_k")
    cci = indicators.get("cci_20")
    adx = indicators.get("adx_14")

    # Oscillator ratings
    osc_buy, osc_sell, osc_neutral = 0, 0, 0

    if rsi is not None:
        if rsi < 30: osc_buy += 1
        elif rsi > 70: osc_sell += 1
        else: osc_neutral += 1

    if stoch is not None:
        if stoch < 20: osc_buy += 1
        elif stoch > 80: osc_sell += 1
        else: osc_neutral += 1

    if cci is not None:
        if cci < -100: osc_buy += 1
        elif cci > 100: osc_sell += 1
        else: osc_neutral += 1

    # Moving average ratings
    sma_list = [("sma_5", 5), ("sma_10", 10), ("sma_20", 20), ("sma_50", 50), ("sma_100", 100), ("sma_200", 200)]
    ma_buy, ma_sell, ma_neutral = 0, 0, 0

    for key, _ in sma_list:
        val = indicators.get(key)
        if val is not None and close > 0:
            if close > val: ma_buy += 1
            elif close < val: ma_sell += 1
            else: ma_neutral += 1

    ema_list = [("ema_10", 10), ("ema_20", 20), ("ema_50", 50)]
    for key, _ in ema_list:
        val = indicators.get(key)
        if val is not None and close > 0:
            if close > val: ma_buy += 1
            elif close < val: ma_sell += 1

    def _rating(buy, sell, neutral):
        total = buy + sell + neutral
        if total == 0: return "NEUTRAL"
        if buy > sell: return "BUY" if buy > (sell + neutral) else "NEUTRAL"
        if sell > buy: return "SELL" if sell > (buy + neutral) else "NEUTRAL"
        return "NEUTRAL"

    osc_rating = _rating(osc_buy, osc_sell, osc_neutral)
    ma_rating = _rating(ma_buy, ma_sell, ma_neutral)

    overall = "NEUTRAL"
    if osc_rating == "BUY" and ma_rating == "BUY": overall = "STRONG BUY"
    elif osc_rating == "BUY" or ma_rating == "BUY": overall = "BUY"
    elif osc_rating == "SELL" and ma_rating == "SELL": overall = "STRONG SELL"
    elif osc_rating == "SELL" or ma_rating == "SELL": overall = "SELL"

    return {
        "oscillators": {"buy": osc_buy, "sell": osc_sell, "neutral": osc_neutral, "rating": osc_rating},
        "moving_averages": {"buy": ma_buy, "sell": ma_sell, "neutral": ma_neutral, "rating": ma_rating},
        "overall": overall,
    }
