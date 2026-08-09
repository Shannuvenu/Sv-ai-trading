"""Gemini AI market intelligence service — structured analysis with risk constraints."""
import json
import logging
import re
from typing import Optional
from decimal import Decimal

import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold

from app.core.config import get_settings

settings = get_settings()
logger = logging.getLogger("gemini_service")

SAFETY_SETTINGS = {
    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_ONLY_HIGH,
    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_ONLY_HIGH,
    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_ONLY_HIGH,
    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_ONLY_HIGH,
}

SYSTEM_PROMPT = """You are a professional financial market analyst for the Indian stock market (NSE/BSE).
You receive structured market data, technical indicators, news sentiment, and portfolio context.

Your job is to produce a JSON analysis with the exact schema below. Never include any text outside the JSON.

{
  "decision": "BUY" | "SELL" | "HOLD",
  "confidence": 0-100,
  "summary": "One-line summary of your analysis",
  "strategy": "Name of recommended strategy",
  "entry": recommended_entry_price_as_number,
  "stop_loss": recommended_stop_loss_as_number,
  "take_profit": recommended_take_profit_as_number,
  "position_size": recommended_quantity_as_integer,
  "risk_reward": risk_reward_ratio_as_number,
  "time_horizon": "INTRADAY" | "SWING" | "POSITIONAL",
  "reasoning": "Detailed reasoning",
  "technical_reasons": ["reason1", "reason2"],
  "fundamental_reasons": ["reason1 if available"],
  "news_reasons": ["reason1 if available"],
  "market_context": "Current market regime/sentiment analysis",
  "risks": ["risk1", "risk2"],
  "invalidating_conditions": ["condition1"],
  "supporting_evidence": ["evidence1"]
}

Rules:
- Never recommend a trade without sufficient data.
- If data is insufficient or market is closed, decision must be HOLD.
- Stop loss must be below entry for BUY, above entry for SELL.
- Position size must respect capital constraints.
- Always be conservative with Indian stocks.
- Disclose uncertainty when present.
- This is for educational/research purposes only — never present as financial advice.
"""


