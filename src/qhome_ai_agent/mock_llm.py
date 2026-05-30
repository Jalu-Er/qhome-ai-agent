from __future__ import annotations

import re
from typing import Any

from .orchestrator import is_coding_request


class MockChatModel:
    """Deterministic agent outputs for reproducible renovation and sales triage demos."""

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
        text = self._customer_text(f"{ticket.get('subject', '')} {ticket.get('message', '')} {ticket.get('history', '')}")
        outputs = state.get("agent_outputs", {})

        if agent_name == "triage_router":
            return self._triage_router(ticket, text)
        # Route new 7-Agent renovation quotation pipeline
        if agent_name == "requirement_intake":
            return self._requirement_intake(text, ticket)
        if agent_name == "product_retrieval":
            return self._product_retrieval(outputs, payload.get("catalog_products", []))
        if agent_name == "inventory_snapshot":
            return self._inventory_snapshot(payload.get("inventory_snapshots", []))
        if agent_name == "quantity_estimator":
            return self._quantity_estimator(payload.get("draft_material_estimations", []), outputs)
        if agent_name == "quote_builder":
            return self._quote_builder(payload.get("calculated_draft", {}), outputs)
        if agent_name == "risk_policy_verifier":
            return self._risk_policy_verifier(payload.get("draft_quote", {}), outputs, payload.get("policies", []))
        if agent_name == "staff_handoff_response":
            return self._staff_handoff_response(outputs)

        # Route original 5-agent fallback pipeline
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

    # --- 7-AGENT WORKFLOW MOCK GENERATORS ---

    def _triage_router(self, ticket: dict, text: str) -> dict[str, Any]:
        msg = text.lower()
        latest_msg = ticket.get("message", "").lower().strip()

        # SHORT FOLLOW-UP WORDS: These are unambiguous continuations
        SHORT_FOLLOW_UP = {
            "iya", "ok", "oke", "baik", "lanjut", "lanjutkan", "ya", "setuju",
            "siap", "yang tadi", "produk tadi", "ambil itu", "ambil yang itu",
            "ambil", "konfirmasi", "bisa", "oke deh", "oke gan", "makasih",
        }
        session_state = ticket.get("session_state", {}) or {}
        prev_pipeline = session_state.get("current_pipeline")
        prev_intent = session_state.get("last_intent") or "general_support"
        is_short_followup = latest_msg in SHORT_FOLLOW_UP or (len(latest_msg.split()) <= 3 and latest_msg in SHORT_FOLLOW_UP)

        # Detect intents from the whole conversation
        is_complaint = any(word in msg for word in ["pecah", "rusak", "retak", "terlambat", "belum sampai", "salah ukuran", "damage", "komplain"])
        is_renovation = any(word in msg for word in ["renovasi", "quote", "estimasi", "biaya", "2x2", "kamar_mandi", "renovation", "lembab", "jamur", "mandi", "batu bata", "ingin memesan"])
        is_bulk = "semen 10 pack" in msg or "order bahan bangunan" in msg or self._is_bulk_order(msg)
        is_advice = "damp-wall-paint-advice" in msg or any(word in msg for word in ["cat interior", "dinding lembab", "tembok"])
        is_coding = is_coding_request(latest_msg)

        # Detect intents specifically from the LATEST message
        latest_is_renovation = any(word in latest_msg for word in ["ingin memesan", "batu bata", "renovasi", "quote", "estimasi", "biaya"])
        latest_is_complaint = any(word in latest_msg for word in ["pecah", "rusak", "retak"])

        # Default fallback
        primary_intent = "general_support"
        secondary_intents = []
        selected_pipeline = "support"
        multi_intent = False
        priority_rule = "standard_routing"
        routing_reason = "Layanan pelanggan QHome Mart standar."
        staff_handoff_notes = "Tangani pertanyaan umum dari pelanggan secara profesional."

        # SHORT FOLLOW-UP: keep same pipeline as previous session
        if is_short_followup and prev_pipeline:
            primary_intent = prev_intent
            secondary_intents = []
            selected_pipeline = prev_pipeline
            multi_intent = False
            priority_rule = "follow_up_continuation"
            routing_reason = f"Pesan pendek pelanggan ({latest_msg!r}) adalah lanjutan dari percakapan sebelumnya."
            staff_handoff_notes = f"Pesan ini adalah konfirmasi/lanjutan. Pipeline tetap: {prev_pipeline}."
            _phone_match = re.search(r"\b(?:\+62|62|0)8\d{7,13}\b", ticket.get("message", ""))
            wa = _phone_match.group(0) if _phone_match else None
            return {
                "primary_intent": primary_intent, "secondary_intents": secondary_intents,
                "selected_pipeline": selected_pipeline, "multi_intent": multi_intent,
                "routing_reason": routing_reason, "priority_rule": priority_rule,
                "staff_handoff_notes": staff_handoff_notes,
                "customer_whatsapp": wa, "customer_name": None,
            }

        # Mixed multi-intent case (complaint + sales/renovation)
        if is_coding:
            primary_intent = "out_of_scope_coding"
            secondary_intents = []
            selected_pipeline = "support"
            multi_intent = False
            priority_rule = "out_of_scope_guard"
            routing_reason = "Pesan terbaru meminta bantuan coding yang berada di luar layanan QHome Mart."
            staff_handoff_notes = "Tolak permintaan coding secara sopan dan arahkan kembali ke produk, pesanan, renovasi, atau komplain QHome."
        elif latest_is_renovation and not latest_is_complaint and is_complaint:
            # DYNAMIC PIPELINE SWITCHING: latest message is a new order, old message was a complaint
            primary_intent = "renovation_quote"
            secondary_intents = ["damaged_item"]
            selected_pipeline = "renovation_quote"
            multi_intent = True
            priority_rule = "dynamic_pipeline_switch"
            routing_reason = "Pesan terbaru pelanggan adalah permintaan pesanan baru, dialihkan ke pipa renovasi."
            staff_handoff_notes = "Pelanggan sebelumnya memiliki komplain, tapi sekarang meminta penawaran baru."

        elif is_complaint and is_renovation:
            primary_intent = "damaged_item"
            secondary_intents = ["renovation_quote"]
            selected_pipeline = "support"
            multi_intent = True
            priority_rule = "complaint_first"
            routing_reason = "Pelanggan mengajukan keluhan barang pecah/rusak sekaligus permintaan estimasi renovasi. Sesuai kebijakan QHome Mart, keluhan pelanggan diprioritaskan terlebih dahulu untuk menjaga kepercayaan."
            staff_handoff_notes = (
                "PENTING: Pelanggan mengeluhkan barang pecah (Keramik pecah/rusak). "
                "Staff wajib menangani proses klaim penggantian barang/retur terlebih dahulu secara empatik (JANGAN menawarkan sales/penjualan tambahan secara agresif saat komplain belum selesai). "
                "Setelah keluhan teratasi, bantu pelanggan dengan kebutuhan sekundernya untuk estimasi/order renovasi kamar mandi."
            )
        elif is_complaint:
            primary_intent = "damaged_item" if any(word in msg for word in ["pecah", "rusak", "retak"]) else "delivery_tracking"
            secondary_intents = []
            selected_pipeline = "support"
            multi_intent = False
            priority_rule = "standard_routing"
            routing_reason = "Keluhan atau masalah pengiriman barang terdeteksi. Dialihkan ke pipa support/after-sales."
            staff_handoff_notes = "Hubungi pelanggan untuk memproses keluhan barang rusak/terlambat sesuai SOP after-sales."
        elif is_renovation and not is_bulk and not is_advice:
            primary_intent = "renovation_quote"
            secondary_intents = []
            selected_pipeline = "renovation_quote"
            multi_intent = False
            priority_rule = "standard_routing"
            routing_reason = "Permintaan estimasi renovasi atau draf penawaran terdeteksi. Dialihkan ke pipa renovasi 7-agent."
            staff_handoff_notes = "Pelanggan membutuhkan estimasi material renovasi secara detail. Siapkan draf quotation untuk survey lokasi."
        elif is_bulk:
            primary_intent = "bulk_order_delivery"
            secondary_intents = []
            selected_pipeline = "support"
            multi_intent = False
            priority_rule = "standard_routing"
            routing_reason = "Permintaan order bahan bangunan dalam jumlah besar terdeteksi. Dialihkan ke pipa support untuk verifikasi manual logistik."
            staff_handoff_notes = "Pesanan grosir/bulk material bangunan. Hubungi pelanggan untuk validasi stok fisik, armada toko, dan biaya kirim."
        elif is_advice:
            primary_intent = "product_advice"
            secondary_intents = []
            selected_pipeline = "support"
            multi_intent = False
            priority_rule = "standard_routing"
            routing_reason = "Permintaan konsultasi rekomendasi produk terdeteksi. Dialihkan ke pipa support/after-sales."
            staff_handoff_notes = "Bantu pelanggan memilih produk cat anti-lembab/anti-jamur yang sesuai dengan kondisi dindingnya."

        # Contextual extraction of customer details
        phone = None
        phone_match = re.search(r"\b(?:\+62|62|0)8\d{7,13}\b", text)
        if phone_match:
            phone = phone_match.group(0)

        name = "Pelanggan"
        text_lower = text.lower()
        if "naya" in text_lower:
            name = "Naya"
        elif "lona" in text_lower:
            name = "Lona"
        elif "jalue" in text_lower:
            name = "Jalue"

        return {
            "primary_intent": primary_intent,
            "secondary_intents": secondary_intents,
            "selected_pipeline": selected_pipeline,
            "multi_intent": multi_intent,
            "routing_reason": routing_reason,
            "priority_rule": priority_rule,
            "staff_handoff_notes": staff_handoff_notes,
            "customer_whatsapp": phone,
            "customer_name": name if name != "Pelanggan" else None,
        }

    def _requirement_intake(self, text: str, ticket: dict[str, Any] | None = None) -> dict[str, Any]:
        ticket = ticket or {}
        is_bathroom = any(word in text for word in ["mandi", "tiling", "keramik", "bathroom", "closet", "shower"])
        is_room_renovation = "renovasi" in text and "mandi" not in text and any(word in text for word in ["kamar", "ruangan", "room"])
        is_paint = any(word in text for word in ["cat", "dinding", "lembab", "jamur", "tembok"])
        is_material_order = any(word in text for word in ["semen", "batu bata", "besi", "pasir"])
        delivery_quality_concern = any(word in text for word in ["jangan sampai", "saat tiba", "rusak lagi", "pecah lagi"])

        if is_material_order:
            project_type = "material_order"
            area = 0.0
            budget = 0
            cats = ["material_order"]
            missing = []
            if not self._has_contact(text):
                missing.append("nomor HP/WhatsApp aktif")
            if not any(word in text for word in ["jl", "jalan", "alamat", "bantul", "sleman", "yogyakarta"]):
                missing.append("alamat pengiriman lengkap")
            reasoning = "Pesan terbaru pelanggan adalah permintaan pemesanan material bangunan sehingga komplain lama hanya dipakai sebagai konteks handoff."
        elif is_room_renovation:
            project_type = "renovasi_kamar"
            area = 10.0
            budget = 3000000 if "3jt" in text or "3 juta" in text else 0
            cats = ["keramik", "cat", "lampu LED"]
            missing = ["ukuran kamar", "jenis pengerjaan yang diinginkan", "preferensi lantai/dinding/pencahayaan"]
            reasoning = "Pelanggan ingin renovasi kamar dan meminta arahan kebutuhan material dengan anggaran awal."
        elif is_bathroom:
            project_type = "kamar_mandi"
            area = 4.0
            budget = 2000000
            cats = ["keramik", "perekat keramik", "nat keramik", "shower", "closet"]
            missing = [
                "ukuran spesifik tinggi dinding (hanya luas lantai 2x2m yang diketahui)",
                "pilihan warna atau motif keramik",
                "apakah ada bongkaran closet lama"
            ]
            reasoning = "Pelanggan ingin merenovasi kamar mandi ukuran 2x2m dan mencari estimasi biaya keramik, perekat, closet, dan shower."
        elif is_paint:
            project_type = "dinding_lembab"
            area = 15.0
            budget = 1000000
            cats = ["cat", "waterproofing", "nat keramik"]
            missing = [
                "apakah ada rembesan air aktif dari luar dinding",
                "warna cat akhir yang diinginkan",
                "lokasi dinding interior atau eksterior"
            ]
            reasoning = "Pelanggan berkonsultasi mengenai solusi cat untuk dinding rumah yang lembab dan sedikit berjamur."
        else:
            project_type = "general"
            area = 10.0
            budget = 1500000
            cats = ["keramik", "cat"]
            missing = ["kebutuhan ruangan atau detail renovasi"]
            reasoning = "Klasifikasi umum untuk pertanyaan konsultasi bahan bangunan."

        # Extract WhatsApp if exists
        phone = ticket.get("customer_whatsapp")
        match = re.search(r"\b(?:\+62|62|0)8\d{7,13}\b", text)
        if match:
            phone = match.group(0)

        # Extract customer name
        name = "Pelanggan"
        if "jalue" in text:
            name = "Jalue"

        return {
            "project_type": project_type,
            "area_m2": area,
            "budget": budget,
            "categories_needed": cats,
            "requested_materials": self._extract_material_items(text) if is_material_order else [],
            "delivery_quality_concern": delivery_quality_concern,
            "customer_name": name,
            "customer_whatsapp": phone,
            "location": "Bantul, Yogyakarta" if "bantul" in text else None,
            "missing_information": missing,
            "reasoning": reasoning,
        }

    def _product_retrieval(self, outputs: dict[str, Any], catalog: list[dict[str, Any]]) -> dict[str, Any]:
        intake = outputs.get("requirement_intake", {})
        proj = intake.get("project_type", "general")

        recommended = []
        if proj == "material_order":
            material_map = {
                "semen": ("QH-MAT-SEMEN", "Semen Portland 50kg", "sak", 65000, "Material utama untuk pekerjaan bangunan; stok dan ongkir wajib divalidasi staff."),
                "batu bata": ("QH-MAT-BATA", "Batu Bata Merah", "buah", 1200, "Material dinding dalam jumlah besar; perlu validasi armada dan kapasitas pengiriman."),
                "besi": ("QH-MAT-BESI", "Besi Beton", "batang", 52000, "Material struktur; ukuran diameter perlu dikonfirmasi staff sebelum finalisasi."),
                "pasir": ("QH-MAT-PASIR", "Pasir Bangunan", "m3", 285000, "Material curah; biaya kirim tergantung jarak dan volume."),
            }
            requested = intake.get("requested_materials") or []
            for item in requested:
                key = item.get("material", "")
                sku, name, unit, price, reason = material_map.get(
                    key,
                    (f"QH-MAT-{key.upper().replace(' ', '-')}", key.title(), item.get("unit", "unit"), 0, "Material perlu dikonfirmasi staff."),
                )
                recommended.append({
                    "sku": sku,
                    "name": name,
                    "unit": unit,
                    "unit_price": price,
                    "requested_qty": item.get("qty", 1),
                    "selection_reason": reason,
                })
        elif proj == "kamar_mandi":
            items = [
                ("QH-KRM-001", "Keramik Lantai Anti Slip 40x40", "box", 85000, "Keramik bertekstur kasar/anti slip sangat aman untuk lantai kamar mandi basah."),
                ("QH-ADH-002", "Perekat Keramik Area Basah 25kg", "sak", 89000, "Perekat premium khusus area terendam air agar keramik tidak popping/lepas."),
                ("QH-GRT-001", "Nat Keramik Anti Jamur 1kg", "pack", 26000, "Pengisi sela keramik anti air dan anti jamur menjaga kebersihan nat."),
                ("QH-SHW-001", "Hand Shower Set Chrome", "set", 185000, "Shower mandi dengan hand-set modern berlapis chrome tahan karat."),
                ("QH-CLS-001", "Closet Duduk Dual Flush", "pcs", 875000, "Closet duduk hemat air dengan mekanisme dual flush berkualitas.")
            ]
        elif proj == "dinding_lembab":
            items = [
                ("QH-CAT-003", "Alkali Resisting Primer 4L", "pail", 138000, "Cat dasar pelapis alkali untuk menahan kelembaban semen baru/dinding lembab."),
                ("QH-WTP-001", "Waterproofing Cement Base 4kg", "pail", 125000, "Semen pelapis anti bocor untuk memblokir rembesan air aktif."),
                ("QH-CAT-001", "Cat Interior Anti Jamur 5L", "pail", 165000, "Cat akhir anti jamur premium untuk memperindah ruangan interior.")
            ]
        else:
            items = [
                ("QH-KRM-003", "Keramik Ruang Tamu Matte 60x60", "box", 145000, "Keramik lebar dengan hasil matte elegan cocok untuk ruang tamu."),
                ("QH-CAT-001", "Cat Interior Anti Jamur 5L", "pail", 165000, "Cat anti jamur berkualitas tinggi.")
            ]

        if proj != "material_order":
            for sku, name, unit, price, reason in items:
                # Try to double check catalog to keep prices matched
                catalog_match = next((p for p in catalog if p["sku"] == sku), None)
                if catalog_match:
                    price = catalog_match["price"]
                    name = catalog_match["name"]
                    unit = catalog_match["unit"]
                recommended.append({
                    "sku": sku,
                    "name": name,
                    "unit": unit,
                    "unit_price": price,
                    "selection_reason": reason
                })

        return {
            "recommended_products": recommended,
            "reasoning": f"Produk dipilih secara presisi dari database produk untuk mencukupi kebutuhan proyek {proj}."
        }

    def _inventory_snapshot(self, snapshots: list[dict[str, Any]]) -> dict[str, Any]:
        alerts = []
        status_ok = True

        for snap in snapshots:
            qty = snap.get("stock_qty", 0)
            status = snap.get("stock_status", "")
            name = snap.get("name", "")
            if qty == 0 or "unavailable" in status:
                alerts.append(f"STOK HABIS: {name} ({snap.get('sku')}) saat ini kosong di cabang demo.")
                status_ok = False
            elif qty < 10 or "low_stock" in status:
                alerts.append(f"STOK TERBATAS: {name} ({snap.get('sku')}) tersisa {qty} {snap.get('unit', 'unit')}.")

        alerts.append("Semua informasi stok adalah snapshot data demo dan wajib dikonfirmasi ulang oleh staff logistik.")

        return {
            "inventory_alerts": alerts,
            "stock_status_ok": status_ok,
            "reasoning": "Pengecekan snapshot persediaan menunjukkan ketersediaan sebagian besar produk dengan beberapa catatan stok terbatas."
        }

    def _quantity_estimator(self, draft_quantities: list[dict[str, Any]], outputs: dict[str, Any]) -> dict[str, Any]:
        intake = outputs.get("requirement_intake", {})
        area = intake.get("area_m2", 10.0)

        estimations = []
        for dq in draft_quantities:
            estimations.append({
                "sku": dq["sku"],
                "name": dq["name"],
                "estimated_qty": dq["estimated_qty"],
                "unit": dq["unit"],
                "estimation_math": dq["estimation_math"]
            })

        return {
            "estimations": estimations,
            "reasoning": f"Kuantitas material dihitung berdasarkan luas pengerjaan {area} m² ditambah faktor pembuangan 10% dan diselaraskan dengan kebutuhan standard."
        }

    def _quote_builder(self, calculated_draft: dict[str, Any], outputs: dict[str, Any]) -> dict[str, Any]:
        intake = outputs.get("requirement_intake", {})
        proj = intake.get("project_type", "general")
        
        items = calculated_draft.get("items", [])
        total = calculated_draft.get("estimated_total", 0)
        budget = calculated_draft.get("budget")
        status = calculated_draft.get("budget_status", "unknown_budget")

        quote_code = f"QTE-M{int(total)%100000:04d}"
        
        notes = (
            "1. Rincian di atas merupakan draft estimasi quotation awal.\n"
            "2. Harga belum termasuk diskon proyek, ongkos kirim, dan jasa tukang.\n"
            "3. Ketersediaan stok dan harga final wajib diverifikasi oleh staff toko sebelum pembayaran.\n"
            "4. Penawaran berlaku selama 7 hari kalender."
        )

        return {
            "quote_code": quote_code,
            "estimated_total": total,
            "budget": budget,
            "budget_status": status,
            "line_items": items,
            "notes": notes,
            "reasoning": f"Draft penawaran harga disusun secara sistematis dengan total {total} Rupiah, diselaraskan dengan anggaran customer."
        }

    def _risk_policy_verifier(self, draft_quote: dict[str, Any], outputs: dict[str, Any], policies: list[dict[str, Any]]) -> dict[str, Any]:
        intake = outputs.get("requirement_intake", {})
        whatsapp = intake.get("customer_whatsapp")
        budget_status = draft_quote.get("budget_status")
        missing_info = intake.get("missing_information", [])

        issues = []
        if not whatsapp:
            issues.append("Nomor WhatsApp pelanggan belum terdaftar (POL-CONTACT-CONSENT).")
        if budget_status == "over_budget":
            issues.append("Total biaya draft quotation melebihi budget pelanggan.")
        
        # Append missing items to issues to ensure consistency
        for item in missing_info:
            issues.append(f"Informasi penting masih kurang: {item}")
        
        issues.append("Perlu validasi jenis permukaan semen dan survey lapangan sebelum pengerjaan renovasi.")

        debate_log_lines = [
            "RISK AUDIT PASSED WITH NOTES:",
            "- Kebijakan POL-STOCK-SNAPSHOT terpenuhi: Catatan kaki mencantumkan bahwa stok bersifat snapshot.",
            "- Kebijakan POL-PRICE-ESTIMATE terpenuhi: Draft quotation menyebutkan harga tidak bersifat final."
        ]
        if not whatsapp:
            debate_log_lines.append("- Peringatan: Nomor WhatsApp belum dimasukkan. Kami wajib menanyakan kontak secara halus kepada pelanggan.")
        else:
            debate_log_lines.append(f"- Kebijakan POL-CONTACT-CONSENT terpenuhi: Nomor WhatsApp ({whatsapp}) telah dicatat secara sah.")
            
        if missing_info:
            debate_log_lines.append(f"- Peringatan: {', '.join(missing_info)} masih kurang untuk estimasi final (POL-RENOVATION-RISK).")
            
        debate_log = "\n".join(debate_log_lines)

        return {
            "risk_level": "medium" if issues else "low",
            "issues_found": issues,
            "revision_required": False,  # Keep single pass in mock mode
            "criticism_debate_log": debate_log,
            "reasoning": "Semua poin kepatuhan kebijakan telah diaudit. Penjualan aman diteruskan ke customer dengan catatan klarifikasi kontak."
        }

    def _staff_handoff_response(self, outputs: dict[str, Any]) -> dict[str, Any]:
        intake = outputs.get("requirement_intake", {})
        quote = outputs.get("quote_builder", {})
        verifier = outputs.get("risk_policy_verifier", {})
        
        proj = intake.get("project_type", "renovasi")
        whatsapp = intake.get("customer_whatsapp")
        total = quote.get("estimated_total", 0)

        # Formulate safe response
        if proj == "material_order":
            items = quote.get("line_items", [])
            item_text = ", ".join(f"{item.get('name')} {item.get('qty')} {item.get('unit')}" for item in items) or "material bangunan yang diminta"
            quality_note = ""
            if intake.get("delivery_quality_concern"):
                quality_note = (
                    "\n\nSaya paham kekhawatiran Anda soal barang rusak saat tiba. Saya tandai ini sebagai catatan penting untuk staff logistik agar pengecekan fisik, penataan muatan, dan proses pengiriman diperhatikan lebih hati-hati. "
                    "Kondisi final tetap perlu dikonfirmasi staff bersama armada pengiriman."
                )
            follow_up = (
                f"Nomor WhatsApp {whatsapp} sudah tercatat, sehingga staff QHome Mart bisa menghubungi Anda untuk validasi stok, ongkir, dan jadwal kirim."
                if whatsapp
                else "Boleh kirim nomor HP atau WhatsApp aktif serta alamat lengkap pengiriman agar staff QHome Mart bisa menindaklanjuti pesanan ini?"
            )
            reply = (
                f"Halo {intake.get('customer_name', 'Kak')}, pesanan {item_text} sudah saya catat.\n\n"
                f"Estimasi awal dari katalog demo adalah Rp {total:,}. Angka ini belum termasuk validasi stok, ongkir, kapasitas armada, dan jadwal kirim dari staff toko.\n\n"
                f"{follow_up}{quality_note}"
            )
        elif proj == "kamar_mandi":
            reply = (
                f"Halo {intake.get('customer_name', 'Kak')}, saya telah membantu menyusun draft estimasi awal kebutuhan material untuk renovasi kamar mandi Anda (2x2m).\n\n"
                f"Total estimasi sementara adalah Rp {total:,} (menggunakan keramik anti slip, perekat area basah, nat anti jamur, closet duduk, dan shower set).\n\n"
                "Catatan penting:\n"
                "- Estimasi ini bersifat draf awal. Warna, motif, ketersediaan stok, dan ongkir akhir perlu dipastikan langsung oleh staff logistik kami.\n"
                "- Kami merekomendasikan survey lapangan oleh tukang kami agar ukuran ruangan dan kebutuhan fitting pipa air bersih terukur akurat.\n\n"
                + (f"Nomor WhatsApp {whatsapp} sudah tercatat untuk follow-up staff." if whatsapp else "Untuk melanjutkan pemesanan dan verifikasi stok, bolehkah saya meminta nomor HP atau WhatsApp aktif Anda?")
            )
        elif proj == "renovasi_kamar":
            reply = (
                f"Halo {intake.get('customer_name', 'Kak')}, untuk renovasi kamar dengan budget sekitar Rp {intake.get('budget', 0):,}, kebutuhan awal yang biasanya perlu disiapkan mencakup lantai/keramik atau vinyl, cat dinding, pencahayaan, dan material pendukung sesuai kondisi kamar.\n\n"
                f"Estimasi awal katalog demo dari item rekomendasi saat ini adalah Rp {total:,}. Angka ini belum final karena ukuran kamar dan jenis pengerjaan belum lengkap.\n\n"
                "Catatan penting:\n"
                "- Mohon siapkan ukuran kamar dan prioritas pengerjaan, misalnya lantai, cat, plafon, lampu, atau furniture.\n"
                "- Harga, stok, ongkir, dan kebutuhan tukang perlu divalidasi staff setelah detail ruangan lengkap.\n\n"
                + (f"Nomor WhatsApp {whatsapp} sudah tercatat untuk follow-up staff." if whatsapp else "Boleh kirim nomor WhatsApp aktif agar staff kami bisa bantu lanjutkan estimasi?")
            )
        elif proj == "dinding_lembab":
            reply = (
                f"Halo {intake.get('customer_name', 'Kak')}, untuk solusi dinding rumah yang lembab dan berjamur, berikut adalah draf rekomendasi material pengerjaan:\n\n"
                f"Total estimasi sementara adalah Rp {total:,} (menggunakan Alkali Primer tahan lembab, pelapis semen waterproofing, dan cat interior anti jamur).\n\n"
                "Catatan penting:\n"
                "- Agar cat awet, pastikan sumber rembesan air aktif dibalik dinding sudah diperbaiki terlebih dahulu.\n"
                "- Harga dan persediaan stok di cabang demo bersifat snapshot sementara dan wajib divalidasi staff.\n\n"
                + (f"Nomor WhatsApp {whatsapp} sudah tercatat untuk follow-up staff." if whatsapp else "Boleh minta nomor WhatsApp aktif agar staff toko kami bisa membantu menjadwalkan pengecekan stok atau konsultasi produk lebih lanjut?")
            )
        else:
            reply = (
                f"Halo {intake.get('customer_name', 'Kak')}, berikut draf estimasi awal material pengerjaan proyek Anda:\n\n"
                f"Total estimasi adalah Rp {total:,} berdasarkan harga produk katalog demo kami.\n\n"
                "Harap dicatat bahwa harga ini adalah estimasi awal dan ketersediaan stok harus divalidasi staff.\n\n"
                + (f"Nomor WhatsApp {whatsapp} sudah tercatat untuk follow-up staff." if whatsapp else "Boleh tinggalkan nomor WhatsApp aktif agar staff kami dapat membantu Anda memproses estimasi ini?")
            )

        summary = (
            f"Pelanggan tertarik mengajukan quotation proyek {proj} (Luas: {intake.get('area_m2')} m²). "
            f"Total estimasi draft: Rp {total:,}. Anggaran pelanggan: Rp {intake.get('budget', 0):,}. "
            f"Kontak WhatsApp: {whatsapp or 'Belum ada (wajib ditanyakan)'}."
        )

        if proj == "material_order":
            steps = [
                "Validasi stok semen/batu bata/material sesuai jumlah pesanan terbaru.",
                "Hitung ongkir dan kapasitas armada berdasarkan alamat pengiriman.",
                "Pastikan prosedur loading dan pengiriman mengurangi risiko barang pecah/rusak.",
                "Hubungi pelanggan untuk konfirmasi metode pembayaran sebelum diproses.",
            ]
        elif whatsapp:
            steps = [
                f"Hubungi pelanggan melalui WhatsApp di nomor {whatsapp} untuk mengonfirmasi detail spesifik renovasi.",
                "Validasi fisik ketersediaan stok keramik dan closet di QHome Mart Demo Branch.",
                "Hitung biaya kirim semen/perekat keramik berbobot berat menggunakan armada toko.",
                "Jadwalkan kunjungan survey tukang jika pelanggan meminta instalasi closet/shower."
            ]
        else:
            steps = [
                "Hubungi pelanggan untuk verifikasi kontak WhatsApp dan alamat pengiriman.",
                "Validasi fisik ketersediaan stok keramik dan closet di QHome Mart Demo Branch.",
                "Hitung biaya kirim semen/perekat keramik berbobot berat menggunakan armada toko.",
                "Jadwalkan kunjungan survey tukang jika pelanggan meminta instalasi closet/shower."
            ]

        return {
            "customer_reply": reply,
            "staff_summary": summary,
            "internal_next_steps": steps,
            "contact_required": not bool(whatsapp),
            "requested_contact_fields": ["customer_whatsapp"] if not whatsapp else [],
            "reasoning": "Jawaban final dirumuskan secara aman dengan mencantumkan batasan kebijakan dan meminta kontak follow-up."
        }

    # --- 5-AGENT FALLBACK CODE (PRESERVED FOR BACKWARD COMPATIBILITY) ---

    def _intent(self, text: str) -> dict[str, Any]:
        if is_coding_request(text):
            intent = "out_of_scope_coding"
            category = "out_of_scope"
        elif any(word in text for word in ["cat", "dinding", "lembab", "jamur", "rekomendasi", "pakai apa"]):
            intent = "product_advice"
            category = "product_consultation"
        elif self._is_bulk_order(text):
            intent = "bulk_order_delivery"
            category = "sales_order"
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

        # Contextual extraction of customer details
        phone = None
        phone_match = re.search(r"\b(?:\+62|62|0)8\d{7,13}\b", text)
        if phone_match:
            phone = phone_match.group(0)

        name = "Pelanggan"
        text_lower = text.lower()
        if "naya" in text_lower:
            name = "Naya"
        elif "lona" in text_lower:
            name = "Lona"
        elif "jalue" in text_lower:
            name = "Jalue"

        return {
            "intent": intent,
            "category": category,
            "confidence": 0.84,
            "summary": "Pelanggan membutuhkan bantuan QHome Mart terkait layanan atau rekomendasi produk.",
            "missing_information": self._missing_information(intent, text),
            "reasoning": "Kata kunci pada pesan pelanggan dipetakan ke kategori layanan atau konsultasi produk yang paling relevan.",
            "customer_whatsapp": phone,
            "customer_name": name if name != "Pelanggan" else None,
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
            if intent == "bulk_order_delivery" and policy.get("id") == "POL-BULK-ORDER-DELIVERY":
                score += 5
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
        elif intent == "bulk_order_delivery":
            missing = outputs.get("intent_classifier", {}).get("missing_information", [])
            if missing:
                actions = [
                    "Minta nomor HP/WhatsApp aktif sebelum diteruskan ke staff toko.",
                    "Catat alamat, daftar item, jumlah, dan metode pembayaran yang sudah diberikan.",
                    "Staff perlu validasi stok, ongkir, armada, dan estimasi tiba sebelum konfirmasi order.",
                ]
            else:
                actions = [
                    "Teruskan ringkasan pesanan ke staff toko/logistik.",
                    "Validasi stok semen, batu bata, dan besi sesuai jumlah.",
                    "Hitung ongkir, armada, estimasi tiba, lalu hubungi pelanggan melalui kontak yang diberikan.",
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
        if intent == "out_of_scope_coding":
            actions = [
                "Tolak permintaan coding secara sopan.",
                "Jelaskan bahwa chat ini hanya menangani produk, pesanan, pengiriman, renovasi, dan komplain QHome Mart.",
                "Ajak pelanggan mengirim kebutuhan yang relevan dengan layanan QHome jika ada.",
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
        if intent == "out_of_scope_coding":
            return {
                "priority": "low",
                "escalate": False,
                "escalation_team": None,
                "sla_recommendation": "No staff escalation needed",
                "business_risk": "Risiko rendah: permintaan berada di luar ruang lingkup layanan QHome Mart.",
                "reasoning": "Permintaan coding tidak relevan dengan layanan customer support QHome Mart.",
            }
        if intent == "bulk_order_delivery":
            return {
                "priority": "high" if any(word in text for word in ["saat itu juga", "sekarang", "hari ini"]) else "medium",
                "escalate": True,
                "escalation_team": "sales_logistics",
                "sla_recommendation": "Staff follow-up within 30 minutes during store operating hours",
                "business_risk": "Potensi order bernilai besar, tetapi perlu validasi stok, armada, ongkir, dan kontak pelanggan sebelum diproses.",
                "reasoning": "Pesanan bahan bangunan jumlah besar harus diteruskan ke staff toko/logistik untuk konfirmasi operasional.",
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
                "Setelah permukaan bersih dan kering, gunakan alkali resisting primer or wall sealer anti lembab, "
                "lalu pilih cat anti jamur yang sesuai area indoor/outdoor. "
                "Boleh info dindingnya di dalam/luar rumah dan lembabnya berupa jamur, noda, atau rembes?"
            )
        elif intent.get("intent") == "out_of_scope_coding":
            response = (
                f"Maaf {ticket.get('customer_name', 'Kak')}, saya tidak bisa membantu membuat kode, script, bot, atau otomasi di chat QHome Mart ini. "
                "Saya bisa membantu hal yang terkait layanan QHome seperti rekomendasi produk bangunan, cek kebutuhan material, estimasi awal renovasi, pesanan, pengiriman, atau komplain barang. "
                "Kalau ada kebutuhan terkait produk atau pesanan QHome, kirimkan detailnya dan saya bantu arahkan."
            )
        elif intent.get("intent") == "bulk_order_delivery":
            if missing:
                response = (
                    f"Terima kasih {ticket.get('customer_name', 'Kak')}, detail pesanan dan alamat sudah saya catat. "
                    "Agar staff toko bisa menghubungi Anda untuk konfirmasi stok, ongkir, armada, estimasi tiba, dan instruksi transfer BNI, "
                    "mohon berikan nomor HP atau WhatsApp aktif. Estimasi pengiriman belum bisa dipastikan sebelum staff mengecek stok dan jadwal armada."
                )
            else:
                response = (
                    f"Terima kasih {ticket.get('customer_name', 'Kak')}, data pesanan dan kontak sudah lengkap. "
                    "Saya teruskan ke staff toko/logistik untuk validasi stok, ongkir, armada, dan estimasi tiba. "
                    "Staff akan menghubungi Anda melalui nomor HP/WhatsApp yang diberikan sebelum pembayaran diproses."
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
        if intent == "bulk_order_delivery":
            missing = []
            if not self._has_contact(text):
                missing.append("nomor HP/WhatsApp aktif")
            if not any(word in text for word in ["jl", "jalan", "alamat", "bantul", "sleman", "yogyakarta"]):
                missing.append("alamat pengiriman lengkap")
            if not any(word in text for word in ["semen", "batu", "bata", "besi", "pasir", "cat", "keramik"]):
                missing.append("daftar item dan jumlah")
            if not any(word in text for word in ["transfer", "cash", "tunai", "bni", "bca", "mandiri", "bri"]):
                missing.append("metode pembayaran")
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

    def _extract_material_items(self, text: str) -> list[dict[str, Any]]:
        patterns = [
            ("semen", r"semen", "sak"),
            ("batu bata", r"batu\s+bata", "buah"),
            ("besi", r"besi", "batang"),
            ("pasir", r"pasir", "m3"),
        ]
        items = []
        for material, material_pattern, unit in patterns:
            match = re.search(rf"{material_pattern}\D{{0,30}}(\d+)", text)
            if not match:
                match = re.search(rf"(\d+)\s*(?:pcs|buah|sak|pack|batang|m3)?\D{{0,30}}{material_pattern}", text)
            if match:
                items.append({"material": material, "qty": int(match.group(1)), "unit": unit})
        if not items:
            for material, material_pattern, unit in patterns:
                if re.search(material_pattern, text):
                    items.append({"material": material, "qty": 1, "unit": unit})
        return items

    def _is_bulk_order(self, text: str) -> bool:
        if "pesanan qh-" in text:
            return False
        order_words = ["memesan", "mau pesan", "ingin pesan", "saya pesan", "order", "beli", "pembayaran", "transfer"]
        material_words = ["bahan bangunan", "semen", "batu bata", "besi", "pasir", "keramik", "dikirim"]
        return any(word in text for word in order_words) and any(word in text for word in material_words)

    def _has_contact(self, text: str) -> bool:
        if re.search(r"\b(?:\+62|62|0)8\d{7,13}\b", text):
            return True
        contact_phrases = [
            "nomor hp",
            "no hp",
            "nomor wa",
            "no wa",
            "whatsapp saya",
            "wa saya",
            "telepon saya",
            "telp saya",
            "hubungi saya",
        ]
        return any(phrase in text for phrase in contact_phrases)
