from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

DEFAULT_DB_PATH = Path("data/qhome_agent.db")


def get_connection(db_path: Path = DEFAULT_DB_PATH) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: Path = DEFAULT_DB_PATH) -> None:
    conn = get_connection(db_path)
    cursor = conn.cursor()

    # 1. products
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sku TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        category TEXT NOT NULL,
        unit TEXT NOT NULL,
        price INTEGER NOT NULL,
        coverage_m2 REAL,
        coverage_per_liter REAL,
        use_case TEXT,
        risk_note TEXT,
        is_active INTEGER DEFAULT 1
    )
    """)

    # 2. inventory_snapshots
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS inventory_snapshots (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sku TEXT NOT NULL,
        branch_name TEXT NOT NULL,
        stock_qty INTEGER NOT NULL,
        stock_status TEXT NOT NULL,
        last_updated TEXT NOT NULL
    )
    """)

    # 3. tickets
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS tickets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ticket_code TEXT UNIQUE NOT NULL,
        session_id TEXT NOT NULL,
        customer_name TEXT,
        customer_whatsapp TEXT,
        status TEXT NOT NULL,
        priority TEXT,
        category TEXT,
        summary TEXT,
        missing_info TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """)

    # 4. messages
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ticket_code TEXT NOT NULL,
        role TEXT NOT NULL,
        content TEXT NOT NULL,
        created_at TEXT NOT NULL
    )
    """)

    # 5. quotes
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS quotes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        quote_code TEXT UNIQUE NOT NULL,
        ticket_code TEXT NOT NULL,
        estimated_total INTEGER NOT NULL,
        budget INTEGER,
        budget_status TEXT,
        risk_level TEXT,
        notes TEXT,
        created_at TEXT NOT NULL
    )
    """)

    # 6. quote_items
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS quote_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        quote_code TEXT NOT NULL,
        sku TEXT NOT NULL,
        name TEXT NOT NULL,
        qty INTEGER NOT NULL,
        unit TEXT NOT NULL,
        unit_price INTEGER NOT NULL,
        subtotal INTEGER NOT NULL
    )
    """)

    # 7. agent_runs
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS agent_runs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        run_id TEXT UNIQUE NOT NULL,
        ticket_code TEXT,
        mode TEXT NOT NULL,
        created_at TEXT NOT NULL
    )
    """)

    # 8. agent_steps
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS agent_steps (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        run_id TEXT NOT NULL,
        agent_name TEXT NOT NULL,
        input_json TEXT,
        output_json TEXT,
        created_at TEXT NOT NULL
    )
    """)

    # 9. policies
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS policies (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        policy_code TEXT UNIQUE NOT NULL,
        title TEXT NOT NULL,
        summary TEXT NOT NULL,
        risk_note TEXT
    )
    """)

    conn.commit()
    conn.close()


def seed_db(project_root: Path, db_path: Path = DEFAULT_DB_PATH) -> None:
    init_db(db_path)
    conn = get_connection(db_path)
    cursor = conn.cursor()

    # Seed products
    prod_file = project_root / "data/seed/products.json"
    if prod_file.exists():
        try:
            products = json.loads(prod_file.read_text(encoding="utf-8"))
            for p in products:
                use_case_str = json.dumps(p.get("use_case", []))
                cursor.execute(
                    """
                    INSERT OR IGNORE INTO products (
                        sku, name, category, unit, price, coverage_m2, coverage_per_liter, use_case, risk_note
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        p["sku"],
                        p["name"],
                        p["category"],
                        p["unit"],
                        p["price"],
                        p.get("coverage_m2"),
                        p.get("coverage_per_liter"),
                        use_case_str,
                        p.get("risk_note"),
                    ),
                )
        except Exception as e:
            print(f"Error seeding products: {e}")

    # Seed inventory
    inv_file = project_root / "data/seed/inventory.json"
    if inv_file.exists():
        try:
            inventory = json.loads(inv_file.read_text(encoding="utf-8"))
            for inv in inventory:
                # Check if already seeded to prevent duplication
                cursor.execute(
                    "SELECT 1 FROM inventory_snapshots WHERE sku = ? AND branch_name = ?",
                    (inv["sku"], inv["branch_name"]),
                )
                if not cursor.fetchone():
                    cursor.execute(
                        """
                        INSERT INTO inventory_snapshots (sku, branch_name, stock_qty, stock_status, last_updated)
                        VALUES (?, ?, ?, ?, ?)
                    """,
                        (
                            inv["sku"],
                            inv["branch_name"],
                            inv["stock_qty"],
                            inv["stock_status"],
                            inv["last_updated"],
                        ),
                    )
        except Exception as e:
            print(f"Error seeding inventory: {e}")

    # Seed policies
    pol_file = project_root / "data/seed/policies.json"
    if pol_file.exists():
        try:
            policies = json.loads(pol_file.read_text(encoding="utf-8"))
            for pol in policies:
                cursor.execute(
                    """
                    INSERT OR IGNORE INTO policies (policy_code, title, summary, risk_note)
                    VALUES (?, ?, ?, ?)
                """,
                    (pol["policy_code"], pol["title"], pol["summary"], pol.get("risk_note")),
                )
        except Exception as e:
            print(f"Error seeding policies: {e}")

    conn.commit()
    conn.close()


