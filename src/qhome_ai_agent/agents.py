from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .llm import ChatModel
from .models import RunState


@dataclass(frozen=True)
class Agent:
    name: str
    display_name: str
    system_prompt: str

    def run(self, model: ChatModel, state: RunState) -> dict[str, Any]:
        return model.generate_json(
            agent_name=self.name,
            system_prompt=self.system_prompt,
            payload={
                "agent": self.name,
                "state": state.to_context(),
                "knowledge_base": state.knowledge_base,
            },
        )


AGENTS: list[Agent] = [
    Agent(
        name="intent_classifier",
        display_name="Intent Classifier Agent",
        system_prompt=(
            "You are the Intent Classifier Agent for QHome Mart customer support. "
            "Classify the ticket intent and category, including product_advice when the customer asks for product recommendations. "
            "Summarize the issue, identify missing information, "
            "and explain concise reasoning. Return JSON with keys: intent, category, confidence, summary, "
            "missing_information, reasoning. Use snake_case English labels for intent and category. "
            "Use Bahasa Indonesia for summary, missing_information, and reasoning."
        ),
    ),
    Agent(
        name="knowledge_retrieval",
        display_name="Knowledge Retrieval Agent",
        system_prompt=(
            "You are the Knowledge Retrieval Agent. Use the provided local knowledge base and previous agent outputs. "
            "Select relevant policies and product guides for the ticket. relevant_facts must contain selected policy or product guide "
            "summaries, not an empty array. Return JSON with keys: matched_policy_ids, relevant_facts, confidence, "
            "reasoning. Use Bahasa Indonesia for all human-readable values."
        ),
    ),
    Agent(
        name="solution_planner",
        display_name="Solution Planner Agent",
        system_prompt=(
            "You are the Solution Planner Agent. Build a practical resolution plan for the support team. "
            "For product_advice, recommend product types, ask needed follow-up questions, and include safety/usage caveats. "
            "Use intent and knowledge context. Return JSON with keys: recommended_actions, "
            "customer_response_outline, policy_basis, reasoning. recommended_actions must be an array of short "
            "Bahasa Indonesia strings, not objects. Do not imply this demo can receive file uploads; if evidence is needed, "
            "route it as an internal staff follow-up or ask whether the evidence is available. Use Bahasa Indonesia for all human-readable values."
        ),
    ),
    Agent(
        name="priority_escalation",
        display_name="Priority & Escalation Agent",
        system_prompt=(
            "You are the Priority and Escalation Agent. Decide priority, business risk, SLA, and whether the ticket "
            "needs human escalation. Return JSON with keys: priority, escalate, escalation_team, "
            "sla_recommendation, business_risk, reasoning. priority must be exactly one of: low, medium, high. "
            "escalate must be boolean. Use Bahasa Indonesia for business_risk and reasoning."
        ),
    ),
    Agent(
        name="qa_final_response",
        display_name="QA & Final Response Agent",
        system_prompt=(
            "You are the QA and Final Response Agent. Check consistency across all previous agent outputs, "
            "then produce the final customer reply and internal next steps. Return JSON with keys: ticket_summary, "
            "intent, category, priority, escalate, escalation_team, customer_reply, internal_next_steps, "
            "quality_checks, reasoning. customer_reply and internal_next_steps must use Bahasa Indonesia and match "
            "QHome Mart customer support tone. internal_next_steps must be an array of strings, not a single string. "
            "priority must be exactly one of: low, medium, high. escalate must be boolean. Do not tell customers to upload or send "
            "photos/videos through this chat; say staff will follow up for evidence when needed."
        ),
    ),
]
