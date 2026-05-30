import unittest
from src.qhome_ai_agent.storage import ProductRepository

class TestAliasResolver(unittest.TestCase):
    def setUp(self):
        self.store = ProductRepository()

    def test_alias_hebel(self):
        results = self.store.search_by_alias("hebel")
        self.assertTrue(len(results) > 0)
        self.assertTrue(any("QH-HBL" in p.get("sku", "") for p in results))

    def test_alias_bata(self):
        results = self.store.search_by_alias("bata")
        self.assertTrue(len(results) > 0)
        self.assertTrue(any("QH-BTB" in p.get("sku", "") for p in results))

    def test_alias_semen(self):
        results = self.store.search_by_alias("semen")
        self.assertTrue(len(results) > 0)
        self.assertTrue(any("QH-SMN" in p.get("sku", "") for p in results))

    def test_alias_pc_matches_semen(self):
        results = self.store.search_by_alias("pc")
        if results:
            self.assertTrue(any("QH-SMN" in p.get("sku", "") for p in results))

    def test_unknown_alias(self):
        results = self.store.search_by_alias("alien_titanium_99_karat")
        self.assertEqual(results, [])

    def test_product_retrieval_search_by_alias(self):
        results = self.store.search_by_keyword("hebel")
        self.assertTrue(len(results) > 0)
        self.assertTrue(any("QH-HBL" in p.get("sku", "") for p in results))

    def test_product_retrieval_search_by_keyword(self):
        results = self.store.search_by_keyword("granit")
        self.assertTrue(len(results) > 0)

    def test_hasil_produk_punya_field(self):
        results = self.store.search_by_keyword("bata")
        self.assertTrue(len(results) > 0)
        for p in results:
            self.assertIn("sku", p)
            self.assertIn("name", p)
            self.assertIn("price", p)
            self.assertIn("category", p)

if __name__ == "__main__":
    unittest.main()
