def explain_signal(signal_dict: dict) -> dict:
    return {
        "symbol": signal_dict["symbol"],
        "timestamp": signal_dict["timestamp"],
        "direction": signal_dict["direction"],
        "confidence": signal_dict["confidence"],
        "summary": f"{signal_dict['direction']} signal with {signal_dict['confidence']:.0%} confidence",
        "reasoning": signal_dict.get("reasoning", []),
        "features_used": signal_dict.get("features_used", []),
        "disclaimer": "This is an analytical output from a rule-based signal engine. It is not financial advice and does not guarantee any outcome.",
    }
