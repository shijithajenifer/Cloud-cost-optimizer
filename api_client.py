"""
External API Integration: exchangerate.host (completely free, no API key needed)
Used to convert cloud costs from USD to other currencies for multi-currency reporting.
"""

import requests
from config import EXCHANGE_API_URL, EXCHANGE_API_BASE


def fetch_exchange_rates(base: str = EXCHANGE_API_BASE) -> dict:
    """
    Fetch current currency exchange rates from exchangerate.host.
    Returns a dict like: {"USD": 1.0, "EUR": 0.93, "GBP": 0.79, "INR": 83.5, ...}
    Falls back to hardcoded approximate rates if API is unreachable.
    """
    fallback_rates = {
        "USD": 1.0,
        "EUR": 0.93,
        "GBP": 0.79,
        "INR": 83.5,
        "CAD": 1.36,
        "AUD": 1.53,
        "JPY": 157.0,
        "SGD": 1.35,
    }
    try:
        resp = requests.get(
            EXCHANGE_API_URL,
            params={"base": base, "symbols": "USD,EUR,GBP,INR,CAD,AUD,JPY,SGD"},
            timeout=5
        )
        if resp.status_code == 200:
            data = resp.json()
            rates = data.get("rates", {})
            if rates:
                return {"source": "live", "rates": rates}
        return {"source": "fallback", "rates": fallback_rates}
    except Exception:
        return {"source": "fallback", "rates": fallback_rates}


def convert_cost(amount_usd: float, target_currency: str, rates: dict) -> float:
    """Convert a USD amount to target currency using provided rates dict."""
    rate = rates.get(target_currency, 1.0)
    return round(amount_usd * rate, 2)


def get_currency_symbol(currency_code: str) -> str:
    symbols = {
        "USD": "$", "EUR": "€", "GBP": "£",
        "INR": "₹", "CAD": "CA$", "AUD": "A$",
        "JPY": "¥", "SGD": "S$"
    }
    return symbols.get(currency_code, currency_code + " ")
