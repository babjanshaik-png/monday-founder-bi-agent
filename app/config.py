import os
from dotenv import load_dotenv

# Load .env file
load_dotenv()

# We are using .env, not Streamlit secrets
_SECRETS = {}


def _get(name: str, default: str = "") -> str:
    """Read values from .env"""
    return os.environ.get(name, default)


MONDAY_API_TOKEN = _get("MONDAY_API_TOKEN")
MONDAY_API_URL = "https://api.monday.com/v2"
Grok_API_KEY = _get("Grok_API_KEY")
Grok_MODE = _get("Grok_MODE", "grok-4")

# Alias DEALS_BOARD_ID to check both MONDAY_DEALS_BOARD_ID and DEALS_BOARD_ID in .env
DEALS_BOARD_ID = _get("MONDAY_DEALS_BOARD_ID") or _get("DEALS_BOARD_ID")

# Define WO_BOARD_ID (and keep WORK_ORDERS_BOARD_ID as an alias so nothing breaks)
WO_BOARD_ID = _get("MONDAY_WORK_ORDERS_BOARD_ID") or _get("WO_BOARD_ID")
WORK_ORDERS_BOARD_ID = WO_BOARD_ID
# ---------------------------------------------------------------------------
# Column mapping: logical field name -> list of acceptable monday.com column
# titles (case-insensitive, whitespace-trimmed). The first match wins.
# This lets the agent tolerate small naming differences between whoever set
# up the board and what we expect, without hardcoding column IDs.
# ---------------------------------------------------------------------------
DEALS_COLUMN_MAP = {
    "client": ["client", "company", "account", "customer"],
    "sector": ["sector", "industry", "vertical"],
    "value": ["deal value", "value", "amount", "deal size", "contract value"],
    "stage": ["stage", "deal stage", "status", "pipeline stage"],
    "probability": ["probability", "win probability", "close probability", "%"],
    "expected_close_date": ["expected close date", "close date", "expected close"],
    "owner": ["owner", "sales rep", "assigned to", "rep"],
    "created_date": ["created date", "date created", "created"],
}

WORK_ORDERS_COLUMN_MAP = {
    "client": ["client", "company", "account", "customer"],
    "sector": ["sector", "industry", "vertical"],
    "value": ["budget", "value", "contract value", "work order value"],
    "status": ["status", "work order status"],
    "pct_complete": ["% complete", "percent complete", "completion", "progress"],
    "start_date": ["start date", "kickoff date"],
    "due_date": ["due date", "completion date", "target date", "end date"],
    "assigned_to": ["assigned to", "owner", "lead", "project lead"],
}

# Canonical sector names -> list of messy variants seen in real exports.
# Used to normalize free-text sector/industry values.
SECTOR_CANONICAL_MAP = {
    "Energy": ["energy", "energy sector", "oil & gas", "oil and gas", "o&g", "renewables", "power"],
    "Retail": ["retail", "retail sector", "ecommerce", "e-commerce"],
    "Healthcare": ["healthcare", "health", "medical", "health sector"],
    "Finance": ["finance", "financial", "banking", "fintech", "financial services"],
    "Manufacturing": ["manufacturing", "industrial", "mfg"],
}

# Canonical deal-stage buckets for pipeline health reporting.
OPEN_STAGES = ["lead", "qualified", "proposal", "negotiation"]
WON_STAGES = ["closed won", "won"]
LOST_STAGES = ["closed lost", "lost"]
