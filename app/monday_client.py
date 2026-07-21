"""
Thin, read-only client for the monday.com GraphQL v2 API.

Deliberately minimal: this agent only ever needs to READ items + column
values from boards. No mutations are implemented, by design (see Decision
Log: "Integration Requirements -> Read only").
"""
from __future__ import annotations

import time
from typing import Any

import requests

from . import config


class MondayAPIError(Exception):
    """Raised when the monday.com API returns an error or is unreachable."""


class MondayClient:
    def __init__(self, api_token: str | None = None, api_url: str | None = None):
        self.api_token = api_token or config.MONDAY_API_TOKEN
        self.api_url = api_url or config.MONDAY_API_URL
        if not self.api_token:
            raise MondayAPIError(
                "No monday.com API token configured. Set MONDAY_API_TOKEN in "
                "your environment or Streamlit secrets."
            )

    def _headers(self) -> dict:
        return {
            "Authorization": self.api_token,
            "Content-Type": "application/json",
            "API-Version": "2024-10",
        }

    def _execute(self, query: str, variables: dict | None = None, retries: int = 3) -> dict:
        payload = {"query": query, "variables": variables or {}}
        last_err = None
        for attempt in range(retries):
            try:
                resp = requests.post(
                    self.api_url, json=payload, headers=self._headers(), timeout=30
                )
            except requests.RequestException as e:
                last_err = e
                time.sleep(1.5 * (attempt + 1))
                continue

            if resp.status_code == 429:
                # Rate limited - back off and retry
                time.sleep(2.0 * (attempt + 1))
                continue

            if resp.status_code >= 500:
                last_err = MondayAPIError(f"monday.com server error {resp.status_code}")
                time.sleep(1.5 * (attempt + 1))
                continue

            try:
                data = resp.json()
            except ValueError:
                raise MondayAPIError(f"Non-JSON response from monday.com: {resp.text[:300]}")

            if "errors" in data:
                raise MondayAPIError(f"monday.com API error: {data['errors']}")

            return data

        raise MondayAPIError(f"monday.com API unreachable after {retries} attempts: {last_err}")

    def test_connection(self) -> dict:
        """Simple sanity check - returns the authenticated user's name/account."""
        query = "query { me { name email account { name } } }"
        data = self._execute(query)
        return data.get("data", {}).get("me", {})

    def get_board_name(self, board_id: str) -> str | None:
        query = """
        query ($boardId: [ID!]) {
          boards(ids: $boardId) { name }
        }
        """
        data = self._execute(query, {"boardId": [board_id]})
        boards = data.get("data", {}).get("boards", [])
        return boards[0]["name"] if boards else None

    def get_all_items(self, board_id: str) -> list[dict[str, Any]]:
        """
        Fetch every item on a board, with column values, handling pagination
        via monday.com's cursor-based items_page.

        Returns a list of dicts like:
          {"id": ..., "name": ..., "columns": {"Column Title": "text value", ...}}
        """
        items: list[dict[str, Any]] = []
        cursor = None

        first_query = """
        query ($boardId: [ID!], $limit: Int!) {
          boards(ids: $boardId) {
            items_page(limit: $limit) {
              cursor
              items {
                id
                name
                column_values { id text value column { title } }
              }
            }
          }
        }
        """
        next_query = """
        query ($cursor: String!, $limit: Int!) {
          next_items_page(cursor: $cursor, limit: $limit) {
            cursor
            items {
              id
              name
              column_values { id text value column { title } }
            }
          }
        }
        """

        data = self._execute(first_query, {"boardId": [board_id], "limit": 100})
        boards = data.get("data", {}).get("boards", [])
        if not boards:
            raise MondayAPIError(
                f"Board {board_id} not found or not accessible with this API token."
            )
        page = boards[0]["items_page"]
        items.extend(page["items"])
        cursor = page["cursor"]

        while cursor:
            data = self._execute(next_query, {"cursor": cursor, "limit": 100})
            page = data.get("data", {}).get("next_items_page")
            if not page:
                break
            items.extend(page["items"])
            cursor = page["cursor"]

        # Flatten column_values into a simple {title: text} dict per item for
        # easier downstream cleaning.
        flattened = []
        for it in items:
            cols = {cv["column"]["title"]: cv["text"] for cv in it["column_values"]}
            flattened.append({"id": it["id"], "name": it["name"], "columns": cols})
        return flattened
