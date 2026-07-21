# Founder BI Agent — monday.com Pipeline & Work Order Intelligence

A conversational agent that answers founder-level business questions ("How's pipeline
looking for energy this quarter?") by querying monday.com boards **live** (Deals +
Work Orders), cleaning the inevitable messy data, and giving a grounded, narrated answer —
plus a one-click leadership update.

## Architecture

```
┌─────────────────┐      ┌───────────────────┐      ┌────────────────────┐
│  Streamlit UI    │─────▶│  monday_client.py  │─────▶│  monday.com GraphQL │
│ (chat + update    │      │  (read-only,        │      │  API v2 (live)       │
│  tab)             │      │  paginated)         │      └────────────────────┘
└────────┬─────────┘      └───────────────────┘
         │
         ▼
┌───────────────────┐     ┌──────────────────┐
│ data_cleaning.py    │────▶│  analytics.py      │  <- all numbers computed here
│ (dates, currency,    │     │  (pandas, deterministic
│  sectors, nulls)     │     │  aggregation)       │
└───────────────────┘     └────────┬─────────┘
                                      │
                                      ▼
                            ┌──────────────────┐
                            │  llm_agent.py       │  <- OpenAI function-calling
                            │  picks a tool,       │     picks WHICH analytics
                            │  narrates result     │     fn to call; narrates
                            └──────────────────┘     the JSON result in prose
```

**Key design principle:** the LLM never invents business numbers. It parses the founder's
question into a call to a deterministic `analytics.py` function (pandas aggregation over
cleaned data), receives the JSON result, and writes a plain-English narrative around it. This
keeps the "insight" conversational while keeping the "numbers" trustworthy and auditable
(every chat answer has an "Underlying data" JSON expander in the UI).

## Files

```
app/
  config.py            # env/secrets, board column-name mapping, sector canonicalization
  monday_client.py      # read-only GraphQL client (auth, pagination, retries)
  data_cleaning.py       # messy-data normalization -> clean pandas DataFrames + quality report
  analytics.py           # deterministic BI aggregations (pipeline, work orders, combined)
  llm_agent.py            # OpenAI function-calling agent: intent -> tool -> narration
  leadership_update.py     # one-click founder/board summary generator
  streamlit_app.py          # chat UI + leadership update tab
sample_data/
  deals_sample.csv           # example messy Deals export (for board setup)
  work_orders_sample.csv      # example messy Work Orders export (for board setup)
docs/
  DECISION_LOG.md               # assumptions, trade-offs, what's next
```

## Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Set up your monday.com boards

You need two boards: **Deals** and **Work Orders**.

1. In monday.com, create a new board (or use **Add board > Import from CSV**) and import
   `sample_data/deals_sample.csv` (or your real deal data). Name it e.g. "Deals".
2. Repeat with `sample_data/work_orders_sample.csv` for a board named e.g. "Work Orders".
3. After import, monday.com auto-detects column types from the CSV headers. Quickly check /
   adjust so that:
   - **Deals board** has columns whose *titles* (any of these synonyms are fine — see
     `config.DEALS_COLUMN_MAP`) roughly match: `Client`, `Sector`/`Industry`, `Deal Value`,
     `Stage`, `Probability`, `Expected Close Date`, `Owner`, `Created Date`.
   - **Work Orders board** has: `Client`, `Sector`/`Industry`, `Budget`/`Value`, `Status`,
     `% Complete`, `Start Date`, `Due Date`, `Assigned To`.
   - Exact column *types* (Status vs Text, Date vs Text) don't matter much — the agent reads
     the rendered `text` value of every column and parses it defensively either way. But using
     monday.com's native Status/Date/Number column types will make the underlying data cleaner
     to begin with.
4. Get each board's ID: open the board in monday.com, the ID is the numeric segment in the
   URL, e.g. `https://yourteam.monday.com/boards/1234567890` → `1234567890`.
5. Generate an API token: **Avatar (bottom left) → Admin → API**, or **Profile → Developers →
   My Access Tokens**. Copy the token — this agent only needs **read** access.

### 3. Configure credentials

Copy `.env.example` to `.env` and fill in:

```
MONDAY_API_TOKEN=...
MONDAY_DEALS_BOARD_ID=...
MONDAY_WORK_ORDERS_BOARD_ID=...
OPENAI_API_KEY=...
```

Or, if deploying to Streamlit Community Cloud, put the same keys in **App settings →
Secrets** (TOML format, same key names).

You can also skip the `.env` file entirely and paste the token/keys directly into the
sidebar fields at runtime — nothing is persisted server-side beyond the current session.

### 4. Run

```bash
streamlit run app/streamlit_app.py
```

Open the local URL, confirm/enter your credentials in the sidebar, click **Connect / Refresh
Data**, and start asking questions.

### 5. Deploy (for the hosted link deliverable)

Easiest path: push this repo to GitHub, then on
[share.streamlit.io](https://share.streamlit.io), "New app" → point at
`app/streamlit_app.py` → add the four secrets above → Deploy. Takes about two minutes.

## Example questions to try

- "How's our pipeline looking for the energy sector this quarter?"
- "What work orders are overdue?"
- "Give me the combined view for healthcare — pipeline and delivery."
- "Which sector has the most stalled deals?"
- "What's our weighted pipeline value company-wide?"

## Notes on read-only scope

Per the integration requirements, this agent **only reads** from monday.com — no mutations,
no writes, no item creation. `monday_client.py` has no mutation queries implemented at all,
by design, so there's no accidental-write risk.
