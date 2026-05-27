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
        text = self._customer_text(f"{ticket.get('subject', '')} {ticket.get('message', '')}")
        outputs = state.get("agent_outputs", {})

        if agent_name == "intent_classifier":
            return self._intent(text)
        if agent_name == "knowledge_retrieval":
            return self._knowledge(payload.get("knowledge_base", {}), text, outputs)
        if agent_name == "solution_planner":
            return self._solution(outputs)
        if agent_name == "priority_escalation":
            return self._priority(outputs, text)
        if agent_name == "qa_final_response":
            return self._final(ticket, outputs)
        raise ValueError(f"Unknown mock agent: {agent_name}")

    def _intent(self, text: str) -> dict[str, Any]:
        if any(word in text for word in ["cat", "dinding", "lembab", "jamur", "rekomendasi", "pakai apa"]):
            intent = "product_advice"
            category = "product_consultation"
        elif any(word in text for word in ["pecah", "rusak", "retak", "damage"]):
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
            "summary": "Pelanggan membutuhkan bantuan QHome Mart terkait layanan atau rekomendasi produk.",
            "missing_information": self._missing_information(intent, text),
            "reasoning": "Kata kunci pada pesan pelanggan dipetakan ke kategori layanan atau konsultasi produk yang paling relevan.",
        }

    def _knowledge(self, knowledge_base: dict[str, Any], text: str, outputs: dict[str, Any]) -> dict[str, Any]:
        intent = outputs.get("intent_classifier", {}).get("intent", "")
        scored = []
        entries = knowledge_base.get("policies", []) + knowledge_base.get("product_guides", [])
        for policy in entries:
            haystack = " ".join(
                [
                    policy.get("id", ""),
                    policy.get("title", ""),
                    policy.get("summary", ""),
                    " ".join(policy.get("keywords", [])),
                    " ".join(policy.get("recommended_product_types", [])),
                ]
            ).lower()
            keywords = {keyword.lower() for keyword in policy.get("keywords", [])}
            tokens = {token.strip(".,?!").lower() for token in text.split() if len(token.strip(".,?!")) > 4}
            score = len(tokens.intersection(keywords))
            if policy.get("id", "").startswith("GUIDE") and any(word in text for word in ["rekomendasi", "pakai apa", "butuh"]):
                score += 1
            if intent == "product_advice" and policy.get("id", "").startswith("GUIDE"):
                score += 3
            if intent == "damaged_item" and policy.get("id") == "POL-DELIVERY-DAMAGE":
                score += 4
            if intent == "delivery_tracking" and policy.get("id") == "POL-DELIVERY-TRACKING":
                score += 4
            if intent == "return_or_refund" and policy.get("id") == "POL-RETURN-7D":
                score += 4
            if any(token in haystack for token in tokens.intersection(keywords)):
                score += 1
            if score:
                scored.append((score, policy))

        scored.sort(key=lambda item: item[0], reverse=True)
        matched = [policy for score, policy in scored if score >= scored[0][0]] if scored else []
        if len(matched) < 1 and scored:
            matched = [scored[0][1]]
        if not matched:
            matched = entries[:2]

        return {
            "matched_policy_ids": [item["id"] for item in matched[:3]],
            "relevant_facts": [item["summary"] for item in matched[:3]],
            "confidence": 0.78,
            "reasoning": "Knowledge base lokal difilter berdasarkan intent dan kata kunci dari ticket.",
        }

    def _solution(self, outputs: dict[str, Any]) -> dict[str, Any]:
        intent = outputs.get("intent_classifier", {}).get("intent", "general_support")
        facts = outputs.get("knowledge_retrieval", {}).get("relevant_facts", [])
        if intent == "product_advice":
            actions = [
                "Tanyakan lokasi dinding, tingkat lembab, dan apakah ada rembes aktif.",
                "Sarankan memperbaiki sumber lembab terlebih dahulu jika ada rembes aktif.",
                "Rekomendasikan alkali resisting primer atau wall sealer anti lembab sebelum cat akhir.",
                "Pilih cat anti jamur sesuai area indoor atau outdoor setelah permukaan siap.",
            ]
        elif intent == "damaged_item":
            missing = outputs.get("intent_classifier", {}).get("missing_information", [])
            if missing:
                actions = [
                    "Catat kebutuhan bukti kerusakan untuk follow-up staff.",
                    "Validasi apakah laporan masih dalam batas waktu klaim kerusakan.",
                    "Eskalasi ke tim after sales jika bukti dan data instalasi sudah lengkap.",
                ]
            else:
                actions = [
                    "Validasi bukti kerusakan dan nomor pesanan.",
                    "Eskalasi ke tim after sales untuk klaim penggantian.",
                    "Koordinasikan jadwal instalasi setelah klaim disetujui.",
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
        if intent == "product_advice":
            return {
                "priority": "medium",
                "escalate": False,
                "escalation_team": None,
                "sla_recommendation": "Respond within 1 business day",
                "business_risk": "Risiko rendah-sedang: rekomendasi produk perlu caveat agar pelanggan tidak salah aplikasi.",
                "reasoning": "Konsultasi produk tidak perlu eskalasi langsung, tetapi perlu pertanyaan lanjutan dan batasan penggunaan.",
            }
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
        missing = intent.get("missing_information", [])
        if intent.get("intent") == "product_advice":
            response = (
                f"Halo {ticket.get('customer_name', 'Kak')}, untuk dinding lembab sebaiknya jangan langsung ditutup cat akhir. "
                "Cek dulu apakah ada rembes aktif. Jika ada, sumber lembabnya perlu diperbaiki atau diberi waterproofing. "
                "Setelah permukaan bersih dan kering, gunakan alkali resisting primer atau wall sealer anti lembab, "
                "lalu pilih cat anti jamur yang sesuai area indoor/outdoor. "
                "Boleh info dindingnya di dalam/luar rumah dan lembabnya berupa jamur, noda, atau rembes?"
            )
        elif intent.get("intent") == "damaged_item" and not missing:
            response = (
                f"Terima kasih {ticket.get('customer_name', 'Kak')}, informasi dan bukti yang dibutuhkan sudah kami terima. "
                "Kami akan teruskan ke tim after sales untuk validasi klaim kerusakan dan koordinasi jadwal instalasi. "
                "Tim kami akan memprioritaskan kasus ini karena terkait barang rusak dan kebutuhan pemasangan."
            )
        else:
            response = (
                f"Halo {ticket.get('customer_name', 'Kak')}, mohon maaf atas kendalanya. "
                "Saya sudah mencatat laporan ini untuk tim support. "
                "Agar klaim bisa diproses, staff akan melakukan follow-up untuk memastikan bukti kerusakan dan detail instalasi yang masih dibutuhkan. "
                f"Langkah internal kami: {'; '.join(actions[:3])}"
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

    def _missing_information(self, intent: str, text: str) -> list[str]:
        if intent == "product_advice":
            missing = []
            if "indoor" not in text and "outdoor" not in text and "dalam" not in text and "luar" not in text:
                missing.append("lokasi dinding indoor atau outdoor")
            if "rembes" not in text:
                missing.append("apakah ada rembes aktif")
            return missing
        if intent == "damaged_item":
            missing = []
            if "qh-" not in text:
                missing.append("nomor pesanan")
            if "foto" not in text and "gambar" not in text:
                missing.append("status bukti kerusakan")
            if any(word in text for word in ["pasang", "instalasi", "dipasang"]) and "alamat" not in text:
                missing.append("alamat instalasi")
            if any(word in text for word in ["pasang", "instalasi", "dipasang"]) and not any(word in text for word in ["senin", "selasa", "rabu", "kamis", "jumat", "sabtu", "minggu", "jadwal"]):
                missing.append("jadwal instalasi")
            return missing
        return ["nomor pesanan"] if "qh-" not in text else []

    def _customer_text(self, text: str) -> str:
        lines = []
        for line in text.splitlines():
            lowered = line.lower().strip()
            if lowered.startswith("assistant:"):
                continue
            if lowered.startswith("customer:"):
                lines.append(lowered.removeprefix("customer:").strip())
            else:
                lines.append(lowered)
        return " ".join(lines)
