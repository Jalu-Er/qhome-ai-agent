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
        self.assertEqual(len(output["trace"]), 5)
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


if __name__ == "__main__":
    unittest.main()
