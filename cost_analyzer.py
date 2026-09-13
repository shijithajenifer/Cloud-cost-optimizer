import pandas as pd
from config import (
    IDLE_CPU_THRESHOLD,
    OVERSIZED_CPU_THRESHOLD,
    STORAGE_WASTE_THRESHOLD,
    HIGH_COST_PERCENTILE,
)


def load_and_clean(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize column types and fill missing values."""
    df = df.copy()
    df["monthly_cost_usd"] = pd.to_numeric(df["monthly_cost_usd"], errors="coerce").fillna(0.0)
    df["cpu_utilization_pct"] = pd.to_numeric(df["cpu_utilization_pct"], errors="coerce").fillna(0.0)
    df["storage_utilization_pct"] = pd.to_numeric(df["storage_utilization_pct"], errors="coerce").fillna(0.0)
    df["resource_id"] = df["resource_id"].astype(str).str.strip()
    df["resource_type"] = df["resource_type"].astype(str).str.strip()
    df["region"] = df["region"].astype(str).str.strip()
    return df


def detect_idle_resources(df: pd.DataFrame) -> pd.DataFrame:
    """Resources with CPU utilization below the idle threshold."""
    mask = (
        (df["cpu_utilization_pct"] < IDLE_CPU_THRESHOLD) &
        (df["resource_type"].str.lower().isin(["ec2", "vm", "compute", "instance", "server"]))
    )
    return df[mask].copy()


def detect_oversized_instances(df: pd.DataFrame) -> pd.DataFrame:
    """Compute resources using less than OVERSIZED_CPU_THRESHOLD but not idle."""
    mask = (
        (df["cpu_utilization_pct"] >= IDLE_CPU_THRESHOLD) &
        (df["cpu_utilization_pct"] < OVERSIZED_CPU_THRESHOLD) &
        (df["resource_type"].str.lower().isin(["ec2", "vm", "compute", "instance", "server"]))
    )
    return df[mask].copy()


def detect_storage_waste(df: pd.DataFrame) -> pd.DataFrame:
    """Storage resources with very low utilization."""
    mask = (
        (df["storage_utilization_pct"] < STORAGE_WASTE_THRESHOLD * 100) &
        (df["resource_type"].str.lower().isin(["s3", "storage", "blob", "disk", "ebs", "gcs"]))
    )
    return df[mask].copy()


def detect_high_cost_resources(df: pd.DataFrame) -> pd.DataFrame:
    """Top N% most expensive resources."""
    threshold = df["monthly_cost_usd"].quantile(HIGH_COST_PERCENTILE / 100)
    return df[df["monthly_cost_usd"] >= threshold].copy()


def compute_summary(df: pd.DataFrame) -> dict:
    idle = detect_idle_resources(df)
    oversized = detect_oversized_instances(df)
    storage_waste = detect_storage_waste(df)
    high_cost = detect_high_cost_resources(df)

    total_cost = df["monthly_cost_usd"].sum()

    # Conservative savings estimates
    idle_savings = idle["monthly_cost_usd"].sum() * 0.90        # 90% if terminated
    oversized_savings = oversized["monthly_cost_usd"].sum() * 0.40  # 40% by rightsizing
    storage_savings = storage_waste["monthly_cost_usd"].sum() * 0.60  # 60% by cleanup
    total_savings = idle_savings + oversized_savings + storage_savings

    return {
        "total_cost": round(total_cost, 2),
        "total_resources": len(df),
        "idle_count": len(idle),
        "oversized_count": len(oversized),
        "storage_waste_count": len(storage_waste),
        "high_cost_count": len(high_cost),
        "potential_savings": round(total_savings, 2),
        "savings_pct": round((total_savings / total_cost * 100) if total_cost > 0 else 0, 1),
        "cost_by_type": df.groupby("resource_type")["monthly_cost_usd"].sum().to_dict(),
        "cost_by_region": df.groupby("region")["monthly_cost_usd"].sum().to_dict(),
    }
