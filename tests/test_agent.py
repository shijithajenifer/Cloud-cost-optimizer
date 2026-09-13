"""
Tests for agent.py
Run with: pytest tests/test_agent.py -v
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import pytest
from agent import CloudCostAgent


@pytest.fixture
def sample_df():
    return pd.DataFrame({
        "resource_id":             ["i-001", "i-002", "bucket-001"],
        "resource_type":           ["ec2",   "ec2",   "s3"],
        "region":                  ["us-east-1", "us-west-2", "us-east-1"],
        "monthly_cost_usd":        [300.0,  120.0,  60.0],
        "cpu_utilization_pct":     [1.5,    75.0,   0.0],
        "storage_utilization_pct": [50.0,   80.0,   8.0],
    })


def test_agent_runs_and_returns_report(sample_df):
    agent = CloudCostAgent(sample_df, filename="test.csv")
    report = agent.run()
    assert isinstance(report, dict)
    assert "summary" in report
    assert "recommendations" in report
    assert "confidence" in report


def test_agent_confidence_between_0_and_1(sample_df):
    agent = CloudCostAgent(sample_df, filename="test.csv")
    report = agent.run()
    assert 0.0 <= report["confidence"] <= 1.0


def test_agent_logs_populated(sample_df):
    agent = CloudCostAgent(sample_df, filename="test.csv")
    agent.run()
    assert len(agent.logs) > 0


def test_agent_recommendations_have_required_keys(sample_df):
    agent = CloudCostAgent(sample_df, filename="test.csv")
    report = agent.run()
    for rec in report["recommendations"]:
        assert "resource_id" in rec
        assert "issue_type" in rec
        assert "priority" in rec
        assert "estimated_savings" in rec
        assert "recommendation" in rec


def test_agent_savings_not_exceed_cost(sample_df):
    agent = CloudCostAgent(sample_df, filename="test.csv")
    report = agent.run()
    for rec in report["recommendations"]:
        assert rec["estimated_savings"] <= rec["current_cost"], (
            f"Savings {rec['estimated_savings']} > current cost {rec['current_cost']} "
            f"for {rec['resource_id']}"
        )


def test_agent_detects_idle(sample_df):
    agent = CloudCostAgent(sample_df, filename="test.csv")
    report = agent.run()
    issue_types = [r["issue_type"] for r in report["recommendations"]]
    assert "Idle Resource" in issue_types


def test_agent_iterations_within_max(sample_df):
    from config import AGENT_MAX_ITERATIONS
    agent = CloudCostAgent(sample_df, filename="test.csv")
    report = agent.run()
    assert report["iterations_run"] <= AGENT_MAX_ITERATIONS


def test_agent_with_no_idle_resources():
    df = pd.DataFrame({
        "resource_id":             ["i-healthy"],
        "resource_type":           ["ec2"],
        "region":                  ["us-east-1"],
        "monthly_cost_usd":        [100.0],
        "cpu_utilization_pct":     [80.0],
        "storage_utilization_pct": [75.0],
    })
    agent = CloudCostAgent(df, filename="healthy.csv")
    report = agent.run()
    assert report is not None
    assert report["summary"]["idle_count"] == 0