class GeminiService:
    def __init__(self):
        self._api_key = settings.GEMINI_API_KEY.strip()
        self._configured = bool(self._api_key)
        if not self._configured:
            logger.warning("GEMINI_API_KEY not set — AI intelligence will be unavailable.")
            self._model = None
        else:
            genai.configure(api_key=self._api_key)
            self._model = genai.GenerativeModel(
                model_name="gemini-2.0-flash",
                system_instruction=SYSTEM_PROMPT,
                safety_settings=SAFETY_SETTINGS,
            )

    @property
    def is_configured(self) -> bool:
        return self._configured

    def analyze(
        self,
        symbol: str,
        last_price: float,
        change_pct: float,
        indicators: dict,
        news_headlines: list[str],
        portfolio_context: Optional[dict] = None,
    ) -> dict:
        if not self._configured:
            return _fallback_analysis(symbol, indicators)

        market_snapshot = {
            "symbol": symbol,
            "last_price": last_price,
            "change_pct": round(change_pct, 2),
            "rsi_14": indicators.get("rsi_14"),
            "macd_line": indicators.get("macd_line"),
            "macd_signal": indicators.get("macd_signal"),
            "sma_20": indicators.get("sma_20"),
            "sma_50": indicators.get("sma_50"),
            "ema_20": indicators.get("ema_20"),
            "bb_upper": indicators.get("bb_upper"),
            "bb_middle": indicators.get("bb_middle"),
            "bb_lower": indicators.get("bb_lower"),
            "atr_14": indicators.get("atr_14"),
            "volume_sma_20": indicators.get("volume_sma_20"),
            "latest_volume": indicators.get("latest_volume"),
        }
        market_snapshot = {k: v for k, v in market_snapshot.items() if v is not None}

        news_text = "\n".join(f"- {h}" for h in news_headlines[:10]) if news_headlines else "No recent news available."

        prompt = f"""Analyze this Indian stock and provide your structured JSON analysis.

MARKET DATA:
{json.dumps(market_snapshot, indent=2)}

RECENT NEWS:
{news_text}

PORTFOLIO CONTEXT:
{json.dumps(portfolio_context or {}, indent=2)}

Provide ONLY the JSON response, no other text."""

        try:
            response = self._model.generate_content(prompt)
            raw = response.text.strip()
            # Strip markdown code fences if present
            raw = re.sub(r'^```(?:json)?\s*\n?', '', raw)
            raw = re.sub(r'\n?```\s*$', '', raw)
            result = json.loads(raw)
            return _validate_and_normalize(result, symbol, last_price)
        except Exception as e:
            logger.error(f"Gemini analysis failed for {symbol}: {e}")
            return _fallback_analysis(symbol, indicators)

    def analyze_strategy(
        self,
        symbol: str,
        last_price: float,
        indicators: dict,
        strategies: dict,
        news_headlines: list[str],
        market_regime: str = "NEUTRAL",
    ) -> dict:
        """Pick the best strategy for current market conditions."""
        if not self._configured:
            return {"recommended": "momentum", "confidence": 50, "reasoning": "Defaulting to momentum (Gemini unavailable)"}

        prompt = f"""Given current market conditions, select the best trading strategy.

STOCK: {symbol}
PRICE: ₹{last_price}
MARKET REGIME: {market_regime}

INDICATORS:
{json.dumps({k: v for k, v in indicators.items() if not k.startswith('_')}, indent=2)}

AVAILABLE STRATEGIES:
{json.dumps(strategies, indent=2)}

RECENT NEWS:
{chr(10).join(f'- {h}' for h in news_headlines[:5]) or 'No news'}

Return ONLY a JSON:
{{"recommended": "strategy_name", "confidence": 0-100, "reasoning": "why"}}"""

        try:
            response = self._model.generate_content(prompt)
            raw = response.text.strip()
            raw = re.sub(r'^```(?:json)?\s*\n?', '', raw)
            raw = re.sub(r'\n?```\s*$', '', raw)
            result = json.loads(raw)
            return result
        except Exception as e:
            logger.error(f"Gemini strategy analysis failed: {e}")
            return {"recommended": "momentum", "confidence": 50, "reasoning": "Default (analysis failed)"}

    def summarize_news(self, headlines: list[str]) -> dict:
        """Generate AI summary and sentiment from news headlines."""
        if not self._configured or not headlines:
            return {"sentiment": "NEUTRAL", "summary": "No AI summary available", "impact_score": 0}

        prompt = f"""Summarize these financial news headlines for Indian market context.

HEADLINES:
{chr(10).join(f'- {h}' for h in headlines[:15])}

Return ONLY JSON:
{{"sentiment": "BULLISH" | "BEARISH" | "NEUTRAL", "summary": "2-3 sentence summary", "impact_score": -10 to +10, "key_themes": ["theme1", "theme2"]}}"""

        try:
            response = self._model.generate_content(prompt)
            raw = response.text.strip()
            raw = re.sub(r'^```(?:json)?\s*\n?', '', raw)
            raw = re.sub(r'\n?```\s*$', '', raw)
            return json.loads(raw)
        except Exception as e:
            logger.error(f"Gemini news summary failed: {e}")
            return {"sentiment": "NEUTRAL", "summary": "Analysis unavailable", "impact_score": 0}


