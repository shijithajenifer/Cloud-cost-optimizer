"""
Generate a downloadable PDF report from agent results using fpdf2.
"""

import os
import datetime
from fpdf import FPDF
from config import REPORT_DIR


class CostReport(FPDF):
    def header(self):
        self.set_font("Helvetica", "B", 14)
        self.set_text_color(0, 72, 144)
        self.cell(0, 10, "Cloud Cost Optimizer - Analysis Report", align="C", new_x="LMARGIN", new_y="NEXT")
        self.set_font("Helvetica", "", 9)
        self.set_text_color(100, 100, 100)
        self.cell(0, 6, f"Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                  align="C", new_x="LMARGIN", new_y="NEXT")
        self.ln(3)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(150, 150, 150)
        self.cell(0, 10, f"Page {self.page_no()}", align="C")

    def section_title(self, title: str):
        self.set_font("Helvetica", "B", 12)
        self.set_text_color(0, 72, 144)
        self.set_fill_color(230, 240, 255)
        self.cell(0, 8, title, fill=True, new_x="LMARGIN", new_y="NEXT")
        self.ln(2)

    def kv_row(self, key: str, value: str):
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(60, 60, 60)
        self.cell(70, 7, key + ":")
        self.set_font("Helvetica", "", 10)
        self.set_text_color(0, 0, 0)
        self.cell(0, 7, str(value), new_x="LMARGIN", new_y="NEXT")

    def rec_row(self, rec: dict, idx: int):
        priority_colors = {
            "High": (255, 75, 75),
            "Medium": (255, 165, 0),
            "Low": (0, 200, 83),
        }
        color = priority_colors.get(rec.get("priority", "Medium"), (128, 128, 128))
        self.set_font("Helvetica", "B", 9)
        self.set_text_color(*color)
        self.cell(0, 6, f"[{rec.get('priority','?')}] {rec.get('issue_type','')} — {rec.get('resource_id','')}",
                  new_x="LMARGIN", new_y="NEXT")
        self.set_font("Helvetica", "", 9)
        self.set_text_color(40, 40, 40)
        self.multi_cell(0, 5, rec.get("recommendation", ""), new_x="LMARGIN", new_y="NEXT")
        self.set_font("Helvetica", "I", 9)
        self.set_text_color(80, 80, 80)
        self.cell(0, 5,
                  f"  Current Cost: ${rec.get('current_cost', 0):.2f}/mo  |  "
                  f"Estimated Saving: ${rec.get('estimated_savings', 0):.2f}/mo",
                  new_x="LMARGIN", new_y="NEXT")
        self.ln(2)


def generate_pdf_report(final_report: dict, filename: str = "cloud_cost_report.pdf") -> str:
    """
    Generate a PDF report from the agent's final_report dict.
    Returns the file path of the saved PDF.
    """
    summary = final_report.get("summary", {})
    recommendations = final_report.get("recommendations", [])
    stats = final_report.get("recommendation_stats", {})

    pdf = CostReport()
    pdf.add_page()

    # ---- Executive Summary ----
    pdf.section_title("Executive Summary")
    pdf.kv_row("Total Monthly Spend", f"${summary.get('total_cost', 0):,.2f}")
    pdf.kv_row("Total Resources Analyzed", str(summary.get("total_resources", 0)))
    pdf.kv_row("Potential Monthly Savings", f"${summary.get('potential_savings', 0):,.2f}")
    pdf.kv_row("Savings Opportunity", f"{summary.get('savings_pct', 0):.1f}% of total spend")
    pdf.kv_row("Analysis Confidence", f"{final_report.get('confidence', 0):.0%}")
    pdf.kv_row("Agent Iterations", str(final_report.get("iterations_run", 1)))
    pdf.ln(4)

    # ---- Issues Detected ----
    pdf.section_title("Issues Detected")
    pdf.kv_row("Idle Resources", str(summary.get("idle_count", 0)))
    pdf.kv_row("Oversized Instances", str(summary.get("oversized_count", 0)))
    pdf.kv_row("Storage Waste", str(summary.get("storage_waste_count", 0)))
    pdf.kv_row("Total Recommendations", str(stats.get("total_recommendations", 0)))
    pdf.ln(4)

    # ---- Cost by Region ----
    pdf.section_title("Cost by Region")
    for region, cost in summary.get("cost_by_region", {}).items():
        pdf.kv_row(region, f"${cost:,.2f}")
    pdf.ln(4)

    # ---- Recommendations ----
    pdf.section_title("Recommendations")
    if not recommendations:
        pdf.set_font("Helvetica", "I", 10)
        pdf.cell(0, 7, "No recommendations generated.", new_x="LMARGIN", new_y="NEXT")
    else:
        for i, rec in enumerate(recommendations, 1):
            pdf.rec_row(rec, i)

    # Save
    out_path = os.path.join(REPORT_DIR, filename)
    pdf.output(out_path)
    return out_path
