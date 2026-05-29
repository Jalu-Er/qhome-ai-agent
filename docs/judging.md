# Kesesuaian Kriteria Penilaian (Evaluation Fit)

Dokumen ini memaparkan implementasi teknis QHome AI Agent berdasarkan kriteria penilaian kompetisi:

---

## 1. Routing & Orchestration (LLM-Powered Multi-Intent Router)
*   **Routing Dinamis**: Menggunakan **Triage Router Agent** berbasis LLM. Router ini menganalisis seluruh konteks chat pelanggan untuk menentukan pipeline terbaik.
*   **Prioritas Penanganan (Complaint First)**: Jika terjadi *mixed multi-intent* (contoh: komplain barang rusak sekaligus permintaan pembelian), sistem memprioritaskan penyelesaian komplain melalui `support` pipeline.
*   **Staff Handoff & Secondary Intent Capture**: Kebutuhan sekunder tetap ditangkap di parameter `secondary_intents` dan didokumentasikan di `staff_handoff_notes` untuk ditindaklanjuti staf internal.

---

## 2. Kolaborasi Multi-Agent (7-Agent Pipeline)
Sistem menggunakan beberapa agen dengan peran spesifik:
*   **Requirement Intake**: Ekstraksi dimensi area, kontak, anggaran, dan jenis proyek.
*   **Product Retrieval & Inventory Snapshot**: Mengambil data produk dari SQLite dan memverifikasi ketersediaan stok fisik cabang.
*   **Quantity Estimator**: Menggunakan kalkulator deterministik (Python functions) untuk menghitung kebutuhan material berdasarkan dimensi area (termasuk *waste allowance* 10%).
*   **Quote Builder**: Menyusun draf penawaran harga dengan detail item dan subtotal.
*   **Active Debate Loop (Critic/Verifier)**: Agen audit memeriksa kepatuhan kebijakan (stok, harga estimasi). Jika terdeteksi masalah, sistem memicu perulangan (*loop*) revisi agar Quote Builder melakukan koreksi sebelum respons difinalisasi.

---

## 3. Implementasi Sistem Bisnis
*   **Persistensi SQLite**: Menyimpan riwayat percakapan, jejak interaksi agen (`agent_runs`, `agent_steps`), data tiket, dan draf penawaran (quotation).
*   **Staff Dashboard Live**: Menyediakan antarmuka untuk memantau status tiket, melihat visualisasi eksekusi agen secara step-by-step, dan meninjau ringkasan hasil (triage intent, draf quote).
*   **Skema Data Relasional**: Menggunakan skema database yang mendukung penggabungan dengan sistem logistik atau inventaris nyata.

---

## 4. Reproducibility & Pengujian
*   **Automated Evaluation Suite**: Memiliki skenario uji otomatis untuk memvalidasi akurasi ekstraksi intent, kepatuhan kebijakan (safety), dan keluaran kalkulasi estimasi.
*   **Unit Tests**: Menyertakan 20 test komprehensif (`python3 -m unittest discover -s tests`) yang menguji kalkulator, database, triage router, normalisasi output, perpindahan pipeline antar-turn percakapan, follow-up kekhawatiran kualitas pengiriman, dan penolakan abuse coding di luar layanan QHome. (Lulus 100%).
*   **Mock Mode**: Mendukung mode simulasi deterministik yang berjalan sepenuhnya lokal tanpa LLM API, memastikan seluruh workflow dan web UI dapat dievaluasi langsung oleh juri.
