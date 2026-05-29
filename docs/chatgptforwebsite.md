# Context for ChatGPT: QHome AI Agent Project

> **Baca ini dahulu sebelum mulai review atau bantu debug project ini.**

---

## 🎯 Apa Ini?

Ini adalah project **QHome AI Agent** — sebuah sistem **Multi-Agent AI** yang dibangun dari nol untuk mengikuti **AI Agent Competition 2026**. 

**Bisnis yang disimulasikan:** QHome Mart, toko material bangunan di Yogyakarta.

**Tujuan sistem:** Melayani percakapan pelanggan secara otomatis melalui dua jalur pipeline agen, ditentukan oleh satu router cerdas di garis depan.

---

## 🗂️ Repositori GitHub

Kode sumber tersedia di:
> **https://github.com/Jalu-Er/qhome-ai-agent**

Branch aktif saat ini: **`feature/agentz-routing-improvements`**

Pastikan kamu melihat branch ini, bukan `main` (yang sudah sedikit tertinggal).

---

## 🏗️ Arsitektur Sistem (Ringkasan)

```
[Pelanggan kirim pesan]
        ↓
[1] Hybrid Triage Router Agent (LLM)
    → Deteksi: primary_intent, secondary_intents, pipeline_target, WA number
    → Business Rules:
       - Complaint-First: jika ada komplain+pesanan di 1 pesan → utamakan komplain
       - Dynamic Switch: jika pesan TERBARU adalah pesanan baru → switch ke pipeline quotation
        ↓
    [Decision: support] ──────────────────────────────────────────────────────→ [A]
    [Decision: renovation_quote] ─────────────────────────────────────────────→ [B]

[A] 5-Agent Support Pipeline:
    intent_classifier → knowledge_retrieval → solution_planner → priority_escalation → qa_final_response
    Untuk: komplain, retur, barang rusak, pertanyaan kebijakan

[B] 7-Agent Renovation & Quotation Pipeline:
    requirement_intake → product_retrieval → inventory_snapshot → quantity_estimator → quote_builder → risk_verifier → staff_handoff_response
    Untuk: estimasi biaya, kalkulasi material, pesanan baru

[Output akhir]
    → Respons ke pelanggan (via web chat)
    → Tiket disimpan ke SQLite
    → Live trace di Staff Dashboard
```

---

## 📂 File-File Penting (dan apa fungsinya)

| File | Fungsi |
|------|--------|
| `src/qhome_ai_agent/agents.py` | Semua **system prompt** agen (Triage Router + 5 Support + 7 Renovation). Kalau ada masalah respons AI, cari di sini. |
| `src/qhome_ai_agent/orchestrator.py` | Logika **workflow execution** — siapa memanggil siapa, urutan agen, dynamic pipeline switching. |
| `src/qhome_ai_agent/mock_llm.py` | **Simulasi deterministik** agen untuk unit test & eval (bukan real LLM). Kaku, keyword-based. |
| `src/qhome_ai_agent/web.py` | Server web + session management + `_build_transcript()` yang memisahkan `message` (pesan terbaru) dari `history` (riwayat). |
| `src/qhome_ai_agent/storage.py` | Repositori SQLite: produk, inventory, tiket, quotation, agent_runs. |
| `src/qhome_ai_agent/tools.py` | Kalkulator deterministik: `calculate_tile_boxes()`, `calculate_paint_liters()`. |
| `web/customer.html & .js` | UI chat pelanggan. Mode default: **Live API** (bukan Mock). |
| `web/staff.html & .js` | Staff Dashboard — live agent trace per langkah, highlight WA, detail triage. |
| `data/evaluation_cases.json` | 7 skenario evaluasi otomatis. |
| `tests/` | 20 unit test (13 mock workflow + 7 renovation pipeline). |

---

## 🔑 Business Rules yang Sudah Diimplementasikan

### 1. Complaint-First Priority
Jika satu pesan pelanggan mengandung komplain DAN pesanan, sistem **selalu** masuk ke pipeline `support` dulu. Pesanan dicatat sebagai `secondary_intents`.

**Contoh trigger:**
> "Keramik saya pecah, tapi saya juga mau pesan batu bata."
→ Pipeline: `support`, secondary: `["renovation_quote"]`

### 2. Dynamic Pipeline Switching (🆕 terbaru)
Jika pesan terbaru pelanggan adalah **pesanan baru** (tidak ada komplain baru), sistem **berpindah otomatis** ke pipeline `renovation_quote` meskipun percakapan awalnya adalah komplain.

**Contoh alur:**
```
Pesan 1: "Keramik saya pecah" → Pipeline: support
Pesan 2: "Nomor WA saya 0812..."  → Pipeline: support (masih dalam konteks komplain)
Pesan 3: "Saya ingin pesan batu bata 500 pcs" → Pipeline: renovation_quote (SWITCH!)
```

