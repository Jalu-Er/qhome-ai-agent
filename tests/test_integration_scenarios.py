import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from qhome_ai_agent.mock_llm import MockChatModel
from qhome_ai_agent.orchestrator import run_workflow

class TestIntegrationScenarios(unittest.TestCase):
    def setUp(self):
        self.model = MockChatModel()
        self.knowledge_base = {"policies": [], "product_guides": []}
        self.sessions = {}

    def process_message(self, session_id: str, message: str):
        if session_id not in self.sessions:
            self.sessions[session_id] = {
                "id": session_id,
                "history": [],
                "session_state": {},
                "customer_whatsapp": None
            }
        
        session = self.sessions[session_id]
        
        # Build history string from previous messages
        history_lines = []
        for past_run in session["history"]:
            past_msg = past_run.get("ticket", {}).get("message", "")
            if past_msg:
                history_lines.append(f"Customer: {past_msg}")
            past_resp = past_run.get("final", {}).get("customer_reply", "")
            if past_resp:
                history_lines.append(f"Assistant: {past_resp}")
        history_str = "\n".join(history_lines)
        
        ticket = {
            "id": f"ticket-{session_id}-{len(session['history'])}",
            "customer_name": "Test User",
            "message": message,
            "history": history_str,
            "session_state": session["session_state"],
            "customer_whatsapp": session["customer_whatsapp"]
        }
        
        output = run_workflow(
            model=self.model,
            ticket=ticket,
            knowledge_base=self.knowledge_base,
            output_dir=ROOT / "runs-test",
            run_id=ticket["id"]
        )
        
        # Update session state based on triage and final output
        final_resp = output["agent_outputs"].get("final_response", {})
        triage = output["agent_outputs"].get("triage_router", {})
        
        pipeline = triage.get("selected_pipeline", "support")
        intent = triage.get("primary_intent", "")
        
        new_state = {
            "active_pipeline": pipeline,
            "last_intent": intent
        }
        
        if pipeline == "support":
            support_case = final_resp.get("support_case", {})
            if support_case and "missing_data_any" in support_case: # Mock simplified
                pass
                
        session["session_state"] = new_state
        
        # Attempt to extract WA if provided
        import re
        wa_match = re.search(r"(?:08|\+628)\d{7,11}", message)
        if wa_match:
            session["customer_whatsapp"] = wa_match.group(0)
            
        session["history"].append(output)
        return output, session

    def test_support_complaint_no_wa(self):
        session_id = "test_int_1"
        message = "Pesanan QH-10482 baru sampai pagi ini, tapi 6 dus keramik ada yang pecah dan retak. Saya butuh dipasang minggu ini."
        output, session = self.process_message(session_id, message)
        
        triage = output["agent_outputs"]["triage_router"]
        self.assertEqual(triage["selected_pipeline"], "support")
        
        self.assertEqual(triage["primary_intent"], "damaged_item")
        
        final_out = output.get("final", {})
        support_case = final_out.get("support_case", {})
        self.assertTrue(support_case)
        
        staff_action = support_case.get("staff_next_action", "").lower()
        self.assertNotIn("hubungi pelanggan via wa untuk memverifikasi", staff_action)
        self.assertTrue("tunggu" in staff_action or "chat" in staff_action or "minta" in staff_action)
        
        trace = output.get("trace", [])
        self.assertGreaterEqual(len(trace), 6)

    def test_followup_wa(self):
        session_id = "test_int_2"
        self.process_message(session_id, "Pesanan QH-10482 ada yang retak.")
        
        output, session = self.process_message(session_id, "Nomor WA saya 08123456789")
        triage = output["agent_outputs"]["triage_router"]
        self.assertEqual(triage["selected_pipeline"], "support")
        
        final_out = output.get("final", {})
        support_case = final_out.get("support_case", {})
        staff_action = support_case.get("staff_next_action", "").lower()
        self.assertTrue("hubungi pelanggan" in staff_action or "telepon pelanggan" in staff_action or "eskalasi" in staff_action)

    def test_dynamic_switch_support_to_renovation(self):
        session_id = "test_int_3"
        self.process_message(session_id, "Keramik saya pecah 3 dus, minta bantuan.")
        self.process_message(session_id, "Nomor WA saya 08123456789.")
        
        output, session = self.process_message(session_id, "Saya juga ingin pesan batu bata 3000 pcs untuk pagar, berapa estimasinya?")
        triage = output["agent_outputs"]["triage_router"]
        
        self.assertEqual(triage["selected_pipeline"], "renovation_quote")
        
        trace = output.get("trace", [])
        self.assertGreaterEqual(len(trace), 8)
        
        quote = output.get("final", {})
        self.assertTrue(quote)
        self.assertGreater(quote.get("estimated_total", 0), 0)

    def test_renovation_brick_order(self):
        session_id = "test_int_4"
        output, _ = self.process_message(session_id, "Saya butuh batu bata 5000 buah untuk bangun pagar. Berapa estimasi harganya?")
        
        triage = output["agent_outputs"]["triage_router"]
        self.assertEqual(triage["selected_pipeline"], "renovation_quote")
        
        quote = output.get("final", {})
        self.assertTrue(quote)
        self.assertGreater(quote.get("estimated_total", 0), 0)

    def test_hebel_inquiry(self):
        session_id = "test_int_5"
        output, _ = self.process_message(session_id, "Saya mau renovasi pakai hebel batu bata untuk dinding 30 meter persegi, kira-kira butuh berapa?")
        triage = output["agent_outputs"]["triage_router"]
        self.assertEqual(triage["selected_pipeline"], "renovation_quote")
        
        quote = output.get("final", {})
        self.assertTrue(quote.get("line_items"))

    def test_product_not_found(self):
        session_id = "test_int_6"
        output, _ = self.process_message(session_id, "Saya mau beli material alien titanium 99 karat untuk kamar mandi.")
        
        triage = output["agent_outputs"]["triage_router"]
        self.assertEqual(triage["selected_pipeline"], "renovation_quote")
        
        final_out = output["agent_outputs"].get("final_response", {})
        response_text = final_out.get("customer_reply", "").lower()
        self.assertNotIn("qh-", response_text)

    def test_complaint_first(self):
        session_id = "test_int_7"
        output, _ = self.process_message(session_id, "Keramik saya pecah, tapi saya juga mau pesan batu bata.")
        
        triage = output["agent_outputs"]["triage_router"]
        self.assertEqual(triage["selected_pipeline"], "support")
        self.assertEqual(triage.get("priority_rule", ""), "complaint_first")

if __name__ == "__main__":
    unittest.main()
