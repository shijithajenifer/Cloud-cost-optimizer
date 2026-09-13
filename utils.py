import pandas as pd


REQUIRED_COLUMNS = [
    "resource_id", "resource_type", "region",
    "monthly_cost_usd", "cpu_utilization_pct", "storage_utilization_pct"
]


def validate_csv(df: pd.DataFrame) -> tuple[bool, str]:
    """
    Validate that the uploaded CSV has required columns.
    Returns (is_valid: bool, message: str)
    """
    missing = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing:
        return False, f"Missing required columns: {', '.join(missing)}"
    if df.empty:
        return False, "CSV file is empty."
    return True, "OK"


def format_currency(value: float, symbol: str = "$") -> str:
    return f"{symbol}{value:,.2f}"


def priority_color(priority: str) -> str:
    mapping = {"High": "#ff4b4b", "Medium": "#ffa500", "Low": "#00c853"}
    return mapping.get(priority, "#888888")


def priority_sort_key(priority: str) -> int:
    mapping = {"High": 0, "Medium": 1, "Low": 2}
    return mapping.get(priority, 3)
