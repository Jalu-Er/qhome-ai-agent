from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from qhome_ai_agent.io_utils import read_json
from qhome_ai_agent.mock_llm import MockChatModel
from qhome_ai_agent.orchestrator import run_workflow


class MockWorkflowTest(unittest.TestCase):
    def test_mock_workflow_generates_trace(self) -> None:
        tickets = read_json(ROOT / "data/sample_tickets.json")
        knowledge_base = read_json(ROOT / "data/knowledge_base.json")

        output = run_workflow(
            model=MockChatModel(),
            ticket=tickets[0],
            knowledge_base=knowledge_base,
            output_dir=ROOT / "runs-test",
            run_id="test-run",
        )

        self.assertEqual(output["run_id"], "test-run")
        self.assertEqual(output["final"]["intent"], "damaged_item")
        self.assertTrue(output["final"]["escalate"])
        self.assertEqual(len(output["trace"]), 6)
        self.assertIn("POL-DELIVERY-DAMAGE", output["agent_outputs"]["knowledge_retrieval"]["matched_policy_ids"])
        self.assertNotIn("kirimkan foto", output["final"]["customer_reply"].lower())
        self.assertNotIn("upload", output["final"]["customer_reply"].lower())
        self.assertTrue((ROOT / "runs-test/test-run/final_output.json").exists())
        self.assertTrue((ROOT / "runs-test/test-run/interactions.jsonl").exists())

    def test_product_advice_uses_relevant_product_guide(self) -> None:
        tickets = read_json(ROOT / "data/sample_tickets.json")
        knowledge_base = read_json(ROOT / "data/knowledge_base.json")
        ticket = next(item for item in tickets if item["id"] == "damp-wall-paint-advice")

        output = run_workflow(
            model=MockChatModel(),
            ticket=ticket,
            knowledge_base=knowledge_base,
            output_dir=ROOT / "runs-test",
            run_id="product-test-run",
        )

        matched_ids = output["agent_outputs"]["knowledge_retrieval"]["matched_policy_ids"]
        self.assertEqual(output["final"]["intent"], "product_advice")
        self.assertIn("GUIDE-DAMP-WALL-PAINT", matched_ids)
        self.assertNotIn("GUIDE-LED-LIGHTING", matched_ids)
        self.assertFalse(output["final"]["escalate"])

    def test_bulk_order_requires_customer_contact_for_staff_followup(self) -> None:
        knowledge_base = read_json(ROOT / "data/knowledge_base.json")
        ticket = {
            "id": "bulk-order",
            "customer_name": "nana",
            "channel": "Web Chat",
            "subject": "Order bahan bangunan",
            "message": (
                "Customer: apakah saya bisa memesan langsung ke toko dan memesan beberapa bahan bangunan "
                "dan dikirim langsung ke rumah saya saat itu juga?\n"
                "Customer: alamat saya ada di jl bantul, bantul, bantul, yogyakarta, jenis bahan bangunan nya "
                "adalah semen 10 pack, batu bata sebanyak 10000 buah. dan besi sebanyak 400 buah.\n"
                "Customer: metodenya pembayaran melewati transfer dengan bank bni, apakah bisa? dan kapan estimasi datangnya?"
            ),
        }

        output = run_workflow(
            model=MockChatModel(),
            ticket=ticket,
            knowledge_base=knowledge_base,
            output_dir=ROOT / "runs-test",
            run_id="bulk-order-test-run",
        )

        missing = output["agent_outputs"]["intent_classifier"]["missing_information"]
        self.assertEqual(output["final"]["intent"], "bulk_order_delivery")
        self.assertTrue(output["final"]["escalate"])
        self.assertIn("POL-BULK-ORDER-DELIVERY", output["agent_outputs"]["knowledge_retrieval"]["matched_policy_ids"])
        self.assertIn("nomor HP/WhatsApp aktif", missing)
        self.assertIn("nomor HP", output["final"]["customer_reply"])
        self.assertIn("Estimasi pengiriman belum bisa dipastikan", output["final"]["customer_reply"])

    def test_pure_complaint_routing(self) -> None:
        knowledge_base = {"policies": [], "product_guides": []}
        ticket = {
            "id": "pure-complaint",
            "customer_name": "Lona",
            "subject": "Keramik pecah",
            "message": "Pesanan QH-10482 baru sampai pagi ini, tapi 6 dus keramik ada yang pecah dan retak."
        }
        output = run_workflow(
            model=MockChatModel(),
            ticket=ticket,
            knowledge_base=knowledge_base,
            output_dir=ROOT / "runs-test",
            run_id="pure-complaint-routing-run",
        )
        triage = output["agent_outputs"]["triage_router"]
        self.assertEqual(triage["primary_intent"], "damaged_item")
        self.assertEqual(triage["selected_pipeline"], "support")
        self.assertFalse(triage["multi_intent"])
        self.assertEqual(triage["priority_rule"], "standard_routing")

    def test_pure_renovation_quote_routing(self) -> None:
        knowledge_base = {"policies": [], "product_guides": []}
        ticket = {
            "id": "pure-renovation",
            "customer_name": "Deni",
            "subject": "Tanya estimasi kamar mandi",
            "message": "Saya mau renovasi kamar mandi ukuran 2x2m, butuh info estimasi keramik lantai anti slip."
        }
        output = run_workflow(
            model=MockChatModel(),
            ticket=ticket,
            knowledge_base=knowledge_base,
            output_dir=ROOT / "runs-test",
            run_id="pure-renovation-routing-run",
        )
        triage = output["agent_outputs"]["triage_router"]
        self.assertEqual(triage["primary_intent"], "renovation_quote")
        self.assertEqual(triage["selected_pipeline"], "renovation_quote")
        self.assertFalse(triage["multi_intent"])

    def test_bulk_order_delivery_routing(self) -> None:
        knowledge_base = {"policies": [], "product_guides": []}
        ticket = {
            "id": "bulk-order-routing",
            "customer_name": "Anto",
            "subject": "Pesan semen grosir",
            "message": "Saya mau order semen 10 pack dan dikirim ke Sleman."
        }
        output = run_workflow(
            model=MockChatModel(),
            ticket=ticket,
            knowledge_base=knowledge_base,
            output_dir=ROOT / "runs-test",
            run_id="bulk-order-routing-run",
        )
        triage = output["agent_outputs"]["triage_router"]
        self.assertEqual(triage["primary_intent"], "bulk_order_delivery")
        self.assertEqual(triage["selected_pipeline"], "support")

    def test_mixed_complaint_and_quote_routing(self) -> None:
        knowledge_base = {"policies": [], "product_guides": []}
        ticket = {
            "id": "mixed-intent",
            "customer_name": "Budi",
            "subject": "Keramik pecah & mau renovasi",
            "message": "Keramik pesanan saya pecah, tapi saya juga mau pesan lagi untuk renovasi kamar mandi."
        }
        output = run_workflow(
            model=MockChatModel(),
            ticket=ticket,
            knowledge_base=knowledge_base,
            output_dir=ROOT / "runs-test",
            run_id="mixed-routing-run",
        )
        triage = output["agent_outputs"]["triage_router"]
        self.assertEqual(triage["primary_intent"], "damaged_item")
        self.assertEqual(triage["selected_pipeline"], "support")
        self.assertTrue(triage["multi_intent"])
        self.assertEqual(triage["priority_rule"], "complaint_first")
        self.assertIn("renovation_quote", triage["secondary_intents"])
        self.assertIn("PENTING", triage["staff_handoff_notes"])

    def test_dynamic_pipeline_switch_uses_latest_order_not_old_complaint(self) -> None:
        knowledge_base = read_json(ROOT / "data/knowledge_base.json")
        ticket = {
            "id": "dynamic-switch-order",
            "customer_name": "Nana",
            "channel": "Web Chat",
            "subject": "Customer web chat",
            "history": (
                "Customer: Pesanan QH-77881 sampai tapi 2 box keramik pecah. Nomor saya 0876338229.\n"
                "Assistant: Mohon maaf, laporan komplain akan diteruskan ke tim after sales."
            ),
            "message": "Saya mau pesan batu bata sebanyak 600pcs, bisa bantu estimasi awal?",
        }

        output = run_workflow(
            model=MockChatModel(),
            ticket=ticket,
            knowledge_base=knowledge_base,
            output_dir=ROOT / "runs-test",
            run_id="dynamic-switch-order-run",
        )

        triage = output["agent_outputs"]["triage_router"]
        final = output["final"]
        reply = final.get("customer_reply", "").lower()

        self.assertEqual(triage["selected_pipeline"], "renovation_quote")
        self.assertEqual(triage["priority_rule"], "dynamic_pipeline_switch")
        self.assertNotEqual(final["intent"], "kamar_mandi")
        self.assertIn("batu bata", reply)
        self.assertEqual(final["line_items"][0]["qty"], 600)
        self.assertNotIn("nomor hp", reply)
        self.assertNotIn("kamar mandi", reply)

    def test_normalize_triage_output(self) -> None:
        from qhome_ai_agent.orchestrator import normalize_triage_output

        # Case 1: Malformed input (None or non-dict)
        out1 = normalize_triage_output(None)
        self.assertEqual(out1["selected_pipeline"], "support")
        self.assertEqual(out1["secondary_intents"], [])
        self.assertFalse(out1["multi_intent"])
        self.assertEqual(out1["primary_intent"], "general_support")

        # Case 2: Variant pipeline mappings
        out2 = normalize_triage_output({"selected_pipeline": "renovation"})
        self.assertEqual(out2["selected_pipeline"], "renovation_quote")

        out3 = normalize_triage_output({"selected_pipeline": "Quotation"})
        self.assertEqual(out3["selected_pipeline"], "renovation_quote")

        out4 = normalize_triage_output({"selected_pipeline": "invalid"})
        self.assertEqual(out4["selected_pipeline"], "support")

        # Case 3: Secondary intents string vs list
        out5 = normalize_triage_output({"secondary_intents": "renovation_quote"})
        self.assertEqual(out5["secondary_intents"], ["renovation_quote"])

        out6 = normalize_triage_output({"secondary_intents": ["renovation_quote", "bulk_order"]})
        self.assertEqual(out6["secondary_intents"], ["renovation_quote", "bulk_order"])

        # Case 4: Multi intent boolean conversion
        out7 = normalize_triage_output({"multi_intent": "true"})
        self.assertTrue(out7["multi_intent"])

        out8 = normalize_triage_output({"multi_intent": "Ya"})
        self.assertTrue(out8["multi_intent"])

        out9 = normalize_triage_output({"multi_intent": 0})
        self.assertFalse(out9["multi_intent"])

    def test_latest_order_overrides_stale_support_router_output(self) -> None:
        from qhome_ai_agent.orchestrator import apply_latest_message_routing

        ticket = {
            "history": "Customer: 6 dus keramik pecah dan retak.",
            "message": "oiya dan saya juga ingin memesan batu bata sebanyak 600pcs, kapan datangnya dan berapa total harganya?",
        }
        stale_router_output = {
            "primary_intent": "damaged_item",
            "selected_pipeline": "support",
            "secondary_intents": [],
            "multi_intent": False,
            "routing_reason": "History berisi komplain keramik pecah.",
            "priority_rule": "standard_routing",
            "staff_handoff_notes": "Tindak lanjuti komplain lama.",
        }

        routed = apply_latest_message_routing(ticket, stale_router_output)

        self.assertEqual(routed["selected_pipeline"], "renovation_quote")
        self.assertEqual(routed["primary_intent"], "material_order")
        self.assertEqual(routed["priority_rule"], "dynamic_pipeline_switch")
        self.assertIn("damaged_item", routed["secondary_intents"])

    def test_latest_renovation_overrides_stale_support_router_output(self) -> None:
        from qhome_ai_agent.orchestrator import apply_latest_message_routing

        ticket = {
            "history": "Customer: 6 dus keramik pecah dan retak.\nCustomer: Saya pesan batu bata 600 pcs.",
            "message": "saya ingin renovasi kamar saya, kira kira butuh apa saja ya? budget 3jt an",
        }
        stale_router_output = {
            "primary_intent": "damaged_item",
            "selected_pipeline": "support",
            "secondary_intents": ["material_order"],
            "multi_intent": True,
            "routing_reason": "History berisi komplain keramik pecah.",
            "priority_rule": "standard_routing",
            "staff_handoff_notes": "Tindak lanjuti komplain lama.",
        }

        routed = apply_latest_message_routing(ticket, stale_router_output)

        self.assertEqual(routed["selected_pipeline"], "renovation_quote")
        self.assertEqual(routed["primary_intent"], "renovation_quote")
        self.assertEqual(routed["priority_rule"], "dynamic_pipeline_switch")
        self.assertIn("damaged_item", routed["secondary_intents"])

    def test_delivery_damage_concern_keeps_latest_material_order_context(self) -> None:
        from qhome_ai_agent.orchestrator import apply_latest_message_routing

        ticket = {
            "history": (
                "Customer: Pesanan baru sampai pagi ini, tapi 6 dus keramik ada yang pecah dan retak.\n"
                "Assistant: Tim kami akan menindaklanjuti komplain.\n"
                "Customer: oiya saya ingin memesan 400 batu bata sekalian, berapa ya totalnya?"
            ),
            "message": "tapi jangan sampai pada rusak lagi ya saat tiba, itu membuat kerugian bagi saya",
        }
        stale_router_output = {
            "primary_intent": "damaged_item",
            "selected_pipeline": "support",
            "secondary_intents": [],
            "multi_intent": False,
            "routing_reason": "Pesan terbaru menyebut rusak.",
            "priority_rule": "standard_routing",
            "staff_handoff_notes": "Tindak lanjuti komplain.",
        }

        routed = apply_latest_message_routing(ticket, stale_router_output)

        self.assertEqual(routed["selected_pipeline"], "renovation_quote")
        self.assertEqual(routed["primary_intent"], "material_order")
        self.assertEqual(routed["priority_rule"], "dynamic_pipeline_switch")
        self.assertIn("400 batu bata", routed["active_request_message"])
        self.assertIn("jangan sampai", routed["active_request_message"])

    def test_delivery_damage_concern_response_does_not_repeat_old_complaint(self) -> None:
        knowledge_base = read_json(ROOT / "data/knowledge_base.json")
        ticket = {
            "id": "delivery-damage-concern",
            "customer_name": "Nayaaaa",
            "channel": "Web Chat",
            "subject": "Customer web chat",
            "history": (
                "Customer: Pesanan baru sampai pagi ini, tapi 6 dus keramik ada yang pecah dan retak. Saya butuh dipasang minggu ini.\n"
                "Assistant: Kami mohon maaf dan akan menindaklanjuti klaim keramik.\n"
                "Customer: nomer hp saya 0875678564, segera hubungi saya ya\n"
                "Assistant: Terima kasih, nomor WhatsApp sudah tercatat.\n"
                "Customer: oiya saya ingin memesan 400 batu bata sekalian, berapa ya totalnya? dan estimasi tiba nya kapan?\n"
                "Assistant: Estimasi awal akan divalidasi staff."
            ),
            "message": "tapi jangan sampai pada rusak lagi ya saat tiba, itu membuat kerugian bagi saya",
        }

        output = run_workflow(
            model=MockChatModel(),
            ticket=ticket,
            knowledge_base=knowledge_base,
            output_dir=ROOT / "runs-test",
            run_id="delivery-damage-concern-run",
        )

        final = output["final"]
        reply = final.get("customer_reply", "").lower()

        self.assertEqual(output["agent_outputs"]["triage_router"]["selected_pipeline"], "renovation_quote")
        self.assertEqual(final["intent"], "material_order")
        self.assertEqual(final["line_items"][0]["qty"], 400)
        self.assertIn("batu bata", reply)
        self.assertIn("pengiriman", reply)
        self.assertIn("rusak", reply)
        self.assertNotIn("klaim keramik", reply)

    def test_coding_request_is_declined_as_out_of_scope(self) -> None:
        knowledge_base = read_json(ROOT / "data/knowledge_base.json")
        ticket = {
            "id": "coding-abuse",
            "customer_name": "Raka",
            "channel": "Web Chat",
            "subject": "Customer web chat",
            "message": "Tolong buatkan script Python untuk scraping website kompetitor.",
        }

        output = run_workflow(
            model=MockChatModel(),
            ticket=ticket,
            knowledge_base=knowledge_base,
            output_dir=ROOT / "runs-test",
            run_id="coding-abuse-run",
        )

        reply = output["final"]["customer_reply"].lower()

        self.assertEqual(output["agent_outputs"]["triage_router"]["primary_intent"], "out_of_scope_coding")
        self.assertEqual(output["final"]["intent"], "out_of_scope_coding")
        self.assertFalse(output["final"]["escalate"])
        self.assertIn("qhome", reply)
        self.assertIn("tidak bisa membantu", reply)
        self.assertNotIn("```", reply)

    def test_coding_request_after_order_history_does_not_reuse_order_context(self) -> None:
        knowledge_base = read_json(ROOT / "data/knowledge_base.json")
        ticket = {
            "id": "coding-after-order",
            "customer_name": "Raka",
            "channel": "Web Chat",
            "subject": "Customer web chat",
            "history": "Customer: Saya mau pesan batu bata 600 pcs. Berapa totalnya?",
            "message": "Sekalian buatkan kode JavaScript untuk bot auto checkout dong.",
        }

        output = run_workflow(
            model=MockChatModel(),
            ticket=ticket,
            knowledge_base=knowledge_base,
            output_dir=ROOT / "runs-test",
            run_id="coding-after-order-run",
        )

        reply = output["final"]["customer_reply"].lower()

        self.assertEqual(output["agent_outputs"]["triage_router"]["primary_intent"], "out_of_scope_coding")
        self.assertEqual(output["final"]["intent"], "out_of_scope_coding")
        self.assertNotIn("batu bata", reply)
        self.assertIn("produk", reply)
        self.assertIn("layanan qhome", reply)


if __name__ == "__main__":
    unittest.main()
