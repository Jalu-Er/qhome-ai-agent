# Architecture & Orchestration System

QHome AI Agent menggunakan arsitektur **Hybrid Orchestration & Multi-Agent System** berbasis SQLite dan LLM.

![System Architecture](system_architecture.png)

---

## 1. Alur Kerja Orchestrator

Setiap pesan pelanggan masuk ke **Hybrid Triage Router Agent** yang menganalisis intent dan menentukan pipeline:

```text
[Pelanggan kirim pesan]
        ↓
[Triage Router Agent] ← LLM menganalisis pesan terbaru + riwayat
        ↓
    ┌───────────────────────┐
    │ selected_pipeline?    │
    └───────┬───────────────┘
            │
    ┌───────┴───────┐
    ▼               ▼
[SUPPORT]     [RENOVATION_QUOTE]
 5-Agent         7-Agent
    │               │
    ▼               ▼
[Customer Reply + SQLite + Staff Dashboard]
```

---

## 2. Triage Router Agent — Output Format

Router menghasilkan JSON terstruktur:

```json
{
  "primary_intent": "damaged_item",
  "secondary_intents": ["renovation_quote"],
  "selected_pipeline": "support",
  "multi_intent": true,
  "routing_reason": "Pelanggan mengeluhkan barang pecah, komplain diprioritaskan.",
  "priority_rule": "complaint_first",
  "staff_handoff_notes": "Tangani klaim keramik pecah terlebih dahulu.",
  "customer_whatsapp": "08123456789",
  "customer_name": "Naya"
}
```

---

## 3. Business Rules

### Complaint-First Priority
Jika satu pesan mengandung komplain DAN pesanan → pipeline `support`, pesanan dicatat di `secondary_intents`.

### Dynamic Pipeline Switching
Jika pesan terbaru pelanggan adalah pesanan baru (tanpa komplain baru) → otomatis switch ke pipeline `renovation_quote`, meskipun percakapan awalnya adalah komplain.

![Dynamic Pipeline Switching](pipeline_switching.png)

### Anti-Looping
Agen `qa_final_response` dan `staff_handoff_response` diinstruksikan agar tidak mengulang ringkasan sebelumnya pada pesan follow-up.

### Latest-Message-First Classification
`intent_classifier` mengklasifikasi intent berdasarkan pesan terbaru saja, bukan seluruh riwayat.

---

## 4. Pipeline 1: Support (5-Agent)

| # | Agen | Fungsi |
|---|------|--------|
| 1 | Intent Classifier | Klasifikasi intent & deteksi data yang kurang |
| 2 | Knowledge Retrieval | Cari kebijakan, FAQ, dan panduan produk |
| 3 | Solution Planner | Rancang rencana penyelesaian masalah |
| 4 | Priority & Escalation | Nilai prioritas, risiko, SLA eskalasi |
| 5 | QA & Final Response | Susun respons final + langkah internal staf |

---

## 5. Pipeline 2: Renovation & Quotation (7-Agent)

| # | Agen | Fungsi |
|---|------|--------|
| 1 | Requirement Intake | Ekstrak area (m²), budget, kategori proyek |
| 2 | Product Retrieval | Pilih SKU dari katalog SQLite |
| 3 | Inventory Snapshot | Cek ketersediaan stok cabang |
| 4 | Quantity Estimator | Kalkulasi deterministik (waste +10%) |
| 5 | Quote Builder | Susun draf penawaran `QTE-XXXX` |
| 6 | Risk & Policy Verifier | Audit kepatuhan kebijakan, loop revisi |
| 7 | Staff Handoff Response | Rangkuman tugas staf + respons pelanggan |

---

## 6. Shared State & SQLite

Semua agen berkomunikasi melalui `RunState` yang merekam setiap langkah secara terurut. Database SQLite (`data/qhome_agent.db`) mencakup:

| Tabel | Fungsi |
|-------|--------|
| `products` | Katalog material bangunan |
| `inventory_snapshots` | Snapshot stok fisik per SKU |
| `tickets` | Tiket operasional pelanggan |
| `messages` | Riwayat pesan per tiket |
| `quotes` & `quote_items` | Draf penawaran + rincian item |
| `agent_runs` & `agent_steps` | Metadata dan I/O per agen |
| `policies` | Kebijakan guardrail (stok, harga, kontak) |

---

## 7. Logging & Evaluasi

Setiap eksekusi workflow menghasilkan:
- `runs/<run_id>/interactions.jsonl` — Log mentah interaksi per-agen
- `runs/<run_id>/final_output.json` — Output lengkap untuk dashboard
- `runs/<run_id>/report.md` — Laporan markdown untuk presentasi

Evaluasi otomatis: `python3 run.py eval` — 7 skenario, skor rata-rata 28.29/30.