# Repositories

class ProductRepository:
    def __init__(self, db_path: Path = DEFAULT_DB_PATH) -> None:
        self.db_path = db_path

    def search_products(
        self, category: str | None = None, use_case: str | None = None, budget: int | None = None, limit: int = 10
    ) -> list[dict[str, Any]]:
        conn = get_connection(self.db_path)
        cursor = conn.cursor()
        query = "SELECT * FROM products WHERE is_active = 1"
        params: list[Any] = []

        if category:
            query += " AND category = ?"
            params.append(category)

        if budget is not None:
            query += " AND price <= ?"
            params.append(budget)

        query += " LIMIT ?"
        params.append(limit)

        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        results = []
        for r in rows:
            prod = dict(r)
            try:
                prod["use_case"] = json.loads(prod["use_case"]) if prod["use_case"] else []
            except Exception:
                prod["use_case"] = []
            
            # Additional matching filter for use_case since it's JSON array
            if use_case:
                if use_case not in prod["use_case"]:
                    continue
            results.append(prod)

        return results

    def get_product_by_sku(self, sku: str) -> dict[str, Any] | None:
        conn = get_connection(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM products WHERE sku = ?", (sku,))
        row = cursor.fetchone()
        conn.close()
        if not row:
            return None
        prod = dict(row)
        try:
            prod["use_case"] = json.loads(prod["use_case"]) if prod["use_case"] else []
        except Exception:
            prod["use_case"] = []
        return prod


class InventoryRepository:
    def __init__(self, db_path: Path = DEFAULT_DB_PATH) -> None:
        self.db_path = db_path

    def get_inventory_snapshot(self, sku: str, branch_name: str | None = None) -> dict[str, Any] | None:
        conn = get_connection(self.db_path)
        cursor = conn.cursor()
        if branch_name:
            cursor.execute("SELECT * FROM inventory_snapshots WHERE sku = ? AND branch_name = ?", (sku, branch_name))
        else:
            cursor.execute("SELECT * FROM inventory_snapshots WHERE sku = ? LIMIT 1", (sku,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None


class TicketRepository:
    def __init__(self, db_path: Path = DEFAULT_DB_PATH) -> None:
        self.db_path = db_path

    def create_ticket(
        self,
        ticket_code: str,
        session_id: str,
        customer_name: str | None = None,
        customer_whatsapp: str | None = None,
        status: str = "new",
        priority: str | None = None,
        category: str | None = None,
        summary: str | None = None,
        missing_info: str | None = None,
    ) -> dict[str, Any]:
        conn = get_connection(self.db_path)
        cursor = conn.cursor()
        now = datetime.now(UTC).isoformat()
        cursor.execute(
            """
            INSERT INTO tickets (
                ticket_code, session_id, customer_name, customer_whatsapp, status, priority, category, summary, missing_info, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                ticket_code,
                session_id,
                customer_name,
                customer_whatsapp,
                status,
                priority,
                category,
                summary,
                missing_info,
                now,
                now,
            ),
        )
        conn.commit()
        conn.close()
        return self.get_ticket(ticket_code) or {}

    def update_ticket(self, ticket_code: str, **kwargs: Any) -> dict[str, Any] | None:
        if not kwargs:
            return self.get_ticket(ticket_code)
        conn = get_connection(self.db_path)
        cursor = conn.cursor()
        now = datetime.now(UTC).isoformat()
        kwargs["updated_at"] = now

        sets = ", ".join([f"{k} = ?" for k in kwargs.keys()])
        params = list(kwargs.values())
        params.append(ticket_code)

        cursor.execute(f"UPDATE tickets SET {sets} WHERE ticket_code = ?", params)
        conn.commit()
        conn.close()
        return self.get_ticket(ticket_code)

    def get_ticket(self, ticket_code: str) -> dict[str, Any] | None:
        conn = get_connection(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM tickets WHERE ticket_code = ?", (ticket_code,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

    def get_ticket_by_session(self, session_id: str) -> dict[str, Any] | None:
        conn = get_connection(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM tickets WHERE session_id = ? ORDER BY id DESC LIMIT 1", (session_id,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

    def list_tickets(self) -> list[dict[str, Any]]:
        conn = get_connection(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM tickets ORDER BY updated_at DESC")
        rows = cursor.fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def add_message(self, ticket_code: str, role: str, content: str) -> None:
        conn = get_connection(self.db_path)
        cursor = conn.cursor()
        now = datetime.now(UTC).isoformat()
        cursor.execute(
            "INSERT INTO messages (ticket_code, role, content, created_at) VALUES (?, ?, ?, ?)",
            (ticket_code, role, content, now),
        )
        conn.commit()
        conn.close()


class QuoteRepository:
    def __init__(self, db_path: Path = DEFAULT_DB_PATH) -> None:
        self.db_path = db_path

    def create_quote(
        self,
        quote_code: str,
        ticket_code: str,
        estimated_total: int,
        budget: int | None = None,
        budget_status: str | None = None,
        risk_level: str | None = None,
        notes: str | None = None,
    ) -> dict[str, Any]:
        conn = get_connection(self.db_path)
        cursor = conn.cursor()
        now = datetime.now(UTC).isoformat()
        cursor.execute(
            """
            INSERT OR REPLACE INTO quotes (
                quote_code, ticket_code, estimated_total, budget, budget_status, risk_level, notes, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (quote_code, ticket_code, estimated_total, budget, budget_status, risk_level, notes, now),
        )
        conn.commit()
        conn.close()
        return self.get_quote_by_ticket(ticket_code) or {}

    def add_quote_item(
        self, quote_code: str, sku: str, name: str, qty: int, unit: str, unit_price: int, subtotal: int
    ) -> None:
        conn = get_connection(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO quote_items (quote_code, sku, name, qty, unit, unit_price, subtotal)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
            (quote_code, sku, name, qty, unit, unit_price, subtotal),
        )
        conn.commit()
        conn.close()

    def get_quote_by_ticket(self, ticket_code: str) -> dict[str, Any] | None:
        conn = get_connection(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM quotes WHERE ticket_code = ?", (ticket_code,))
        row = cursor.fetchone()
        if not row:
            conn.close()
            return None
        quote = dict(row)
        cursor.execute("SELECT * FROM quote_items WHERE quote_code = ?", (quote["quote_code"],))
        items = cursor.fetchall()
        conn.close()
        quote["items"] = [dict(i) for i in items]
        return quote


class AgentTraceRepository:
    def __init__(self, db_path: Path = DEFAULT_DB_PATH) -> None:
        self.db_path = db_path

    def create_run(self, run_id: str, ticket_code: str | None, mode: str) -> None:
        conn = get_connection(self.db_path)
        cursor = conn.cursor()
        now = datetime.now(UTC).isoformat()
        cursor.execute(
            "INSERT OR REPLACE INTO agent_runs (run_id, ticket_code, mode, created_at) VALUES (?, ?, ?, ?)",
            (run_id, ticket_code, mode, now),
        )
        conn.commit()
        conn.close()

    def add_step(self, run_id: str, agent_name: str, input_json: dict | None, output_json: dict | None) -> None:
        conn = get_connection(self.db_path)
        cursor = conn.cursor()
        now = datetime.now(UTC).isoformat()
        cursor.execute(
            "INSERT INTO agent_steps (run_id, agent_name, input_json, output_json, created_at) VALUES (?, ?, ?, ?, ?)",
            (run_id, agent_name, json.dumps(input_json) if input_json else None, json.dumps(output_json) if output_json else None, now),
        )
        conn.commit()
        conn.close()

    def get_steps(self, run_id: str) -> list[dict[str, Any]]:
        conn = get_connection(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM agent_steps WHERE run_id = ? ORDER BY id ASC", (run_id,))
        rows = cursor.fetchall()
        conn.close()
        steps = []
        for r in rows:
            step = dict(r)
            try:
                step["input"] = json.loads(step["input_json"]) if step["input_json"] else None
            except Exception:
                step["input"] = None
            try:
                step["output"] = json.loads(step["output_json"]) if step["output_json"] else None
            except Exception:
                step["output"] = None
            steps.append(step)
        return steps
