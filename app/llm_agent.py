"""
The conversational "brain" of the agent.

Design: the LLM does NOT compute business numbers itself (that's
analytics.py's job, deterministically, via pandas). Instead the LLM:
  1. Reads the founder's question + conversation history
  2. Picks one of a small set of analytics tools to call, with parameters
     (sector, quarter, stage, status), OR asks a clarifying question if the
     query is genuinely ambiguous (e.g. unknown sector, no time frame and
     it matters)
  3. Is given the tool's JSON result and asked to write a founder-friendly
     narrative answer, including any data-quality caveats returned by the
     tool.

This keeps numbers trustworthy while keeping the interface conversational.
"""
from __future__ import annotations

import json

from openai import OpenAI

from . import analytics, config

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "pipeline_summary",
            "description": "Sales pipeline / deals analysis: open pipeline value, weighted value, won/lost deals, breakdowns by stage and sector. Use for revenue, pipeline, deals, sales questions.",
            "parameters": {
                "type": "object",
                "properties": {
                    "sector": {"type": "string", "description": "Filter to one sector, e.g. Energy, Retail, Healthcare, Finance, Manufacturing. Omit for all sectors."},
                    "stage": {"type": "string", "description": "Filter to one deal stage, e.g. Lead, Qualified, Proposal, Negotiation, Closed Won, Closed Lost. Omit for all stages."},
                    "year": {"type": "integer", "description": "Calendar year for a quarter filter, e.g. 2026."},
                    "quarter": {"type": "integer", "description": "Quarter number 1-4, based on expected close date."},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "work_order_summary",
            "description": "Project execution / delivery analysis: work order counts, value, status breakdown, overdue in-progress orders. Use for operations, delivery, execution, project status questions.",
            "parameters": {
                "type": "object",
                "properties": {
                    "sector": {"type": "string", "description": "Filter to one sector. Omit for all sectors."},
                    "status": {"type": "string", "description": "Filter to one status, e.g. Not Started, In Progress, Completed, On Hold, Cancelled."},
                    "year": {"type": "integer"},
                    "quarter": {"type": "integer", "description": "Quarter number 1-4, based on due date."},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "combined_sector_view",
            "description": "Cross-board view combining sales pipeline AND delivery/execution for one sector or overall. Use when the question spans both sales and operations, e.g. 'how is the energy sector doing overall'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "sector": {"type": "string", "description": "Sector to analyze. Omit for a company-wide combined view."},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "ask_clarifying_question",
            "description": "Use ONLY when the question is genuinely ambiguous and guessing would risk a misleading answer (e.g. an unrecognized sector name, or a time frame that materially changes the answer and isn't inferable). Do not use this for things you can reasonably default (e.g. 'this quarter' defaults to the current calendar quarter).",
            "parameters": {
                "type": "object",
                "properties": {
                    "question": {"type": "string", "description": "The clarifying question to ask the founder."},
                },
                "required": ["question"],
            },
        },
    },
]

SYSTEM_PROMPT = """You are a founder-facing business intelligence assistant for a company \
that tracks its sales pipeline (Deals board) and project delivery (Work Orders board) in \
monday.com. You answer conversationally, like a sharp chief-of-staff who knows the numbers \
cold, not like a database.

Rules:
- Always ground numeric claims in the tool result you receive. Never invent numbers.
- Available sectors will be provided in context; if the founder names something close but not \
exact (e.g. "energy sector" vs "Energy"), just map it yourself, don't ask.
- If the tool result shows meaningful data-quality gaps (e.g. many deals missing values or \
close dates), mention it briefly as a caveat, so the founder knows to sanity check.
- If asked something outside pipeline/work orders (the two boards), say so plainly.
- Default ambiguous time frames like "this quarter" to the current calendar quarter rather \
than asking - only ask a clarifying question for things you genuinely can't reasonably guess.
- Be concise: lead with the headline number/insight, then 2-4 supporting bullets, not a wall \
of text. Sound like a person, not a report generator.
"""


class BIAgent:
    def __init__(self, deals_df, wo_df, deals_quality, wo_quality):
        # Configure client for xAI / Grok endpoint
        self.client = OpenAI(
            api_key=getattr(config, "XAI_API_KEY", getattr(config, "OPENAI_API_KEY", None)),
            base_url="https://api.xai.com/v1",
        )
        self.deals_df = deals_df
        self.wo_df = wo_df
        self.deals_quality = deals_quality
        self.wo_quality = wo_quality
        self.sectors = analytics.list_sectors(deals_df, wo_df)

    def _current_quarter_context(self) -> str:
        import pandas as pd
        today = pd.Timestamp.today()
        q = (today.month - 1) // 3 + 1
        return f"Today is {today.date().isoformat()} (Q{q} {today.year})."

    def _call_tool(self, name: str, args: dict) -> dict:
        if name == "pipeline_summary":
            return analytics.pipeline_summary(self.deals_df, **args)
        if name == "work_order_summary":
            return analytics.work_order_summary(self.wo_df, **args)
        if name == "combined_sector_view":
            return analytics.combined_sector_view(self.deals_df, self.wo_df, **args)
        raise ValueError(f"Unknown tool: {name}")

    def answer(self, conversation_history: list[dict]) -> dict:
        """
        conversation_history: list of {"role": "user"/"assistant", "content": str}
        Returns: {"type": "answer"|"clarify", "text": str, "tool_used": str|None, "tool_result": dict|None}
        """
        context_note = (
            f"{self._current_quarter_context()} "
            f"Known sectors in the data: {', '.join(self.sectors) if self.sectors else 'none detected'}. "
            f"Deals board has {self.deals_quality.get('total_rows', 0)} rows; "
            f"Work Orders board has {self.wo_quality.get('total_rows', 0)} rows."
        )

        messages = (
            [{"role": "system", "content": SYSTEM_PROMPT + "\n\n" + context_note}]
            + conversation_history
        )

        # Fallback to 'grok-2-latest' if config model is not updated
        model_name = getattr(config, "GROK_MODEL", getattr(config, "OPENAI_MODEL", "grok-2-latest"))

        first = self.client.chat.completions.create(
            model=model_name,
            messages=messages,
            tools=TOOLS,
            tool_choice="auto",
        )
        msg = first.choices[0].message

        if not msg.tool_calls:
            # LLM answered directly (e.g. off-topic question, or generic chat)
            return {"type": "answer", "text": msg.content, "tool_used": None, "tool_result": None}

        tool_call = msg.tool_calls[0]
        fn_name = tool_call.function.name
        try:
            fn_args = json.loads(tool_call.function.arguments or "{}")
        except json.JSONDecodeError:
            fn_args = {}

        if fn_name == "ask_clarifying_question":
            return {
                "type": "clarify",
                "text": fn_args.get("question", "Could you clarify what you're looking for?"),
                "tool_used": None,
                "tool_result": None,
            }

        try:
            result = self._call_tool(fn_name, fn_args)
        except Exception as e:
            return {
                "type": "answer",
                "text": f"I hit an error pulling that data ({e}). Try rephrasing, or check the board is accessible.",
                "tool_used": fn_name,
                "tool_result": None,
            }

        # Second pass: give the model the tool result to narrate
        messages.append({
            "role": "assistant",
            "content": None,
            "tool_calls": [{
                "id": tool_call.id,
                "type": "function",
                "function": {"name": fn_name, "arguments": tool_call.function.arguments},
            }],
        })
        messages.append({
            "role": "tool",
            "tool_call_id": tool_call.id,
            "content": json.dumps(result, default=str),
        })

        second = self.client.chat.completions.create(
            model=model_name,
            messages=messages,
        )
        narrative = second.choices[0].message.content

        return {"type": "answer", "text": narrative, "tool_used": fn_name, "tool_result": result}