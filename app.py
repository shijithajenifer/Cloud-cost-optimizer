"""
Cloud Cost Optimizer AI Agent — Streamlit Dashboard
"""

import io
import os
import time
import datetime
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from github_api import get_repo_info

from database import init_db, get_all_runs, get_recommendations_for_run, get_agent_logs_for_run
from agent import CloudCostAgent
from report_generator import generate_pdf_report
from api_client import fetch_exchange_rates, convert_cost, get_currency_symbol
from utils import validate_csv, format_currency, priority_color


# ─────────────────────────── Page config ────────────────────────────
st.set_page_config(
    page_title="Cloud Cost Optimizer",
    page_icon="☁️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────── CSS ─────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=IBM+Plex+Sans:wght@300;400;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'IBM Plex Sans', sans-serif;
}
h1, h2, h3 { font-family: 'IBM Plex Mono', monospace; }

.metric-card {
    background: linear-gradient(135deg, #0a1628 0%, #0d2040 100%);
    border: 1px solid #1e3a5f;
    border-radius: 10px;
    padding: 18px 22px;
    text-align: center;
    margin-bottom: 8px;
}
.metric-card .label {
    font-size: 11px;
    color: #7a9cc4;
    text-transform: uppercase;
    letter-spacing: 1px;
    margin-bottom: 6px;
}
.metric-card .value {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 26px;
    font-weight: 700;
    color: #4fc3f7;
}
.metric-card .sub {
    font-size: 12px;
    color: #90caf9;
    margin-top: 4px;
}

.rec-card {
    border-left: 4px solid #4fc3f7;
    background: #0d1f33;
    border-radius: 6px;
    padding: 14px 18px;
    margin-bottom: 10px;
}
.rec-card.high { border-left-color: #ff4b4b; }
.rec-card.medium { border-left-color: #ffa500; }
.rec-card.low { border-left-color: #00c853; }

.agent-step {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 8px 12px;
    border-radius: 6px;
    margin-bottom: 6px;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 13px;
}
.step-success { background: #0a2a1a; color: #00c853; }
.step-warning  { background: #2a1e00; color: #ffa500; }
.step-retry    { background: #2a0a0a; color: #ff4b4b; }
.step-complete { background: #0a1a2a; color: #4fc3f7; }

.savings-banner {
    background: linear-gradient(135deg, #0a4a2a, #0a2a1a);
    border: 1px solid #00c853;
    border-radius: 10px;
    padding: 20px;
    text-align: center;
    margin: 12px 0;
}
.savings-banner .amount {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 42px;
    font-weight: 700;
    color: #00e676;
}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────── Init ────────────────────────────────────
init_db()

# ─────────────────────────── Sidebar ─────────────────────────────────
with st.sidebar:
    st.markdown("## ☁️ Cloud Cost Optimizer")
    st.markdown("**AI-powered cloud spend analysis**")
    st.divider()

    page = st.radio(
        "Navigation",
        ["🏠 Dashboard", "📊 Analysis History", "ℹ️ About"],
        label_visibility="collapsed"
    )

    st.divider()
    st.markdown("**Currency**")
    currency = st.selectbox(
        "Display currency",
        ["USD", "INR", "EUR", "GBP", "CAD", "AUD", "JPY", "SGD"],
        label_visibility="collapsed"
    )

    st.divider()
    st.caption("AI Prototype Challenge — VSB Group\nBuilt with Python · Streamlit · SQLite")


# ════════════════════════════════════════════
#  PAGE: DASHBOARD
# ════════════════════════════════════════════
if page == "🏠 Dashboard":
    st.title("☁️ Cloud Cost Optimizer")
    st.markdown("Upload your cloud billing CSV and let the AI agent find savings.")
    st.divider()

    # ── File upload ──
    col_up, col_demo = st.columns([3, 1])
    with col_up:
        uploaded_file = st.file_uploader(
            "Upload Cloud Billing CSV",
            type=["csv"],
            help="Must contain: resource_id, resource_type, region, monthly_cost_usd, "
                 "cpu_utilization_pct, storage_utilization_pct"
        )
    with col_demo:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("📂 Load Sample Data", use_container_width=True):
            st.session_state["use_sample"] = True

    # Determine data source
    df = None
    source_name = None

    if uploaded_file:
        try:
            df = pd.read_csv(uploaded_file)
            source_name = uploaded_file.name
            st.session_state.pop("use_sample", None)
        except Exception as e:
            st.error(f"Could not read CSV: {e}")

    elif st.session_state.get("use_sample"):
        sample_path = os.path.join("sample_data", "cloud_costs.csv")
        if os.path.exists(sample_path):
            df = pd.read_csv(sample_path)
            source_name = "cloud_costs.csv (sample)"
            st.info("📂 Sample data loaded.")
        else:
            st.error("Sample data not found. Please upload a CSV.")

    # ── Validate & analyze ──
    if df is not None:
        valid, msg = validate_csv(df)
        if not valid:
            st.error(f"❌ Invalid CSV: {msg}")
            st.stop()

        # Preview
        with st.expander("📋 Data Preview", expanded=False):
            st.dataframe(df.head(10), use_container_width=True)
            st.caption(f"{len(df)} rows · {len(df.columns)} columns")

        st.divider()
        st.markdown("### 🤖 Agent Loop")

        # ── Run agent ──
               # ── Run agent ──
        if st.button("▶ Run AI Analysis", type="primary", use_container_width=True):
            agent = CloudCostAgent(df, filename=source_name or "uploaded.csv")

            progress_bar = st.progress(0, text="Starting agent...")
            step_log_placeholder = st.empty()
            step_names = ["ANALYZE", "EVALUATE", "RECOMMEND", "VERIFY", "FINAL_REPORT"]
            log_store = {"html": ""}

            def ui_callback(step, iteration, max_iter):
                idx = step_names.index(step) if step in step_names else 0
                pct = int(((idx + 1) / len(step_names)) * 100)
                progress_bar.progress(pct, text=f"Step {idx+1}/{len(step_names)}: {step}...")
                icons = {
                    "ANALYZE": "🔍", "EVALUATE": "📡", "RECOMMEND": "💡",
                    "VERIFY": "✅", "FINAL_REPORT": "📄"
                }
                log_store["html"] += (
                    f'<div class="agent-step step-success">'
                    f'{icons.get(step,"•")} [{iteration}] {step} — running...</div>'
                )
                step_log_placeholder.markdown(log_store["html"], unsafe_allow_html=True)

            with st.spinner("Agent working..."):
                final_report = agent.run(progress_callback=ui_callback)

            progress_bar.progress(100, text="Complete!")
            st.session_state["final_report"] = final_report
            st.session_state["agent_logs"] = agent.logs
            st.session_state["currency"] = currency
            st.success("✅ Analysis complete!")

        # ── Show results ──
        if "final_report" in st.session_state:
            final_report = st.session_state["final_report"]
            summary = final_report["summary"]
            recommendations = final_report["recommendations"]

            # Fetch rates for currency conversion
            rate_data = fetch_exchange_rates()
            rates = rate_data.get("rates", {"USD": 1.0})
            sym = get_currency_symbol(currency)

            def cvt(usd_val):
                return convert_cost(usd_val, currency, rates)

            st.divider()
            st.markdown("### 📊 Summary")

            m1, m2, m3, m4, m5 = st.columns(5)
            with m1:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="label">Total Monthly Cost</div>
                    <div class="value">{sym}{cvt(summary['total_cost']):,.0f}</div>
                    <div class="sub">{currency}</div>
                </div>""", unsafe_allow_html=True)
            with m2:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="label">Resources</div>
                    <div class="value">{summary['total_resources']}</div>
                    <div class="sub">analyzed</div>
                </div>""", unsafe_allow_html=True)
            with m3:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="label">Idle Resources</div>
                    <div class="value">{summary['idle_count']}</div>
                    <div class="sub">detected</div>
                </div>""", unsafe_allow_html=True)
            with m4:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="label">Oversized</div>
                    <div class="value">{summary['oversized_count']}</div>
                    <div class="sub">instances</div>
                </div>""", unsafe_allow_html=True)
            with m5:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="label">Storage Waste</div>
                    <div class="value">{summary['storage_waste_count']}</div>
                    <div class="sub">resources</div>
                </div>""", unsafe_allow_html=True)

            # Savings banner
            st.markdown(f"""
            <div class="savings-banner">
                <div style="color:#7fffb0;font-size:13px;letter-spacing:2px;margin-bottom:6px;">
                    ESTIMATED MONTHLY SAVINGS
                </div>
                <div class="amount">{sym}{cvt(summary['potential_savings']):,.2f}</div>
                <div style="color:#90caf9;font-size:14px;margin-top:6px;">
                    {summary['savings_pct']:.1f}% of total spend · 
                    Confidence: {final_report['confidence']:.0%}
                </div>
            </div>
            """, unsafe_allow_html=True)

            # Charts
            st.divider()
            st.markdown("### 📈 Cost Breakdown")
            c1, c2 = st.columns(2)

            with c1:
                cost_by_type = summary.get("cost_by_type", {})
                if cost_by_type:
                    fig = px.pie(
                        names=list(cost_by_type.keys()),
                        values=[cvt(v) for v in cost_by_type.values()],
                        title=f"Cost by Resource Type ({currency})",
                        color_discrete_sequence=px.colors.sequential.Blues_r,
                        hole=0.4,
                    )
                    fig.update_layout(
                        paper_bgcolor="rgba(0,0,0,0)",
                        plot_bgcolor="rgba(0,0,0,0)",
                        font_color="#c9d8f0"
                    )
                    st.plotly_chart(fig, use_container_width=True)

            with c2:
                cost_by_region = summary.get("cost_by_region", {})
                if cost_by_region:
                    fig2 = px.bar(
                        x=list(cost_by_region.keys()),
                        y=[cvt(v) for v in cost_by_region.values()],
                        title=f"Cost by Region ({currency})",
                        labels={"x": "Region", "y": f"Cost ({sym})"},
                        color=[cvt(v) for v in cost_by_region.values()],
                        color_continuous_scale="Blues",
                    )
                    fig2.update_layout(
                        paper_bgcolor="rgba(0,0,0,0)",
                        plot_bgcolor="rgba(0,0,0,0)",
                        font_color="#c9d8f0",
                        showlegend=False,
                    )
                    st.plotly_chart(fig2, use_container_width=True)

            # Recommendations
            st.divider()
            st.markdown(f"### 💡 Recommendations ({len(recommendations)})")

            filter_priority = st.multiselect(
                "Filter by Priority",
                ["High", "Medium", "Low"],
                default=["High", "Medium", "Low"]
            )
            filtered_recs = [r for r in recommendations if r["priority"] in filter_priority]

            if not filtered_recs:
                st.info("No recommendations match the selected filters.")
            else:
                for rec in filtered_recs:
                    p = rec["priority"].lower()
                    st.markdown(f"""
                    <div class="rec-card {p}">
                        <strong>[{rec['priority']}] {rec['issue_type']}</strong>
                        — <code>{rec['resource_id']}</code>
                        &nbsp;·&nbsp; <em>{rec.get('resource_type','')} · {rec.get('region','')}</em><br>
                        <span style="font-size:13px;color:#c9d8f0;">{rec['recommendation']}</span><br>
                        <span style="font-size:12px;color:#7a9cc4;">
                            Current: {sym}{cvt(rec['current_cost']):,.2f}/mo &nbsp;→&nbsp;
                            Save: <strong style="color:#00e676;">{sym}{cvt(rec['estimated_savings']):,.2f}/mo</strong>
                        </span>
                    </div>
                    """, unsafe_allow_html=True)

            # Agent Logs
            st.divider()
            st.markdown("### 🔁 Agent Loop Trace")
            with st.expander("Show agent step-by-step log", expanded=False):
                css_map = {
                    "SUCCESS": "step-success",
                    "WARNING": "step-warning",
                    "RETRY": "step-retry",
                    "COMPLETE": "step-complete",
                }
                for log in st.session_state.get("agent_logs", []):
                    css = css_map.get(log["status"], "step-success")
                    st.markdown(
                        f'<div class="agent-step {css}">'
                        f'[iter {log["iteration"]}] '
                        f'<strong>{log["step"]}</strong> — {log["status"]} '
                        f'<span style="opacity:.6;font-size:11px;">{log["timestamp"]}</span><br>'
                        f'<span style="font-size:12px;">{log["details"]}</span>'
                        f'</div>',
                        unsafe_allow_html=True
                    )

            # Download
            st.divider()
            st.markdown("### 📥 Download Report")
            col_dl1, col_dl2 = st.columns(2)

            with col_dl1:
                # CSV export
                rec_df = pd.DataFrame(filtered_recs)
                if not rec_df.empty:
                    csv_bytes = rec_df.to_csv(index=False).encode()
                    st.download_button(
                        "⬇ Download Recommendations (CSV)",
                        data=csv_bytes,
                        file_name="recommendations.csv",
                        mime="text/csv",
                        use_container_width=True
                    )

            with col_dl2:
                if st.button("📄 Generate PDF Report", use_container_width=True):
                    with st.spinner("Generating PDF..."):
                        pdf_path = generate_pdf_report(
                            final_report,
                            filename=f"report_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
                        )
                    with open(pdf_path, "rb") as f:
                        st.download_button(
                            "⬇ Download PDF",
                            data=f.read(),
                            file_name=os.path.basename(pdf_path),
                            mime="application/pdf",
                            use_container_width=True
                        )
st.divider()
st.markdown("### 🔗 GitHub Repository Insights")

repo_name = st.text_input(
    "GitHub Repository",
    placeholder="streamlit/streamlit"
)

if st.button("Fetch GitHub Data"):
    repo = get_repo_info(repo_name)

    if repo:
        c1, c2, c3, c4 = st.columns(4)

        c1.metric("⭐ Stars", repo["stars"])
        c2.metric("🍴 Forks", repo["forks"])
        c3.metric("🐞 Issues", repo["open_issues"])
        c4.metric("🕒 Updated", repo["last_updated"][:10])

    else:
        st.error("Repository not found")

# ════════════════════════════════════════════
#  PAGE: HISTORY
# ════════════════════════════════════════════
elif page == "📊 Analysis History":
    st.title("📊 Analysis History")
    st.markdown("Past analysis runs stored in SQLite.")
    st.divider()

    runs = get_all_runs()
    if not runs:
        st.info("No analysis runs yet. Go to Dashboard and upload a CSV.")
    else:
        for run in runs:
            with st.expander(
                f"📁 {run['filename']}  —  {run['run_timestamp'][:19]}  "
                f"  |  Total: ${run['total_cost']:,.2f}  |  Savings: ${run['potential_savings']:,.2f}"
            ):
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Resources", run["total_resources"])
                c2.metric("Idle", run["idle_count"])
                c3.metric("Oversized", run["oversized_count"])
                c4.metric("Storage Waste", run["storage_waste_count"])

                recs = get_recommendations_for_run(run["id"])
                if recs:
                    st.markdown(f"**{len(recs)} Recommendations**")
                    st.dataframe(
                        pd.DataFrame(recs)[["resource_id", "issue_type", "priority",
                                            "current_cost", "estimated_savings", "recommendation"]],
                        use_container_width=True,
                    )

                logs = get_agent_logs_for_run(run["id"])
                if logs:
                    st.markdown(f"**Agent Steps ({len(logs)} logged)**")
                    st.dataframe(
                        pd.DataFrame(logs)[["step_number", "step_name", "status", "details", "timestamp"]],
                        use_container_width=True
                    )


# ════════════════════════════════════════════
#  PAGE: ABOUT
# ════════════════════════════════════════════
elif page == "ℹ️ About":
    st.title("ℹ️ About")
    st.markdown("""
## Cloud Cost Optimizer AI Agent

**Built for:** AI Prototype Challenge — VSB Group  
**Stack:** Python · Streamlit · SQLite · Pandas · Plotly · fpdf2

---

### Agent Loop
```
ANALYZE → EVALUATE → RECOMMEND → VERIFY → FINAL_REPORT
```
The agent loops until confidence ≥ 75% or max iterations reached.

### External API
Uses **exchangerate.host** (free, no API key required) to fetch live  
USD exchange rates for multi-currency reporting.

### Capabilities Demonstrated
- ✅ Agent Loop
- ✅ External API Integration
- ✅ AI-Assisted Development
- ✅ SQLite Persistence
- ✅ PDF Report Generation

### Evaluation Criteria Addressed
| # | Area | How |
|---|------|-----|
| 1 | Working code with AI | Claude-assisted development |
| 2 | AI Agents | Iterative agent loop |
| 3 | MCP / External API | exchangerate.host API |
| 4 | API Integration | Full api_client.py module |
| 5 | End-to-end usability | Streamlit dashboard + PDF |
| 6 | Documentation | README, AI_USAGE_NOTE, tests |
""")
