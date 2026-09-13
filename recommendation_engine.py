import pandas as pd
from cost_analyzer import (
    detect_idle_resources,
    detect_oversized_instances,
    detect_storage_waste,
    detect_high_cost_resources,
)


def generate_recommendations(df: pd.DataFrame) -> list[dict]:
    """
    Produce a list of recommendation dicts for each problematic resource.
    Each dict contains: resource_id, resource_type, issue_type, current_cost,
    estimated_savings, recommendation, priority.
    """
    recommendations = []

    # --- Idle Resources ---
    for _, row in detect_idle_resources(df).iterrows():
        savings = round(row["monthly_cost_usd"] * 0.90, 2)
        recommendations.append({
            "resource_id": row["resource_id"],
            "resource_type": row["resource_type"],
            "region": row.get("region", ""),
            "issue_type": "Idle Resource",
            "current_cost": round(row["monthly_cost_usd"], 2),
            "estimated_savings": savings,
            "recommendation": (
                f"Resource '{row['resource_id']}' has only {row['cpu_utilization_pct']:.1f}% CPU usage. "
                f"Consider terminating or stopping this instance. "
                f"Estimated monthly saving: ${savings:.2f}."
            ),
            "priority": "High",
        })

    # --- Oversized Instances ---
    for _, row in detect_oversized_instances(df).iterrows():
        savings = round(row["monthly_cost_usd"] * 0.40, 2)
        recommendations.append({
            "resource_id": row["resource_id"],
            "resource_type": row["resource_type"],
            "region": row.get("region", ""),
            "issue_type": "Oversized Instance",
            "current_cost": round(row["monthly_cost_usd"], 2),
            "estimated_savings": savings,
            "recommendation": (
                f"Resource '{row['resource_id']}' uses only {row['cpu_utilization_pct']:.1f}% CPU. "
                f"Downsize to a smaller instance type. "
                f"Estimated monthly saving: ${savings:.2f}."
            ),
            "priority": "Medium",
        })

    # --- Storage Waste ---
    for _, row in detect_storage_waste(df).iterrows():
        savings = round(row["monthly_cost_usd"] * 0.60, 2)
        recommendations.append({
            "resource_id": row["resource_id"],
            "resource_type": row["resource_type"],
            "region": row.get("region", ""),
            "issue_type": "Storage Waste",
            "current_cost": round(row["monthly_cost_usd"], 2),
            "estimated_savings": savings,
            "recommendation": (
                f"Storage resource '{row['resource_id']}' is only "
                f"{row['storage_utilization_pct']:.1f}% utilized. "
                f"Delete unused data or resize storage volume. "
                f"Estimated monthly saving: ${savings:.2f}."
            ),
            "priority": "Medium",
        })

    # Sort: High → Medium → Low, then by savings descending
    priority_order = {"High": 0, "Medium": 1, "Low": 2}
    recommendations.sort(
        key=lambda r: (priority_order.get(r["priority"], 3), -r["estimated_savings"])
    )
    return recommendations


def get_summary_stats(recommendations: list[dict]) -> dict:
    total_savings = sum(r["estimated_savings"] for r in recommendations)
    by_priority = {"High": 0, "Medium": 0, "Low": 0}
    by_issue = {}
    for r in recommendations:
        by_priority[r["priority"]] = by_priority.get(r["priority"], 0) + 1
        by_issue[r["issue_type"]] = by_issue.get(r["issue_type"], 0) + 1
    return {
        "total_recommendations": len(recommendations),
        "total_estimated_savings": round(total_savings, 2),
        "by_priority": by_priority,
        "by_issue_type": by_issue,
    }
