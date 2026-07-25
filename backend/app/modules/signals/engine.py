from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from app.modules.signals.enums import SignalDirection


@dataclass
class Signal:
    symbol: str
    timestamp: datetime
    direction: SignalDirection
    confidence: float
    features_used: list[str] = field(default_factory=list)
    reasoning: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "timestamp": self.timestamp.isoformat(),
            "direction": self.direction.value,
            "confidence": round(self.confidence, 2),
            "features_used": self.features_used,
            "reasoning": self.reasoning,
        }


def generate_signal(
    symbol: str,
    indicators: dict,
) -> Signal:
    now = datetime.now(timezone.utc)
    reasons: list[str] = []
    signals_list: list[tuple[str, float]] = []
    features: list[str] = []

    rsi_val = indicators.get("rsi_14")
    if rsi_val is not None:
        features.append("RSI")
        if rsi_val < 30:
            signals_list.append(("BUY", 0.7))
            reasons.append(f"RSI is {rsi_val:.1f}, indicating an oversold condition.")
        elif rsi_val > 70:
            signals_list.append(("SELL", 0.7))
            reasons.append(f"RSI is {rsi_val:.1f}, indicating an overbought condition.")

    macd_l = indicators.get("macd_line")
    macd_s = indicators.get("macd_signal")
    if macd_l is not None and macd_s is not None:
        features.append("MACD")
        if macd_l > macd_s:
            signals_list.append(("BUY", 0.65))
            if macd_l > 0:
                reasons.append("MACD is above its signal line and positive.")
            else:
                reasons.append("MACD crossed above its signal line.")
        elif macd_l < macd_s:
            signals_list.append(("SELL", 0.65))
            reasons.append("MACD is below its signal line.")

    sma_20 = indicators.get("sma_20")
    sma_50 = indicators.get("sma_50")
    latest_close = indicators.get("latest_close")
    if sma_20 is not None and sma_50 is not None and latest_close is not None:
        features.append("Moving Average")
        if sma_20 > sma_50 and latest_close > sma_20:
            signals_list.append(("BUY", 0.6))
            reasons.append("Price is above SMA 20 and SMA 50, confirming uptrend.")
        elif sma_20 < sma_50 and latest_close < sma_20:
            signals_list.append(("SELL", 0.6))
            reasons.append("Price is below SMA 20 and SMA 50, confirming downtrend.")

    bb_upper = indicators.get("bb_upper")
    bb_lower = indicators.get("bb_lower")
    bb_middle = indicators.get("bb_middle")
    if bb_upper is not None and bb_lower is not None and latest_close is not None:
        features.append("Bollinger Bands")
        if latest_close < bb_lower:
            signals_list.append(("BUY", 0.55))
            reasons.append("Price is below the lower Bollinger Band, indicating potential reversal.")
        elif latest_close > bb_upper:
            signals_list.append(("SELL", 0.55))
            reasons.append("Price is above the upper Bollinger Band, indicating potential reversal.")

    latest_volume = indicators.get("latest_volume")
    vol_sma = indicators.get("volume_sma_20")
    if latest_volume is not None and vol_sma is not None and vol_sma > 0:
        features.append("Volume")
        ratio = latest_volume / vol_sma
        if ratio > 1.5:
            reasons.append(f"Volume is {ratio:.1f}x its 20-day average, confirming strength.")

    if not signals_list:
        return Signal(
            symbol=symbol,
            timestamp=now,
            direction=SignalDirection.HOLD,
            confidence=0.5,
            features_used=features,
            reasoning=["No clear signal detected. RSI, MACD, and price trends are neutral."],
        )

    buy_score = sum(c for d, c in signals_list if d == "BUY")
    sell_score = sum(c for d, c in signals_list if d == "SELL")

    if buy_score > sell_score:
        direction = SignalDirection.BUY
        confidence = min(buy_score / (buy_score + sell_score + 0.01), 0.95)
    elif sell_score > buy_score:
        direction = SignalDirection.SELL
        confidence = min(sell_score / (buy_score + sell_score + 0.01), 0.95)
    else:
        direction = SignalDirection.HOLD
        confidence = 0.5

    return Signal(
        symbol=symbol,
        timestamp=now,
        direction=direction,
        confidence=confidence,
        features_used=features,
        reasoning=reasons,
    )
