# Kesesuaian Kriteria Penilaian (Judging Criteria Mapping)

Dokumen ini memaparkan implementasi teknis QHome AI Agent berdasarkan kriteria penilaian kompetisi AI Agent Competition 2026.

---

## 1. Routing & Orchestration (LLM-Powered Multi-Intent Router)

- **Routing Dinamis**: Menggunakan **Hybrid Triage Router Agent** berbasis LLM. Router menganalisis pesan terbaru pelanggan untuk menentukan pipeline terbaik (support atau renovation_quote).
- **Complaint-First Priority**: Jika satu pesan mengandung komplain dan pesanan secara bersamaan, sistem memprioritaskan komplain melalui pipeline `support`. Pesanan dicatat di `secondary_intents` untuk tindak lanjut staf.
- **Dynamic Pipeline Switching**: Jika pesan terbaru pelanggan adalah pesanan baru (tanpa komplain baru), sistem secara otomatis berpindah ke pipeline `renovation_quote` meskipun percakapan sebelumnya adalah komplain.
- **Anti-Looping**: Agen `qa_final_response` dan `staff_handoff_response` diinstruksikan agar tidak mengulang jawaban sebelumnya pada pesan follow-up singkat.
- **Latest-Message-First Classification**: `intent_classifier` mengklasifikasi intent berdasarkan pesan terbaru saja, bukan seluruh riwayat — mencegah konteks lama mendominasi routing.
- **Secondary Intent Capture**: Kebutuhan sekunder tetap ditangkap di `secondary_intents` dan `staff_handoff_notes` untuk tindak lanjut staf setelah komplain selesai.

---

## 2. Kolaborasi Multi-Agent (13 Agen Total)

Dua jalur pipeline yang dioperasikan bersama satu Hybrid Triage Router:

**5-Agent Support Pipeline:**

```text
Intent Classifier → Knowledge Retrieval → Solution Planner → Priority & Escalation → QA Final Response
```

**7-Agent Renovation & Quotation Pipeline:**

```text
Requirement Intake → Product Retrieval → Inventory Snapshot → Quantity Estimator → Quote Builder → Risk & Policy Verifier → Staff Handoff Response
```

Fitur kolaborasi khusus:
- **Shared State via RunState**: Output setiap agen direkam dan tersedia untuk agen berikutnya.
- **Quantity Estimator**: Kalkulasi deterministik Python (bukan tebakan LLM) dengan waste allowance +10% untuk tile dan coverage formula untuk cat.
- **Critic Debate Loop**: Risk & Policy Verifier dapat memicu revisi Quote Builder jika terdeteksi masalah kelengkapan data atau inkonsistensi budget.

---

## 3. Implementasi Sistem Bisnis

- **SQLite Persisten**: Menyimpan riwayat tiket, riwayat agen (`agent_runs`, `agent_steps`), quotation, dan katalog produk secara lokal.
- **Staff Dashboard Live**: Visualisasi eksekusi agen step-by-step, highlight WhatsApp pelanggan, detail routing triage, Support Case Packet.
- **Support Case Packet**: Instruksi operasional terstruktur untuk staf — termasuk `staff_next_action`, `sla_suggestion`, dan `escalation_team` — yang disesuaikan berdasarkan ketersediaan kontak pelanggan.
- **Product Alias Resolver**: Memetakan nama informal pelanggan (misal "hebel", "granit polished") ke SKU katalog yang benar.
- **Skema Data Relasional**: 9 tabel yang mendukung integrasi nyata dengan sistem logistik/inventaris.

---

## 4. Reproducibility & Pengujian

- **Unit & Integration Tests**: 56 test (`python3 -m unittest discover -s tests`) yang mencakup routing, multi-intent, dynamic switching, kalkulator, SQLite persistence, support case packet, alias resolver, dan edge case. **Hasil: 56/56 OK.**
- **Eval Suite (100-Point Rubric)**: 5 skenario golden otomatis memvalidasi akurasi routing (30 poin), keamanan/compliance (40 poin), dan kualitas output packet/quotation (30 poin). **Hasil: 5/5 PASS, skor rata-rata 99/100.**
- **Quality Gate Scripts**: `scripts/run_full_quality_check.py`, `scripts/smoke_linux.sh`, `scripts/smoke_windows.bat`, `scripts/smoke_windows.ps1` — siap dijalankan di semua OS.
- **Mock Mode**: Simulasi deterministik yang berjalan sepenuhnya lokal tanpa API key — memastikan seluruh workflow dapat dievaluasi langsung oleh juri.
- **Live Mode**: Mendukung SumoPod AI API (OpenAI-compatible) untuk demo dengan LLM sesungguhnya.
- **Release Package**: `python scripts/build_release.py` menghasilkan ZIP portabel yang bisa langsung diekstrak dan dijalankan.

---

## 5. Zero External Dependencies

Project ini hanya memerlukan:
- **Python 3.11+** (stdlib saja)
- **SQLite** (sudah bawaan Python)
- **API Key** (opsional — hanya untuk Live mode)

Tidak ada `pip install` yang diperlukan untuk menjalankan sistem.
