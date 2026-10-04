"""Regression tests for strict, multi-color catalogue search."""

from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

from backend.agent import NO_MATCH_REPLY, _validated_reply
from backend.tools import search_catalogue


def _color_test_database(path: Path) -> None:
    connection = sqlite3.connect(path)
    try:
        connection.executescript(
            """
            CREATE TABLE catalogue (
                product_id TEXT PRIMARY KEY, name TEXT, garment_type TEXT,
                description TEXT, colors TEXT, search_tags TEXT,
                image_file_path TEXT, price REAL
            );
            CREATE TABLE inventory (
                id INTEGER PRIMARY KEY, product_id TEXT, size TEXT, quantity INTEGER
            );
            INSERT INTO catalogue VALUES
                ('cream-item', 'Cream Pullover', 'pullover hoodie', 'Campus apparel',
                    '["cream"]', '["hoodie"]', 'cream.png', 58.0),
                ('white-item', 'White Tee', 't-shirt', 'Campus apparel',
                    '["white"]', '["tee"]', 'white.png', 28.0),
                ('navy-item', 'Navy Hoodie', 'pullover hoodie', 'Campus apparel',
                    '["navy", "white"]', '["hoodie"]', 'navy.png', 58.0);
            """
        )
        connection.commit()
    finally:
        connection.close()


class SearchColorTests(unittest.TestCase):
    def test_multiple_requested_colors_match_any_main_color(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            database_path = folder / "shop.db"
            _color_test_database(database_path)

            results = search_catalogue(
                "apparel",
                database_path,
                folder,
                category_context="Do you have white, cream, or ivory apparel?",
            )

            self.assertEqual(
                {product.product_id for product in results},
                {"cream-item", "white-item"},
            )

    def test_broad_color_search_still_uses_main_color_only(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            database_path = folder / "shop.db"
            _color_test_database(database_path)

            results = search_catalogue(
                "apparel",
                database_path,
                folder,
                category_context="Show me white apparel",
            )

            self.assertEqual(
                {product.product_id for product in results}, {"white-item"}
            )

    def test_empty_search_cannot_be_described_as_a_successful_find(self) -> None:
        self.assertEqual(
            _validated_reply(
                "I found several cream options.",
                search_performed=True,
                has_products=False,
            ),
            NO_MATCH_REPLY,
        )
        self.assertEqual(
            _validated_reply(
                "Hello!", search_performed=False, has_products=False
            ),
            "Hello!",
        )


if __name__ == "__main__":
    unittest.main()
