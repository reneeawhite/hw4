"""Offline checks for the append-only, privacy-minimized agent audit trail."""

from __future__ import annotations

import asyncio
import json
import sqlite3
import stat
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from pydantic_ai import Agent
from pydantic_ai.messages import ModelResponse, ToolCallPart, ToolReturnPart
from pydantic_ai.models.function import FunctionModel

from backend import agent
from backend.models import AgentChatReply, AgentDependencies, InventoryItem, StockResult
from backend.tools import price


def _test_database(path: Path) -> None:
    connection = sqlite3.connect(path)
    try:
        connection.executescript(
            """
            CREATE TABLE catalogue (
                product_id TEXT PRIMARY KEY, name TEXT, garment_type TEXT,
                description TEXT, colors TEXT, search_tags TEXT,
                image_file_path TEXT, price REAL
            );
            CREATE TABLE inventory (id INTEGER PRIMARY KEY, product_id TEXT, size TEXT, quantity INTEGER);
            INSERT INTO catalogue VALUES (
                'test-hoodie', 'Test Hoodie', 'pullover hoodie', 'A test item',
                '["navy"]', '["hoodie"]', 'test.png', 58.0
            );
            INSERT INTO inventory VALUES (1, 'test-hoodie', 'M', 3);
            """
        )
        connection.commit()
    finally:
        connection.close()


def _offline_model(messages, info):
    if any(
        isinstance(part, ToolReturnPart)
        for message in messages
        for part in message.parts
    ):
        return ModelResponse(
            parts=[ToolCallPart(info.output_tools[0].name, {"reply": "The price is $58.", "product_ids": []})],
            finish_reason="tool_call",
        )
    return ModelResponse(
        parts=[ToolCallPart("price", {"product_id": "test-hoodie"})],
        finish_reason="tool_call",
    )


class AuditTrailTests(unittest.TestCase):
    def test_tool_events_append_across_runs_without_private_text(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            database_path = folder / "shop.db"
            audit_path = folder / "audit_trail.json"
            _test_database(database_path)
            fake_agent = Agent(
                FunctionModel(_offline_model),
                output_type=AgentChatReply,
                deps_type=AgentDependencies,
                tools=[price],
            )
            with patch.object(agent, "get_agent", return_value=fake_agent), patch.object(
                agent, "AUDIT_TRAIL_PATH", audit_path
            ):
                for _ in range(2):
                    response = asyncio.run(
                        agent.run_chat(
                            "What is the price? My email is private@example.com and password is secret123",
                            [],
                            database_path,
                        )
                    )
                    self.assertIn("$58", response.reply)

            raw = audit_path.read_text(encoding="utf-8")
            self.assertEqual(stat.S_IMODE(audit_path.stat().st_mode), 0o600)
            records = [json.loads(line) for line in raw.splitlines()]
            self.assertEqual(len(records), 4)
            self.assertEqual([record["event"] for record in records], [
                "tool_call", "run_end", "tool_call", "run_end"
            ])
            self.assertEqual(records[0]["tool_name"], "price")
            self.assertEqual(records[0]["result_summary"]["price"], 58.0)
            self.assertIsNone(records[0]["stop_reason"])
            self.assertIn("time", records[0])
            self.assertEqual(records[1]["stop_reason"], "completed")
            self.assertNotEqual(records[0]["request_id"], records[2]["request_id"])
            self.assertNotIn("private@example.com", raw)
            self.assertNotIn("secret123", raw)

    def test_configuration_failure_has_stop_record(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            with patch.object(agent, "AUDIT_TRAIL_PATH", folder / "audit_trail.json"), patch.object(
                agent, "get_agent", side_effect=agent.AgentConfigurationError("key missing")
            ):
                with self.assertRaises(agent.AgentConfigurationError):
                    asyncio.run(agent.run_chat("hello", [], folder / "missing.db"))
            records = [json.loads(line) for line in (folder / "audit_trail.json").read_text().splitlines()]
            self.assertEqual(len(records), 1)
            self.assertEqual(records[0]["stop_reason"], "configuration_error")

    def test_free_text_audit_args_are_redacted(self) -> None:
        call = ToolCallPart(
            "search_products",
            {"query": "hoodies password secret123 private@example.com", "limit": 5},
        )
        summary = agent._audit_args("search_products", call, {"test-hoodie"})
        self.assertEqual(summary, {"query_terms": ["hoodies"], "limit": 5})
        unknown_id = ToolCallPart("stock", {"product_id": "secret123", "size": "M"})
        self.assertEqual(
            agent._audit_args("stock", unknown_id, {"test-hoodie"})["product_id"],
            "[unverified]",
        )
        secret_size = ToolCallPart("stock", {"product_id": "test-hoodie", "size": "secret12"})
        self.assertEqual(
            agent._audit_args("stock", secret_size, {"test-hoodie"})["size"],
            "[redacted]",
        )

    def test_stock_result_is_short_and_structured(self) -> None:
        result = StockResult(
            product_id="test-hoodie",
            name="Test Hoodie",
            total_stock=3,
            inventory_by_size=[InventoryItem(size="M", quantity=3)],
        )
        summary = agent._audit_result(ToolReturnPart("stock", result), {"test-hoodie"})
        self.assertEqual(summary["total_stock"], 3)
        self.assertEqual(summary["inventory_by_size"], [{"size": "M", "quantity": 3}])
        self.assertNotIn("Test Hoodie", json.dumps(summary))


if __name__ == "__main__":
    unittest.main()
