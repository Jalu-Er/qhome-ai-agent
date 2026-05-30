import unittest
from src.qhome_ai_agent.mock_llm import MockChatModel

class TestSupportCasePacket(unittest.TestCase):
    def setUp(self):
        self.model = MockChatModel()

    def test_missing_wa_prevents_contact_instruction(self):
        ticket = {"customer_whatsapp": None}
        inputs = {
            "intent_classifier": {"intent": "damaged_item"},
            "priority_escalation": {"priority": "high", "escalate": True}
        }
        output = self.model._final(ticket, inputs)
        staff_action = output.get("support_case", {}).get("staff_next_action", "").lower()
        
        self.assertNotIn("hubungi pelanggan melalui whatsapp", staff_action)
        self.assertNotIn("hubungi pelanggan secara langsung", staff_action)
        self.assertTrue("tunggu" in staff_action or "chat" in staff_action or "minta" in staff_action,
                        f"Expected instruction to ask for WA via chat, got: {staff_action}")

    def test_wa_present_allows_contact_instruction(self):
        ticket = {"customer_whatsapp": "08123456789"}
        inputs = {
            "intent_classifier": {"intent": "damaged_item"},
            "priority_escalation": {"priority": "high", "escalate": True}
        }
        output = self.model._final(ticket, inputs)
        staff_action = output.get("support_case", {}).get("staff_next_action", "").lower()
        
        self.assertTrue("hubungi pelanggan" in staff_action or "telepon pelanggan" in staff_action)

if __name__ == "__main__":
    unittest.main()
