# Test Cases

**Project:** Cloud Cost Optimizer AI Agent  
**Test Framework:** pytest

---

## How to Run Tests

```bash
# Activate virtual environment first
pytest tests/ -v
```

---

## Test Suite: test_analyzer.py

| # | Test Name | Input | Expected Output | Pass Condition |
|---|-----------|-------|-----------------|----------------|
| 1 | `test_load_and_clean_types` | DataFrame with string cost values | Columns are float type | `dtype == float` |
| 2 | `test_load_and_clean_strips_strings` | resource_id with spaces `"  i-001  "` | Stripped to `"i-001"` | `== "i-001"` |
| 3 | `test_detect_idle_resources` | EC2 with 2.0% CPU | Resource included in idle | `"i-001" in idle` |
| 4 | `test_detect_idle_resources` (negative) | EC2 with 15% CPU | Resource NOT in idle | `"i-002" not in idle` |
| 5 | `test_detect_oversized_instances` | EC2 with 15% CPU | Resource in oversized | `"i-002" in oversized` |
| 6 | `test_detect_oversized_instances` (negative) | EC2 with 75% CPU | Resource NOT oversized | `"i-003" not in oversized` |
| 7 | `test_detect_storage_waste` | S3 at 5% utilization | Resource flagged as waste | `"bucket-001" in waste` |
| 8 | `test_detect_storage_waste` (EBS) | EBS at 10% utilization | Resource flagged as waste | `"vol-001" in waste` |
| 9 | `test_detect_high_cost_resources` | 5 resources, top 10% | Most expensive flagged | `max == 200.0` |
| 10 | `test_compute_summary_total_cost` | 5 resources summing to $510 | `total_cost == 510.0` | `approx(510.0)` |
| 11 | `test_compute_summary_counts` | Mixed resource types | Correct counts returned | All counts ≥ 1 |
| 12 | `test_compute_summary_potential_savings_positive` | Resources with issues | `potential_savings > 0` | `> 0` |
| 13 | `test_compute_summary_cost_by_region` | All in us-east-1 | Region key present | Key exists, value correct |
| 14 | `test_empty_dataframe` | Empty DataFrame | Zero costs, zero counts | All zeros |
| 15 | `test_missing_values_handled` | None in numeric cols | Replaced with 0.0 | `== 0.0` |

---

## Test Suite: test_agent.py

| # | Test Name | Input | Expected Output | Pass Condition |
|---|-----------|-------|-----------------|----------------|
| 1 | `test_agent_runs_and_returns_report` | Valid DataFrame | Report dict returned | Has `summary`, `recommendations`, `confidence` keys |
| 2 | `test_agent_confidence_between_0_and_1` | Valid DataFrame | Confidence in [0, 1] | `0.0 <= confidence <= 1.0` |
| 3 | `test_agent_logs_populated` | Valid DataFrame | Logs list not empty | `len(logs) > 0` |
| 4 | `test_agent_recommendations_have_required_keys` | Valid DataFrame | Each rec has required keys | All keys present |
| 5 | `test_agent_savings_not_exceed_cost` | Valid DataFrame | No rec saves more than it costs | `savings <= current_cost` |
| 6 | `test_agent_detects_idle` | EC2 at 1.5% CPU | Idle Resource in issue types | `"Idle Resource" in issue_types` |
| 7 | `test_agent_iterations_within_max` | Valid DataFrame | Iterations ≤ AGENT_MAX_ITERATIONS | `<= 5` |
| 8 | `test_agent_with_no_idle_resources` | EC2 at 80% CPU | Zero idle resources | `idle_count == 0` |

---

## Manual / Happy Path Tests

| # | Scenario | Steps | Expected |
|---|----------|-------|----------|
| 1 | Upload valid CSV | Open app → Upload `cloud_costs.csv` → Click Run | Dashboard loads, recommendations shown |
| 2 | Load sample data | Click "Load Sample Data" → Run Analysis | Same as above with 30 resources |
| 3 | Currency switch | Change currency to INR → Run analysis | All costs show ₹ symbol, values converted |
| 4 | Filter recommendations | Uncheck Medium from filter | Only High and Low recommendations shown |
| 5 | Download CSV | Click "Download Recommendations (CSV)" | File downloaded with recommendations |
| 6 | Generate PDF | Click "Generate PDF Report" → Download | PDF with executive summary downloaded |
| 7 | History page | After analysis, go to History page | Previous run shown with all details |
| 8 | Invalid CSV | Upload CSV missing `cpu_utilization_pct` column | Error message: "Missing required columns" |
| 9 | Empty CSV | Upload CSV with headers only | Error message: "CSV file is empty" |
| 10 | API fallback | Disconnect internet, run analysis | Fallback exchange rates used, no crash |
