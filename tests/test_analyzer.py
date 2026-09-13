"""
Tests for cost_analyzer.py
Run with: pytest tests/test_analyzer.py -v
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import pytest
from cost_analyzer import (
    load_and_clean,
    detect_idle_resources,
    detect_oversized_instances,
    detect_storage_waste,
    detect_high_cost_resources,
    compute_summary,
)


@pytest.fixture
def sample_df():
    return pd.DataFrame({
        "resource_id":             ["i-001", "i-002", "i-003", "bucket-001", "vol-001"],
        "resource_type":           ["ec2",   "ec2",   "ec2",   "s3",         "ebs"],
        "region":                  ["us-east-1"] * 5,
        "monthly_cost_usd":        [200.0,   150.0,   80.0,    50.0,         30.0],
        "cpu_utilization_pct":     [2.0,     15.0,    75.0,    0.0,          0.0],
        "storage_utilization_pct": [60.0,    40.0,    80.0,    5.0,          10.0],
    })


def test_load_and_clean_types(sample_df):
    cleaned = load_and_clean(sample_df)
    assert cleaned["monthly_cost_usd"].dtype == float
    assert cleaned["cpu_utilization_pct"].dtype == float
    assert cleaned["storage_utilization_pct"].dtype == float


def test_load_and_clean_strips_strings(sample_df):
    sample_df["resource_id"] = ["  i-001  ", "i-002", "i-003", "bucket-001", "vol-001"]
    cleaned = load_and_clean(sample_df)
    assert cleaned.iloc[0]["resource_id"] == "i-001"


def test_detect_idle_resources(sample_df):
    idle = detect_idle_resources(sample_df)
    # i-001 has 2.0% CPU → idle
    assert "i-001" in idle["resource_id"].values
    # i-002 has 15% CPU → not idle
    assert "i-002" not in idle["resource_id"].values


def test_detect_oversized_instances(sample_df):
    oversized = detect_oversized_instances(sample_df)
    # i-002 has 15% → oversized (between idle threshold 5% and oversized threshold 20%)
    assert "i-002" in oversized["resource_id"].values
    # i-003 has 75% → not oversized
    assert "i-003" not in oversized["resource_id"].values


def test_detect_storage_waste(sample_df):
    waste = detect_storage_waste(sample_df)
    # bucket-001 has 5% storage utilization → waste
    assert "bucket-001" in waste["resource_id"].values
    # vol-001 has 10% storage → also waste (ebs type, below 20%)
    assert "vol-001" in waste["resource_id"].values


def test_detect_high_cost_resources(sample_df):
    high = detect_high_cost_resources(sample_df)
    # Top 10% of 5 rows → the most expensive
    assert len(high) >= 1
    assert high["monthly_cost_usd"].max() == 200.0


def test_compute_summary_total_cost(sample_df):
    summary = compute_summary(sample_df)
    assert summary["total_cost"] == pytest.approx(510.0, rel=1e-3)


def test_compute_summary_counts(sample_df):
    summary = compute_summary(sample_df)
    assert summary["total_resources"] == 5
    assert summary["idle_count"] >= 1
    assert summary["oversized_count"] >= 1
    assert summary["storage_waste_count"] >= 1


def test_compute_summary_potential_savings_positive(sample_df):
    summary = compute_summary(sample_df)
    assert summary["potential_savings"] > 0


def test_compute_summary_cost_by_region(sample_df):
    summary = compute_summary(sample_df)
    assert "us-east-1" in summary["cost_by_region"]
    assert summary["cost_by_region"]["us-east-1"] == pytest.approx(510.0, rel=1e-3)


def test_empty_dataframe():
    empty = pd.DataFrame(columns=[
        "resource_id", "resource_type", "region",
        "monthly_cost_usd", "cpu_utilization_pct", "storage_utilization_pct"
    ])
    summary = compute_summary(empty)
    assert summary["total_cost"] == 0.0
    assert summary["total_resources"] == 0


def test_missing_values_handled():
    df = pd.DataFrame({
        "resource_id":             ["i-bad"],
        "resource_type":           ["ec2"],
        "region":                  ["us-east-1"],
        "monthly_cost_usd":        [None],
        "cpu_utilization_pct":     [None],
        "storage_utilization_pct": [None],
    })
    cleaned = load_and_clean(df)
    assert cleaned.iloc[0]["monthly_cost_usd"] == 0.0
    assert cleaned.iloc[0]["cpu_utilization_pct"] == 0.0
