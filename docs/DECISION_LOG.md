# Decision Log

## Key Assumptions

1. **Board schema.** No real CSVs were available at build time, so I assumed a realistic
   schema for each board based on the problem statement ("work orders / project execution"
   and "deals / sales pipeline") and built:
   - **Deals**: Client, Sector, Deal Value, Stage, Probability, Expected Close Date, Owner,
     Created Date.
   - **Work Orders**: Client, Sector, Budget, Status, % Complete, Start Date, Due Date,
     Assigned To.
   Rather than hardcode this schema rigidly, `config.py` maps *logical* fields to a list of
   acceptable column-title synonyms (e.g. "value" matches "Deal Value", "Amount", "Deal
   Size"...), so the agent degrades gracefully if the real boards use slightly different
   naming, and the mapping is a one-file edit if the real headers differ more than that.
   I generated sample CSVs (`sample_data/`) with the same kinds of messiness described in the
   brief (mixed date formats, inconsistent sector casing/naming, currency symbols, blanks,
   "TBD"/"-" placeholders) so the cleaning logic is demonstrably tested against realistic
   noise, not just my own clean data.

2. **"Quarter" boundaries.** Deals are quartered by Expected Close Date; Work Orders by Due
   Date. "This quarter" with no year specified defaults to the current calendar quarter
   (system prompt tells the LLM this rather than making it ask every time — a founder asking
   "this quarter" almost never means anything else).

3. **Sector normalization is a fixed canonical map**, not fuzzy ML matching. "Energy",
   "energy ", "ENERGY", "Energy Sector", "Oil & Gas", "O&G" all collapse to `Energy`. This is
   deliberately simple and inspectable — a founder can see exactly what maps to what in
   `config.SECTOR_CANONICAL_MAP` — rather than a black-box embedding similarity that could
   silently misclassify a sector during a board meeting.

4. **Numbers come from pandas, not the LLM.** Every dollar figure, count, or percentage
   the agent states is produced by a deterministic function in `analytics.py` and handed to
   the LLM as JSON to narrate — the LLM's job is intent-parsing and prose, never arithmetic.
   This was the single highest-priority design decision: a founder-facing BI tool that
   occasionally hallucinates a revenue number is worse than useless.

## Trade-offs

- **Function-calling over a general text-to-SQL/pandas-code-gen approach.** I gave the LLM a
  small, fixed set of analytics tools (pipeline summary, work order summary, combined sector
  view) rather than letting it generate arbitrary pandas/SQL. This trades some query
  flexibility (truly novel cross-cuts the tools don't support will get an approximate answer
  or "I can't do that yet") for reliability and auditability within a 6-hour build. With more
  time, I'd add a few more tools (rep/owner performance, time-series trend, top-N clients) and
  a "custom breakdown" tool that takes a groupby dimension + metric as structured args — still
  deterministic, just more parameterized.

- **Streamlit over a custom React/Node front end.** Streamlit gets a working, presentable
  conversational UI with a data-quality dashboard and a one-click leadership-update tab built
  and deployable in a fraction of the time a bespoke frontend would take, at the cost of UI
  polish/control. Given the "testable without local setup" and 6-hour constraints, this was
  the right trade.

- **Session-only credentials, no backend datastore.** The agent re-pulls fresh data from
  monday.com every time you hit "Connect / Refresh Data" rather than caching in a database.
  Simpler and always current; the trade-off is a small delay on each refresh for large boards,
  and if the site restarts (e.g. Streamlit Cloud) you're not logged out from anywhere but
  data does need re-fetching. Fine for founder Q&A cadence, not fine for near-real-time
  dashboards at scale.

- **Rule-based cleaning over LLM-based cleaning.** Dates/currency/percent/sector parsing use
  regex + `dateutil` + a canonical map, not an LLM call per cell. Faster, free, deterministic,
  and testable — I'd only reach for LLM-assisted cleaning if the canonical sector list grew
  large and unpredictable enough that manual mapping became unmanageable.

## What I'd do differently with more time

- Add a small eval set of ~20 founder-style questions with expected tool calls / expected
  numeric answers, and CI-check the agent against it, since correctness on business numbers is
  the whole point.
- Expand the tool set: time-series pipeline trend (is pipeline growing quarter over quarter?),
  rep/owner leaderboards, client concentration risk, and a genuinely open-ended "custom
  groupby" tool for cross-cuts I didn't anticipate.
- Real fuzzy/embedding-based sector matching as a fallback when a value doesn't match the
  canonical map or synonym list, with the result flagged as "assumed" so a founder can catch a
  misclassification.
- Persist chat history and pulled snapshots per-user (e.g. lightweight SQLite) so a founder
  can come back and see "what did the pipeline look like when I asked in March."
- Add lightweight auth in front of the Streamlit app before sharing the hosted link broadly,
  since as built anyone with the link and no credentials sees only the empty-state screen, but
  anyone with the link *and* valid tokens can query the connected boards.

## How I interpreted "leadership updates"

The brief left this open ("How you interpret and implement this is up to you"). I read it as:
founders/executives need a **fast, structured, trustworthy snapshot** they can paste into a
board update, investor email, or Slack digest without doing the pulling/cleaning/aggregating
themselves — the same pain point described in the problem statement, just packaged as a
standing artifact instead of a one-off chat answer.

Implementation: a dedicated "Leadership Update" tab that, on click, runs the *same*
deterministic `analytics.py` aggregations used by chat (company-wide pipeline health,
company-wide delivery status, and a per-sector combined breakdown), and asks the LLM to
narrate all of it in one pass into a fixed five-section markdown brief: **Headline → Pipeline
Health → Delivery Status → Sector Breakdown → Data Quality & Risks**. The last section is
deliberate: a leadership update that hides its own data gaps would be actively misleading, so
every update explicitly surfaces how many records were missing key fields before the founder
trusts the numbers in a real decision. It's downloadable as markdown so it can be dropped
straight into whatever the team already uses for updates (Notion, email, deck).
