from dataclasses import dataclass
from decimal import Decimal
from typing import Optional
import numpy as np


@dataclass
class IndicatorResult:
    name: str
    values: list[Optional[float]]
    description: str


def _decimal_to_float_list(values: list[Decimal]) -> list[float]:
    return [float(v) for v in values]


def sma(values: list[float], period: int) -> list[Optional[float]]:
    result: list[Optional[float]] = []
    for i in range(len(values)):
        if i < period - 1:
            result.append(None)
        else:
            result.append(sum(values[i - period + 1:i + 1]) / period)
    return result


def ema(values: list[float], period: int) -> list[Optional[float]]:
    result: list[Optional[float]] = []
    multiplier = 2.0 / (period + 1)
    for i in range(len(values)):
        if i == 0:
            result.append(values[0])
        elif i < period:
            result.append(values[i])
        else:
            ema_val = (values[i] - (result[-1] or values[i])) * multiplier + (result[-1] or values[i])
            result.append(ema_val)
    return result


def rsi(values: list[float], period: int = 14) -> list[Optional[float]]:
    result: list[Optional[float]] = []
    gains: list[float] = []
    losses: list[float] = []

    for i in range(1, len(values)):
        delta = values[i] - values[i - 1]
        gains.append(max(delta, 0))
        losses.append(max(-delta, 0))

    for i in range(len(values)):
        if i < period:
            result.append(None)
        else:
            idx = i - 1
            avg_gain = sum(gains[idx - period + 1:idx + 1]) / period
            avg_loss = sum(losses[idx - period + 1:idx + 1]) / period
            if avg_loss == 0:
                result.append(100.0)
            else:
                rs = avg_gain / avg_loss
                result.append(100.0 - (100.0 / (1.0 + rs)))
    return result


def macd(
    values: list[float], fast: int = 12, slow: int = 26, signal: int = 9
) -> tuple[list[Optional[float]], list[Optional[float]], list[Optional[float]]]:
    ema_fast = ema(values, fast)
    ema_slow = ema(values, slow)

    macd_line: list[Optional[float]] = []
    for i in range(len(values)):
        if ema_fast[i] is None or ema_slow[i] is None:
            macd_line.append(None)
        else:
            macd_line.append(ema_fast[i] - ema_slow[i])

    valid_macd = [(v if v is not None else 0.0) for v in macd_line]
    signal_line = ema(valid_macd, signal)

    histogram: list[Optional[float]] = []
    for i in range(len(values)):
        if macd_line[i] is None or signal_line[i] is None:
            histogram.append(None)
        else:
            histogram.append(macd_line[i] - signal_line[i])

    return macd_line, signal_line, histogram


def bollinger_bands(
    values: list[float], period: int = 20, std_dev: float = 2.0
) -> tuple[list[Optional[float]], list[Optional[float]], list[Optional[float]]]:
    middle = sma(values, period)
    upper: list[Optional[float]] = []
    lower: list[Optional[float]] = []

    for i in range(len(values)):
        if middle[i] is None:
            upper.append(None)
            lower.append(None)
        else:
            window = values[i - period + 1:i + 1]
            std = float(np.std(window, ddof=0))
            upper.append(middle[i] + std_dev * std)
            lower.append(middle[i] - std_dev * std)

    return upper, middle, lower


def atr(highs: list[float], lows: list[float], closes: list[float], period: int = 14) -> list[Optional[float]]:
    trs: list[float] = [highs[0] - lows[0]]
    for i in range(1, len(closes)):
        tr = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i - 1]),
            abs(lows[i] - closes[i - 1]),
        )
        trs.append(tr)

    return sma(trs, period)


def volume_sma(volumes: list[float], period: int = 20) -> list[Optional[float]]:
    return sma(volumes, period)


def compute_indicators(
    closes: list[Decimal],
    highs: list[Decimal],
    lows: list[Decimal],
    volumes: list[int],
) -> dict:
    c = _decimal_to_float_list(closes)
    h = _decimal_to_float_list(highs)
    l = _decimal_to_float_list(lows)
    v = [float(vol) for vol in volumes]
    n = len(c)

    last = lambda arr: arr[-1] if arr and arr[-1] is not None else None

    sma_20 = sma(c, 20)
    sma_50 = sma(c, 50)
    ema_20 = ema(c, 20)
    rsi_vals = rsi(c, 14)
    macd_line, signal_line, hist = macd(c)
    bb_upper, bb_middle, bb_lower = bollinger_bands(c, 20)
    atr_vals = atr(h, l, c, 14)
    vol_sma_vals = volume_sma(v, 20)

    return {
        "n": n,
        "sma_20": last(sma_20),
        "sma_50": last(sma_50),
        "ema_20": last(ema_20),
        "rsi_14": last(rsi_vals),
        "macd_line": last(macd_line),
        "macd_signal": last(signal_line),
        "macd_histogram": last(hist),
        "bb_upper": last(bb_upper),
        "bb_middle": last(bb_middle),
        "bb_lower": last(bb_lower),
        "atr_14": last(atr_vals),
        "volume_sma_20": last(vol_sma_vals),
        "latest_close": c[-1] if c else None,
        "latest_volume": v[-1] if v else None,
        "_sma_20": sma_20,
        "_sma_50": sma_50,
        "_ema_20": ema_20,
        "_rsi_vals": rsi_vals,
        "_macd_line": macd_line,
        "_macd_signal": signal_line,
        "_hist": hist,
        "_bb_upper": bb_upper,
        "_bb_middle": bb_middle,
        "_bb_lower": bb_lower,
        "_atr_vals": atr_vals,
        "_vol_sma": vol_sma_vals,
    }
