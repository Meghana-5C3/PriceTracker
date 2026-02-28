"""
Smart Price Prediction Engine (Phase 4).
Uses recent price history to predict whether a price is likely to drop soon.
Algorithm: Linear regression over last N price points.
"""
import logging
from datetime import datetime, timedelta
from app.models.models import PriceHistory

logger = logging.getLogger(__name__)


def predict_price_trend(product_id: int, days: int = 14) -> dict:
    """
    Given a product_id, analyse recent price history and return a simple
    buy/wait recommendation with reasoning.

    Returns a dict:
        {
          "recommendation": "buy" | "wait" | "neutral",
          "reason": str,
          "predicted_drop_pct": float | None,  # estimated drop if waiting
          "confidence": "high" | "medium" | "low"
        }
    """
    since = datetime.utcnow() - timedelta(days=days)
    history = (
        PriceHistory.query
        .filter(PriceHistory.product_id == product_id,
                PriceHistory.checked_at >= since)
        .order_by(PriceHistory.checked_at.asc())
        .all()
    )

    if len(history) < 3:
        return {
            "recommendation": "neutral",
            "reason": "Not enough price history yet — check back in a few days.",
            "predicted_drop_pct": None,
            "confidence": "low"
        }

    prices = [h.price for h in history]
    n = len(prices)

    # Simple linear regression slope
    x_mean = (n - 1) / 2
    y_mean = sum(prices) / n
    num = sum((i - x_mean) * (p - y_mean) for i, p in enumerate(prices))
    den = sum((i - x_mean) ** 2 for i in range(n))
    slope = num / den if den else 0

    last_price = prices[-1]
    lowest     = min(prices)
    highest    = max(prices)
    volatility = (highest - lowest) / highest * 100 if highest else 0

    # Simple heuristic rules
    if slope < -5:  # falling quickly
        predicted_drop = round(abs(slope) * 5, 1)  # ~5 more ticks
        return {
            "recommendation": "wait",
            "reason": f"Price is falling (trend: -{abs(round(slope, 1))}/check). Estimated drop of ~{predicted_drop:.1f}% in next 5 days.",
            "predicted_drop_pct": predicted_drop,
            "confidence": "high" if abs(slope) > 20 else "medium"
        }
    elif slope > 5 and volatility > 8:  # rising — buy now
        return {
            "recommendation": "buy",
            "reason": "Price is rising. Current price looks like a good entry point.",
            "predicted_drop_pct": None,
            "confidence": "medium"
        }
    elif last_price <= lowest * 1.03:  # within 3% of all-time low
        return {
            "recommendation": "buy",
            "reason": "At or near the lowest recorded price — great time to buy! 🎯",
            "predicted_drop_pct": None,
            "confidence": "high"
        }
    else:
        return {
            "recommendation": "neutral",
            "reason": "Price is stable. Set a target price alert and wait for a better deal.",
            "predicted_drop_pct": None,
            "confidence": "low"
        }
