import os

# Database
DB_PATH = "cloud_optimizer.db"

# Free external API - Open Exchange Rates (free tier, no key needed for USD base)
# We use exchangerate.host which is completely free
EXCHANGE_API_URL = "https://api.exchangerate.host/latest"
EXCHANGE_API_BASE = "USD"

# Agent loop settings
AGENT_MAX_ITERATIONS = 5
AGENT_CONFIDENCE_THRESHOLD = 0.75

# Thresholds for detection
IDLE_CPU_THRESHOLD = 5.0          # % CPU usage below this = idle
OVERSIZED_CPU_THRESHOLD = 20.0    # % CPU usage below this = potentially oversized
STORAGE_WASTE_THRESHOLD = 0.20    # Less than 20% utilization = wasted storage
HIGH_COST_PERCENTILE = 90         # Top 10% spenders flagged

# Report output folder
REPORT_DIR = "reports"
os.makedirs(REPORT_DIR, exist_ok=True)
