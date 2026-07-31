"""
Enhanced technical analysis engine with comprehensive indicators and ratings.
All calculations from real OHLCV data — never simulated.
"""
from decimal import Decimal
from typing import Optional
import math


def _decimal_list(values: list[Decimal]) -> list[float]:
    return [float(v) for v in values]


def sma(values: list[float], period: int) -> list[Optional[float]]:
    result: list[Optional[float]] = []
    for i in range(len(values)):
        if i < period - 1:
            result.append(None)
        else:
            result.append(sum(values[i-period+1:i+1]) / period)
    return result


def ema(values: list[float], period: int) -> list[Optional[float]]:
    result: list[Optional[float]] = []
    multiplier = 2.0 / (period + 1)
    for i in range(len(values)):
        if i == 0:
            result.append(values[0])
        elif i < period - 1:
            result.append(None)
        else:
            prev = result[-1] if result[-1] is not None else values[i]
            result.append((values[i] - prev) * multiplier + prev)
    return result


def rsi(values: list[float], period: int = 14) -> list[Optional[float]]:
    if len(values) < period + 1:
        return [None] * len(values)
    result: list[Optional[float]] = [None] * period
    gains, losses = 0.0, 0.0
    for i in range(1, period + 1):
        d = values[i] - values[i-1]
        if d > 0: gains += d
        else: losses += abs(d)
    avg_gain = gains / period
    avg_loss = losses / period
    rs = avg_gain / avg_loss if avg_loss > 0 else float('inf')
    result.append(100.0 - (100.0 / (1.0 + rs)) if rs != float('inf') else 100.0)

    for i in range(period + 1, len(values)):
        d = values[i] - values[i-1]
        gain = d if d > 0 else 0.0
        loss = abs(d) if d < 0 else 0.0
        avg_gain = (avg_gain * (period - 1) + gain) / period
        avg_loss = (avg_loss * (period - 1) + loss) / period
        rs = avg_gain / avg_loss if avg_loss > 0 else float('inf')
        result.append(100.0 - (100.0 / (1.0 + rs)) if rs != float('inf') else 100.0)
    return result


def adx(highs: list[float], lows: list[float], closes: list[float], period: int = 14) -> list[Optional[float]]:
    n = len(closes)
    if n < period + 1:
        return [None] * n
    tr: list[float] = []
    plus_dm: list[float] = []
    minus_dm: list[float] = []
    for i in range(1, n):
        h, l, pc = highs[i], lows[i], closes[i-1]
        tr.append(max(h-l, abs(h-pc), abs(l-pc)))
        up = h - highs[i-1]
        down = lows[i-1] - l
        plus_dm.append(up if up > down and up > 0 else 0.0)
        minus_dm.append(down if down > up and down > 0 else 0.0)
    result: list[Optional[float]] = [None] * (period)
    atr_val = sum(tr[:period]) / period
    plus_dm_s = sum(plus_dm[:period]) / period
    minus_dm_s = sum(minus_dm[:period]) / period
    for i in range(period, n - 1):
        atr_val = (atr_val * (period - 1) + tr[i]) / period
        plus_dm_s = (plus_dm_s * (period - 1) + plus_dm[i]) / period
        minus_dm_s = (minus_dm_s * (period - 1) + minus_dm[i]) / period
        pdi = (plus_dm_s / atr_val * 100) if atr_val > 0 else 0.0
        mdi = (minus_dm_s / atr_val * 100) if atr_val > 0 else 0.0
        dx = abs(pdi - mdi) / (pdi + mdi) * 100 if (pdi + mdi) > 0 else 0.0
        result.append(dx)
    result.extend([None] * (n - len(result)))
    return result


def stochastic(highs: list[float], lows: list[float], closes: list[float], k_period: int = 14, d_period: int = 3) -> list[Optional[float]]:
    n = len(closes)
    result: list[Optional[float]] = [None] * (k_period - 1)
    k_vals: list[float] = []
    for i in range(k_period - 1, n):
        h = max(highs[i-k_period+1:i+1])
        l = min(lows[i-k_period+1:i+1])
        k_val = ((closes[i] - l) / (h - l) * 100) if h != l else 50.0
        k_vals.append(k_val)
    d_vals = sma(k_vals, d_period)
    return [None] * (k_period - 1) + d_vals + [None] * (n - k_period - len(d_vals) + 1)


def vwap(highs: list[float], lows: list[float], closes: list[float], volumes: list[int]) -> list[float]:
    cum_pv, cum_v = 0.0, 0
    result = []
    for i in range(len(closes)):
        typical = (highs[i] + lows[i] + closes[i]) / 3
        cum_pv += typical * volumes[i]
        cum_v += volumes[i]
        result.append(cum_pv / cum_v if cum_v > 0 else closes[i])
    return result


def cci(highs: list[float], lows: list[float], closes: list[float], period: int = 20) -> list[Optional[float]]:
    n = len(closes)
    tp = [(highs[i] + lows[i] + closes[i]) / 3 for i in range(n)]
    result: list[Optional[float]] = [None] * (period - 1)
    for i in range(period - 1, n):
        sma_val = sum(tp[i-period+1:i+1]) / period
        md = sum(abs(tp[j] - sma_val) for j in range(i-period+1, i+1)) / period
        result.append((tp[i] - sma_val) / (0.015 * md) if md > 0 else 0.0)
    return result


def compute_enhanced_indicators(
    closes: list[Decimal], highs: list[Decimal], lows: list[Decimal], volumes: list[int],
) -> dict:
    c = _decimal_list(closes)
    h = _decimal_list(highs)
    l = _decimal_list(lows)
    v = [float(vol) for vol in volumes]

    def last(arr, default=None):
        for v in reversed(arr):
            if v is not None:
                return v
        return default

    rsi_vals = rsi(c, 14)
    adx_vals = adx(h, l, c, 14)
    stoch_vals = stochastic(h, l, c, 14, 3)
    vwap_vals = vwap(h, l, c, v)
    cci_vals = cci(h, l, c, 20)

    sma_5 = sma(c, 5)
    sma_10 = sma(c, 10)
    sma_20 = sma(c, 20)
    sma_50 = sma(c, 50)
    sma_100 = sma(c, 100)
    sma_200 = sma(c, 200)

    ema_10 = ema(c, 10)
    ema_20 = ema(c, 20)
    ema_50 = ema(c, 50)

    return {
        "latest_close": c[-1] if c else 0.0,
        "latest_volume": v[-1] if v else 0,
        "rsi_14": last(rsi_vals),
        "adx_14": last(adx_vals),
        "stoch_k": last(stoch_vals),
        "vwap": last(vwap_vals),
        "cci_20": last(cci_vals),
        "sma_5": last(sma_5),
        "sma_10": last(sma_10),
        "sma_20": last(sma_20),
        "sma_50": last(sma_50),
        "sma_100": last(sma_100),
        "sma_200": last(sma_200),
        "ema_10": last(ema_10),
        "ema_20": last(ema_20),
        "ema_50": last(ema_50),
    }
