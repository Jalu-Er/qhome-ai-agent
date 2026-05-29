from __future__ import annotations

import unittest
from pathlib import Path

from qhome_ai_agent.storage import (
    init_db,
    seed_db,
    ProductRepository,
    InventoryRepository,
    QuoteRepository,
    TicketRepository,
)
from qhome_ai_agent.tools import (
    calculate_tile_boxes,
    calculate_paint_liters,
    calculate_total,
    determine_budget_status,
    verify_quote_risks,
)
from qhome_ai_agent.mock_llm import MockChatModel
from qhome_ai_agent.orchestrator import run_workflow


class RenovationPipelineTest(unittest.TestCase):
    def setUp(self) -> None:
        self.project_root = Path(__file__).resolve().parents[1]
        self.test_db_path = self.project_root / "data/qhome_test.db"
        if self.test_db_path.exists():
            self.test_db_path.unlink()

    def tearDown(self) -> None:
        if self.test_db_path.exists():
            self.test_db_path.unlink()

    def test_database_init_and_seeding(self) -> None:
        # 1. init_db creates database and tables
        init_db(self.test_db_path)
        self.assertTrue(self.test_db_path.exists())

        # 2. seed_db inserts products, inventory and policies without duplication
        seed_db(self.project_root, self.test_db_path)
        
        prod_repo = ProductRepository(self.test_db_path)
        products = prod_repo.search_products(limit=10)
        self.assertTrue(len(products) > 0)
        
        # 3. search_products returns matching products from SQLite
        krm_prods = prod_repo.search_products(category="keramik")
        self.assertTrue(any(p["sku"] == "QH-KRM-001" for p in krm_prods))

    def test_deterministic_calculator_tools(self) -> None:
        # 4. calculate_tile_boxes works correctly (ceil, waste_percent=10%)
        # area=4.0, coverage=1.44: 4.0 * 1.1 = 4.4. 4.4 / 1.44 = 3.05. ceil = 4 boxes.
        boxes = calculate_tile_boxes(4.0, 1.44)
        self.assertEqual(boxes, 4)

        # calculate_paint_liters works correctly
        # area=15.0, coverage=10.0, coats=2: 15.0 * 2 = 30.0. 30.0 / 10.0 = 3.0. 3.0 * 1.1 = 3.3 liters.
        liters = calculate_paint_liters(15.0, 10.0)
        self.assertEqual(liters, 3.3)

    def test_quote_builder_persistence(self) -> None:
        init_db(self.test_db_path)
        qte_repo = QuoteRepository(self.test_db_path)

        # 5. Quote builder creates quote and quote items in SQLite
        qte_repo.create_quote(
            quote_code="QTE-12345",
            ticket_code="TKT-TEST",
            estimated_total=250000,
            budget=300000,
            budget_status="within_budget",
            risk_level="low",
            notes="Testing quote",
        )
        qte_repo.add_quote_item("QTE-12345", "QH-KRM-001", "Anti Slip Tile", 2, "box", 85000, 170000)

        quote = qte_repo.get_quote_by_ticket("TKT-TEST")
        self.assertIsNotNone(quote)
        self.assertEqual(quote["quote_code"], "QTE-12345")
        self.assertEqual(len(quote["items"]), 1)
        self.assertEqual(quote["items"][0]["sku"], "QH-KRM-001")

    def test_risk_verifier_validation(self) -> None:
        # 6. risk verifier detects unsafe stock/final price claim and budget status
        quote = {
            "quote_code": "QTE-12345",
            "estimated_total": 2500000,
            "budget": 2000000,
            "budget_status": "over_budget",
            "customer_whatsapp": None,
        }
        missing_info = ["ukuran tinggi dinding"]
        inventory_notes = ["low_stock of QH-KRM-001"]

        risks = verify_quote_risks(quote, missing_info, inventory_notes)
        
        # Must detect over budget
        self.assertTrue(any("melebihi kapasitas anggaran" in r for r in risks))
        # Must detect low stock
        self.assertTrue(any("stok terbatas" in r for r in risks))
        # Must detect missing dimensions
        self.assertTrue(any("Ukuran ruangan belum lengkap" in r for r in risks))

    def test_full_7_agent_sequential_renovation_pipeline(self) -> None:
        # Pre-seed test database
        seed_db(self.project_root, self.test_db_path)

        ticket = {
            "id": "eval-bathroom-2x2",
            "customer_name": "Ibu Maya",
            "subject": "Renovasi kamar mandi 2x2m",
            "message": "Saya mau renovasi kamar mandi ukuran 2x2m. Butuh keramik lantai anti slip, waterproofing, perekat, dan nat. Budget maksimal 3 juta. Alamat di Jalan Kaliurang, Sleman.",
        }

        knowledge_base = {"policies": [], "product_guides": []}

        # 7. Run full workflow in mock mode
        output = run_workflow(
            model=MockChatModel(),
            ticket=ticket,
            knowledge_base=knowledge_base,
            output_dir=self.project_root / "runs-test",
            run_id="renovation-run",
            db_path=self.test_db_path,
        )

        final = output["final"]
        self.assertEqual(output["run_id"], "renovation-run")
        self.assertEqual(final["category"], "renovation_quote")
        self.assertEqual(final["intent"], "kamar_mandi")
        self.assertTrue(len(output["trace"]) >= 7)

        # Check quote items and codes are populated
        self.assertIsNotNone(final.get("quote_code"))
        self.assertTrue(len(final.get("line_items", [])) > 0)
        self.assertTrue(final.get("estimated_total") > 0)


if __name__ == "__main__":
    unittest.main()
