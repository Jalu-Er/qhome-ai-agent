# Kesesuaian Kriteria Penilaian (Evaluation Fit)

Dokumen ini memaparkan implementasi teknis QHome AI Agent berdasarkan kriteria penilaian kompetisi.

---

## 1. Routing & Orchestration (LLM-Powered Multi-Intent Router)

- **Routing Dinamis**: Menggunakan **Triage Router Agent** berbasis LLM. Router menganalisis pesan terbaru pelanggan untuk menentukan pipeline terbaik.
- **Complaint-First Priority**: Jika satu pesan mengandung komplain dan pesanan secara bersamaan, sistem memprioritaskan komplain melalui pipeline `support`.
- **Dynamic Pipeline Switching**: Jika pesan terbaru pelanggan adalah pesanan baru (tanpa komplain baru), sistem secara otomatis berpindah ke pipeline `renovation_quote` — tanpa perlu intervensi staf.
- **Anti-Looping**: Agen respons diinstruksikan agar tidak mengulang jawaban sebelumnya pada pesan follow-up sederhana.
- **Secondary Intent Capture**: Kebutuhan sekunder tetap ditangkap di `secondary_intents` dan `staff_handoff_notes` untuk tindak lanjut staf.

---

## 2. Kolaborasi Multi-Agent (13 Agen Total)

Dua jalur pipeline optimal:

**5-Agent Support Pipeline:**
Intent Classifier → Knowledge Retrieval → Solution Planner → Priority & Escalation → QA & Final Response

**7-Agent Renovation & Quotation Pipeline:**
Requirement Intake → Product Retrieval → Inventory Snapshot → Quantity Estimator → Quote Builder → Risk & Policy Verifier → Staff Handoff Response

Fitur khusus:
- **Quantity Estimator**: Kalkulasi deterministik Python (bukan tebakan LLM) dengan waste allowance +10%.
- **Critic Debate Loop**: Risk & Policy Verifier dapat memicu revisi Quote Builder jika terdeteksi masalah.

---

## 3. Implementasi Sistem Bisnis

- **SQLite Persisten**: Menyimpan riwayat tiket, riwayat agen (`agent_runs`, `agent_steps`), quotation, dan katalog produk.
- **Staff Dashboard Live**: Visualisasi eksekusi agen step-by-step, highlight WhatsApp pelanggan, dan detail routing triage.
- **Skema Data Relasional**: 9 tabel yang mendukung integrasi dengan sistem logistik/inventaris nyata.

---

## 4. Reproducibility & Pengujian

- **Unit Tests**: 20 test (`python3 -m unittest discover -s tests`) yang mencakup routing, multi-intent, dynamic switching, kalkulator, SQLite, normalisasi output, dan adversarial edge cases. **Hasil: 20/20 OK.**
- **Eval Suite**: 7 skenario otomatis yang memvalidasi akurasi intent, kepatuhan kebijakan (safety), dan kualitas kalkulasi. **Hasil: 7/7 PASS, skor rata-rata 28.29/30.**
- **Mock Mode**: Simulasi deterministik yang berjalan sepenuhnya lokal tanpa API key — memastikan seluruh workflow dapat dievaluasi langsung oleh juri.
- **Live Mode**: Mendukung SumoPod AI API (OpenAI-compatible) untuk demo dengan LLM sesungguhnya.