### 3. Anti-Looping (🆕 terbaru)
Agen `qa_final_response` dan `staff_handoff_response` diinstruksikan agar **tidak mengulang** ringkasan sebelumnya. Jika pelanggan hanya memberikan nomer WA, AI hanya acknowledge dan konfirmasi langkah berikutnya.

### 4. Latest-Message-First Classification
`intent_classifier` diinstruksikan untuk mengklasifikasi intent berdasarkan **pesan terbaru** saja, bukan seluruh riwayat. Ini mencegah AI "tersangkut" di konteks lama.

### 5. Ticket & History Separation (🆕 terbaru)
Di `web.py`, payload ke workflow dibagi menjadi:
- `ticket["message"]` = **hanya pesan terbaru** pelanggan
- `ticket["history"]` = transkip riwayat percakapan sebelumnya

Ini memungkinkan `_triage_router` di `mock_llm.py` untuk membedakan `latest_msg` vs `msg` (keseluruhan).

---

## 🐛 Masalah yang SUDAH Diselesaikan

| Masalah | Solusi |
|---------|--------|
| AI mengulangi "keramik pecah" terus meski sudah dijawab | Anti-looping prompt di `qa_final_response` + `staff_handoff_response` |
| AI tidak mau switch pipeline setelah komplain selesai | Dynamic Pipeline Switching di Triage Router prompt + `mock_llm._triage_router()` |
| Mock LLM salah deteksi "Pesanan QH-xxxx" sebagai intent order | Keyword `"pesanan qh-"` dikecualikan di `_is_bulk_order()` |
| Pipeline tetap di `support` meski pesan terbaru adalah pemesanan | Ditambahkan deteksi `latest_is_renovation` vs `is_complaint` |
| Mode default UI adalah Mock (kaku) | Diubah default ke **Live API** di `customer.html` |

---

## ⚠️ Area yang PERLU DIPERHATIKAN / Belum Sempurna

1. **Mock LLM masih keyword-based** — untuk testing CI saja. Semua respons "nyangkut" di Mock adalah by-design. Jangan pakai untuk demo ke juri.
2. **Pipeline switching hanya berlaku per pesan** — setiap pesan baru masuk, Triage Router dipanggil ulang dari awal dengan konteks terbaru. Tidak ada "session state" di level Triage Router; state hanya disimpan di frontend (`history` di `customer.js`) dan SQLite.
3. **Kalkulasi batu bata** — SKU batu bata mungkin tidak ada di database default (hanya ada produk kamar mandi & cat). Jika pelanggan memesan batu bata, pipeline renovation akan tetap dijalankan, tapi `product_retrieval` mungkin mengembalikan hasil kosong. Perlu tambah data di seed.

---

## 🚀 Cara Jalankan Cepat

```bash
# 1. Inisialisasi DB
python3 run.py init-db

# 2. Jalankan web server
python3 run.py web

# Buka browser:
# Customer: http://127.0.0.1:8000/
# Staff:    http://127.0.0.1:8000/staff

# 3. Jalankan semua test
python3 -m unittest discover -s tests -v

# 4. Jalankan eval suite
python3 run.py eval
```

---

## 🧩 Hal-Hal yang Bisa Ditingkatkan (Opsional untuk ChatGPT)

Kalau saya ingin melanjutkan improvisasi, pertimbangkan ini berdasarkan prioritas:

1. **Tambah SKU batu bata ke database seed** (`data/seed/products.json`) agar kalkulasi quotation untuk batu bata bisa memberikan harga nyata, bukan fallback generic.
2. **Tambah memory minimal di session**: Saat ini session hanya menyimpan riwayat teks, bukan `current_pipeline_state`. Jika pipeline di-persist per session, tidak perlu re-run Triage Router dari nol setiap pesan.
3. **Improved triage for follow-up messages**: Jika pelanggan hanya mengirim satu kata seperti "ok" atau "baik", Triage Router harusnya fallback ke pipeline yang sama dengan pesan sebelumnya, bukan memulai ulang.
4. **UI feedback pipeline yang aktif**: Tampilkan di Customer UI pipeline mana yang sedang aktif (Support atau Quotation) agar pelanggan tahu dalam mode apa AI sedang merespons.

---

## 📌 Catatan Penting untuk Sesi Ini

- **Jangan rombak arsitektur besar** — hanya refinement yang diperlukan
- **Jangan push ke `main` langsung** — gunakan branch `feature/...`
- **Jangan ubah nama project, tema, atau alur utama**
- **Fokus pada:** kualitas respons, logika routing, dan kesiapan demo video

---

*File ini dibuat otomatis sebagai konteks untuk sesi ChatGPT website. Last updated: 2026-05-29.*