def _validate_and_normalize(result: dict, symbol: str, price: float) -> dict:
    """Ensure the Gemini response matches expected schema and is safe."""
    allowed_decisions = {"BUY", "SELL", "HOLD"}
    decision = result.get("decision", "HOLD").upper()
    if decision not in allowed_decisions:
        decision = "HOLD"

    confidence = min(max(int(result.get("confidence", 50)), 0), 100)
    if confidence < 30:
        decision = "HOLD"

    entry = result.get("entry", price)
    if not isinstance(entry, (int, float)) or entry <= 0:
        entry = price

    stop_loss = result.get("stop_loss", price * 0.97)
    if decision == "BUY" and stop_loss >= entry:
        stop_loss = entry * 0.97
    if decision == "SELL" and stop_loss <= entry:
        stop_loss = entry * 1.03

    take_profit = result.get("take_profit", price * 1.06)
    if decision == "BUY" and take_profit <= entry:
        take_profit = entry * 1.06
    if decision == "SELL" and take_profit >= entry:
        take_profit = entry * 0.94

    position_size = max(1, int(result.get("position_size", 1)))

    return {
        "symbol": symbol,
        "decision": decision,
        "confidence": confidence,
        "summary": result.get("summary", f"{decision} signal with {confidence}% confidence"),
        "strategy": result.get("strategy", "momentum"),
        "entry": round(float(entry), 2),
        "stop_loss": round(float(stop_loss), 2),
        "take_profit": round(float(take_profit), 2),
        "position_size": position_size,
        "risk_reward": round(float(result.get("risk_reward", 1.5)), 2),
        "time_horizon": result.get("time_horizon", "SWING"),
        "reasoning": result.get("reasoning", "Analysis generated by Gemini AI"),
        "technical_reasons": result.get("technical_reasons", []),
        "fundamental_reasons": result.get("fundamental_reasons", []),
        "news_reasons": result.get("news_reasons", []),
        "market_context": result.get("market_context", "Analysis unavailable"),
        "risks": result.get("risks", ["Market volatility", "News-driven movement"]),
        "invalidating_conditions": result.get("invalidating_conditions", []),
        "supporting_evidence": result.get("supporting_evidence", []),
        "is_fallback": False,
    }


def _fallback_analysis(symbol: str, indicators: dict) -> dict:
    """Deterministic fallback when Gemini is unavailable."""
    rsi = indicators.get("rsi_14")
    macd_l = indicators.get("macd_line")
    macd_s = indicators.get("macd_signal")
    sma_20 = indicators.get("sma_20")
    sma_50 = indicators.get("sma_50")
    latest_close = indicators.get("latest_close", 0)

    signals = []
    if rsi is not None:
        if rsi < 35: signals.append(("BUY", f"RSI oversold at {rsi:.1f}"))
        elif rsi > 65: signals.append(("SELL", f"RSI overbought at {rsi:.1f}"))
    if macd_l is not None and macd_s is not None:
        if macd_l > macd_s: signals.append(("BUY", "MACD above signal line"))
        else: signals.append(("SELL", "MACD below signal line"))
    if sma_20 is not None and sma_50 is not None and latest_close:
        if sma_20 > sma_50 and latest_close > sma_20: signals.append(("BUY", "Price above SMA20 and SMA50"))
        elif sma_20 < sma_50: signals.append(("SELL", "SMA20 below SMA50"))

    buy_count = sum(1 for d, _ in signals if d == "BUY")
    sell_count = sum(1 for d, _ in signals if d == "SELL")

    if buy_count > sell_count:
        decision, confidence = "BUY", min(40 + buy_count * 15, 75)
    elif sell_count > buy_count:
        decision, confidence = "SELL", min(40 + sell_count * 15, 75)
    else:
        decision, confidence = "HOLD", 50

    return {
        "symbol": symbol,
        "decision": decision,
        "confidence": confidence,
        "summary": f"Rule-based {decision} signal from technical indicators",
        "strategy": "momentum",
        "entry": round(float(latest_close), 2) if latest_close else 0,
        "stop_loss": round(float(latest_close) * 0.97, 2) if latest_close else 0,
        "take_profit": round(float(latest_close) * 1.06, 2) if latest_close else 0,
        "position_size": 1,
        "risk_reward": 1.5,
        "time_horizon": "SWING",
        "reasoning": "Deterministic analysis based on technical indicators (Gemini unavailable)",
        "technical_reasons": [r for d, r in signals if d == decision],
        "fundamental_reasons": [],
        "news_reasons": [],
        "market_context": "Technical indicators suggest " + ("uptrend" if decision == "BUY" else "downtrend" if decision == "SELL" else "neutral"),
        "risks": ["Market volatility", "Rule-based signal limitations"],
        "invalidating_conditions": [],
        "supporting_evidence": [],
        "is_fallback": True,
    }


_service: Optional[GeminiService] = None


def get_gemini_service() -> GeminiService:
    global _service
    if _service is None:
        _service = GeminiService()
    return _service
