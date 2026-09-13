"""
Agent Loop: Analyze → Evaluate → Recommend → Verify → Final Report
This module implements the AI agent that orchestrates all analysis steps
and iterates until confidence threshold is met or max iterations reached.
"""

import time
import pandas as pd
from config import AGENT_MAX_ITERATIONS, AGENT_CONFIDENCE_THRESHOLD
from cost_analyzer import load_and_clean, compute_summary
from recommendation_engine import generate_recommendations, get_summary_stats
from database import save_analysis_run, save_recommendations, save_agent_log
from api_client import fetch_exchange_rates


# Step names in the agent loop
STEPS = ["ANALYZE", "EVALUATE", "RECOMMEND", "VERIFY", "FINAL_REPORT"]


class CloudCostAgent:
    """
    Agent that runs a multi-step loop to analyze cloud cost data.
    Each iteration refines recommendations based on confidence scoring.
    """

    def __init__(self, df: pd.DataFrame, filename: str = "uploaded.csv"):
        self.df = df
        self.filename = filename
        self.iteration = 0
        self.confidence = 0.0
        self.logs = []          # list of dicts for UI display
        self.run_id = None
        self.summary = {}
        self.recommendations = []
        self.exchange_data = {}
        self.final_report = {}

    def _log(self, step: str, status: str, details: str):
        entry = {
            "iteration": self.iteration,
            "step": step,
            "status": status,
            "details": details,
            "timestamp": time.strftime("%H:%M:%S"),
        }
        self.logs.append(entry)
        if self.run_id:
            save_agent_log(self.run_id, self.iteration, step, status, details)

    def _step_analyze(self):
        """Step 1: Load, clean, and compute base statistics."""
        self.df = load_and_clean(self.df)
        self.summary = compute_summary(self.df)
        self._log("ANALYZE", "SUCCESS",
                  f"Loaded {self.summary['total_resources']} resources. "
                  f"Total cost: ${self.summary['total_cost']:,.2f}/month.")

    def _step_evaluate(self):
        """Step 2: Fetch external exchange rates and evaluate cost context."""
        self.exchange_data = fetch_exchange_rates()
        source = self.exchange_data.get("source", "unknown")
        rates_preview = {k: v for k, v in list(self.exchange_data.get("rates", {}).items())[:3]}
        self._log("EVALUATE", "SUCCESS",
                  f"Exchange rates fetched (source: {source}). "
                  f"Sample rates: {rates_preview}. "
                  f"Detected {self.summary['idle_count']} idle, "
                  f"{self.summary['oversized_count']} oversized, "
                  f"{self.summary['storage_waste_count']} wasteful storage resources.")

    def _step_recommend(self):
        """Step 3: Generate recommendations."""
        self.recommendations = generate_recommendations(self.df)
        stats = get_summary_stats(self.recommendations)
        self._log("RECOMMEND", "SUCCESS",
                  f"Generated {stats['total_recommendations']} recommendations. "
                  f"Estimated total savings: ${stats['total_estimated_savings']:,.2f}/month. "
                  f"Priority breakdown: {stats['by_priority']}.")

    def _step_verify(self):
        """Step 4: Verify recommendations for consistency and compute confidence."""
        issues = []
        verified = 0
        for rec in self.recommendations:
            # Basic consistency check: savings must not exceed current cost
            if rec["estimated_savings"] > rec["current_cost"]:
                issues.append(rec["resource_id"])
                rec["estimated_savings"] = round(rec["current_cost"] * 0.90, 2)
            else:
                verified += 1

        total = len(self.recommendations)
        self.confidence = (verified / total) if total > 0 else 1.0

        if issues:
            self._log("VERIFY", "WARNING",
                      f"Fixed {len(issues)} inconsistent savings estimates. "
                      f"Confidence: {self.confidence:.0%}.")
        else:
            self._log("VERIFY", "SUCCESS",
                      f"All {total} recommendations verified. "
                      f"Confidence: {self.confidence:.0%}.")

    def _step_final_report(self):
        """Step 5: Assemble final report data."""
        stats = get_summary_stats(self.recommendations)
        self.final_report = {
            "summary": self.summary,
            "recommendations": self.recommendations,
            "recommendation_stats": stats,
            "exchange_rates": self.exchange_data.get("rates", {}),
            "exchange_source": self.exchange_data.get("source", "fallback"),
            "confidence": self.confidence,
            "iterations_run": self.iteration,
        }
        self._log("FINAL_REPORT", "SUCCESS",
                  f"Final report assembled. {stats['total_recommendations']} actions identified. "
                  f"Save ${stats['total_estimated_savings']:,.2f}/month "
                  f"({self.summary.get('savings_pct', 0):.1f}% of total spend).")

    def run(self, progress_callback=None):
        """
        Execute the agent loop.
        progress_callback(step_name, iteration, total_iterations) is called at each step if provided.
        Returns self.final_report.
        """
        # Save initial DB record (no run_id yet)
        # We'll create it after first analysis
        while self.iteration < AGENT_MAX_ITERATIONS:
            self.iteration += 1

            if progress_callback:
                progress_callback("ANALYZE", self.iteration, AGENT_MAX_ITERATIONS)
            self._step_analyze()

            # Create DB record on first iteration
            if self.run_id is None:
                self.run_id = save_analysis_run(
                    filename=self.filename,
                    total_cost=self.summary["total_cost"],
                    total_resources=self.summary["total_resources"],
                    idle_count=self.summary["idle_count"],
                    oversized_count=self.summary["oversized_count"],
                    storage_waste_count=self.summary["storage_waste_count"],
                    potential_savings=self.summary["potential_savings"],
                    summary_dict=self.summary,
                )
                # Re-log with run_id now set
                for log in self.logs:
                    save_agent_log(self.run_id, log["iteration"], log["step"], log["status"], log["details"])

            if progress_callback:
                progress_callback("EVALUATE", self.iteration, AGENT_MAX_ITERATIONS)
            self._step_evaluate()

            if progress_callback:
                progress_callback("RECOMMEND", self.iteration, AGENT_MAX_ITERATIONS)
            self._step_recommend()

            if progress_callback:
                progress_callback("VERIFY", self.iteration, AGENT_MAX_ITERATIONS)
            self._step_verify()

            if progress_callback:
                progress_callback("FINAL_REPORT", self.iteration, AGENT_MAX_ITERATIONS)
            self._step_final_report()

            # Exit loop if confidence is high enough
            if self.confidence >= AGENT_CONFIDENCE_THRESHOLD:
                self._log("AGENT", "COMPLETE",
                          f"Confidence threshold met ({self.confidence:.0%} >= "
                          f"{AGENT_CONFIDENCE_THRESHOLD:.0%}) after {self.iteration} iteration(s).")
                break
            else:
                self._log("AGENT", "RETRY",
                          f"Confidence {self.confidence:.0%} below threshold. Retrying...")

        # Save recommendations to DB
        if self.run_id and self.recommendations:
            save_recommendations(self.run_id, self.recommendations)

        return self.final_report
