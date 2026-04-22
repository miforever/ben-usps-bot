import logging
import sqlite3
from pathlib import Path
from typing import Any, Dict, List

from src.config import get_settings

logger = logging.getLogger(__name__)

_CLEANUP_SQL = """
    DELETE FROM seen_orders
    WHERE order_id IN (
        SELECT order_id FROM seen_orders
        ORDER BY timestamp DESC
        LIMIT -1 OFFSET ?
    )
"""


class OrderManager:
    """SQLite-backed deduplication store for seen order IDs."""

    def __init__(self):
        settings = get_settings()
        self.db_path = settings.DB_PATH
        self.max_orders = settings.MAX_LOADS
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS seen_orders (
                    order_id TEXT PRIMARY KEY,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

    def _cleanup_old_orders(self, cursor: sqlite3.Cursor):
        cursor.execute(_CLEANUP_SQL, (self.max_orders,))

    def is_seen(self, order_id: str) -> bool:
        with self._connect() as conn:
            cursor = conn.execute("SELECT 1 FROM seen_orders WHERE order_id = ?", (order_id,))
            return cursor.fetchone() is not None

    def mark_seen(self, order_id: str):
        try:
            with self._connect() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT OR REPLACE INTO seen_orders (order_id) VALUES (?)",
                    (order_id,),
                )
                self._cleanup_old_orders(cursor)
        except Exception as e:
            logger.error(f"Error marking order {order_id} as seen: {e}")

    def process_new_entries(self, entries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filter out already-seen entries and record the new ones atomically."""
        unseen: List[Dict[str, Any]] = []

        with self._connect() as conn:
            cursor = conn.cursor()

            # Oldest first so queue order matches scrape order
            for entry in reversed(entries):
                order_id = entry.get("order_id")
                if not order_id:
                    continue
                try:
                    cursor.execute("INSERT INTO seen_orders (order_id) VALUES (?)", (order_id,))
                    unseen.append(entry)
                except sqlite3.IntegrityError:
                    continue

            if unseen:
                self._cleanup_old_orders(cursor)

        return unseen

    def clear_all_orders(self):
        try:
            with self._connect() as conn:
                conn.execute("DELETE FROM seen_orders")
            logger.info("Successfully cleared all seen orders")
        except Exception as e:
            logger.error(f"Error clearing seen orders: {e}")
