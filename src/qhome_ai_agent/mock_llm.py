from __future__ import annotations

from typing import Any


class MockChatModel:
    """Deterministic agent outputs for reproducible demos and tests."""

    def generate_json(
        self,
        *,
        agent_name: str,
        system_prompt: str,
        payload: dict[str, Any],
        max_tokens: int = 1200,
    ) -> dict[str, Any]:
        state = payload.get("state", {})
        ticket = state.get("ticket", payload.get("ticket", {}))
        text = f"{ticket.get('subject', '')} {ticket.get('message', '')}".lower()
        outputs = state.get("agent_outputs", {})

        if agent_name == "intent_classifier":
            return self._intent(text)
        if agent_name == "knowledge_retrieval":
            return self._knowledge(payload.get("knowledge_base", {}), text)
        if agent_name == "solution_planner":
            return self._solution(outputs)
        if agent_name == "priority_escalation":
            return self._priority(outputs, text)
        if agent_name == "qa_final_response":
            return self._final(ticket, outputs)
        raise ValueError(f"Unknown mock agent: {agent_name}")

    def _intent(self, text: str) -> dict[str, Any]:
        if any(word in text for word in ["pecah", "rusak", "retak", "damage"]):
            intent = "damaged_item"
            category = "delivery_issue"
        elif any(word in text for word in ["belum sampai", "terlambat", "resi", "kirim"]):
            intent = "delivery_tracking"
            category = "delivery_issue"
        elif any(word in text for word in ["retur", "refund", "tukar"]):
            intent = "return_or_refund"
            category = "after_sales"
        else:
            intent = "general_support"
            category = "customer_service"

        return {
            "intent": intent,
            "category": category,
            "confidence": 0.84,
            "summary": "Pelanggan membutuhkan bantuan support terkait pesanan QHome Mart.",
            "missing_information": ["nomor pesanan"] if "qh-" not in text else [],
            "reasoning": "Kata kunci pada pesan pelanggan dipetakan ke kategori support yang paling relevan.",
        }

    def _knowledge(self, knowledge_base: dict[str, Any], text: str) -> dict[str, Any]:
        matched = []
        for policy in knowledge_base.get("policies", []):
            haystack = " ".join(
                [
                    policy.get("id", ""),
                    policy.get("title", ""),
                    policy.get("summary", ""),
                    " ".join(policy.get("keywords", [])),
                ]
            ).lower()
            if any(token in haystack for token in text.split() if len(token) > 4):
                matched.append(policy)

        if not matched:
            matched = knowledge_base.get("policies", [])[:2]

        return {
            "matched_policy_ids": [item["id"] for item in matched[:3]],
            "relevant_facts": [item["summary"] for item in matched[:3]],
            "confidence": 0.78,
            "reasoning": "Knowledge base lokal difilter berdasarkan intent dan kata kunci dari ticket.",
        }

    def _solution(self, outputs: dict[str, Any]) -> dict[str, Any]:
        intent = outputs.get("intent_classifier", {}).get("intent", "general_support")
        facts = outputs.get("knowledge_retrieval", {}).get("relevant_facts", [])
        if intent == "damaged_item":
            actions = [
                "Minta nomor pesanan, foto produk rusak, foto kemasan, dan video unboxing jika ada.",
                "Validasi apakah laporan masih dalam batas waktu klaim kerusakan.",
                "Tawarkan penggantian barang atau proses klaim sesuai kebijakan.",
            ]
        elif intent == "delivery_tracking":
            actions = [
                "Minta nomor pesanan atau resi.",
                "Cek status pengiriman dan estimasi tiba.",
                "Eskalasi ke tim fulfillment jika melebihi SLA.",
            ]
        else:
            actions = [
                "Konfirmasi detail kebutuhan pelanggan.",
                "Berikan jawaban berdasarkan kebijakan yang relevan.",
                "Tawarkan eskalasi jika pelanggan membutuhkan keputusan khusus.",
            ]

        return {
            "recommended_actions": actions,
            "customer_response_outline": [
                "Sampaikan empati singkat.",
                "Jelaskan data yang dibutuhkan.",
                "Berikan langkah penyelesaian berikutnya.",
            ],
            "policy_basis": facts,
            "reasoning": "Solusi disusun dari intent, knowledge base, dan kebutuhan data yang masih kurang.",
        }

    def _priority(self, outputs: dict[str, Any], text: str) -> dict[str, Any]:
        intent = outputs.get("intent_classifier", {}).get("intent", "")
        high_risk = intent == "damaged_item" or any(word in text for word in ["komplain", "marah", "urgent"])
        return {
            "priority": "high" if high_risk else "medium",
            "escalate": high_risk,
            "escalation_team": "after_sales" if high_risk else None,
            "sla_recommendation": "Respond within 2 business hours" if high_risk else "Respond within 1 business day",
            "business_risk": "Risiko refund, penggantian barang, dan pengalaman pelanggan buruk." if high_risk else "Risiko operasional normal.",
            "reasoning": "Prioritas ditentukan dari intent, potensi biaya, dan risiko kepuasan pelanggan.",
        }

    def _final(self, ticket: dict[str, Any], outputs: dict[str, Any]) -> dict[str, Any]:
        intent = outputs.get("intent_classifier", {})
        solution = outputs.get("solution_planner", {})
        priority = outputs.get("priority_escalation", {})
        actions = solution.get("recommended_actions", [])
        response = (
            f"Halo {ticket.get('customer_name', 'Kak')}, mohon maaf atas kendalanya. "
            "Agar tim kami bisa membantu dengan cepat, mohon kirimkan nomor pesanan dan bukti pendukung. "
            f"Langkah yang akan kami lakukan: {'; '.join(actions[:3])}"
        )
        return {
            "ticket_summary": intent.get("summary", "Ticket pelanggan membutuhkan tindak lanjut."),
            "intent": intent.get("intent"),
            "category": intent.get("category"),
            "priority": priority.get("priority"),
            "escalate": priority.get("escalate"),
            "escalation_team": priority.get("escalation_team"),
            "customer_reply": response,
            "internal_next_steps": actions,
            "quality_checks": {
                "uses_policy_context": bool(solution.get("policy_basis")),
                "has_clear_next_steps": bool(actions),
                "mentions_escalation": bool(priority.get("escalate")),
            },
            "reasoning": "Jawaban final menggabungkan klasifikasi, policy basis, rencana solusi, dan prioritas eskalasi.",
        }
