# QHome AI Agent

Project submission untuk AI Agent Competition 2026.

QHome AI Agent adalah MVP sistem multi-agent untuk membantu triage customer support dan konsultasi produk QHome Mart. Sistem menerima pertanyaan atau komplain pelanggan, lalu beberapa agent bekerja sama untuk mengklasifikasi intent, mengambil knowledge base yang relevan, menyusun solusi/rekomendasi, menentukan prioritas/eskalasi, dan membuat jawaban final yang terstruktur.

## Kenapa Multi-Agent?

Setiap agent memiliki tanggung jawab berbeda:

1. `intent_classifier`: mengidentifikasi intent, kategori, ringkasan, dan data yang kurang.
2. `knowledge_retrieval`: memilih kebijakan/FAQ/product guide lokal yang relevan.
3. `solution_planner`: menyusun rencana solusi atau rekomendasi produk.
4. `priority_escalation`: menentukan prioritas, SLA, risiko bisnis, dan eskalasi.
5. `qa_final_response`: mengecek konsistensi dan membuat jawaban final.

Workflow dijalankan oleh orchestrator sequential dengan shared state. Semua hasil agent dicatat ke `interactions.jsonl`, lalu output akhir disimpan sebagai JSON dan report Markdown.

## Arsitektur

![Architecture Diagram](docs/architecture.png)

Setiap agent menerima shared state berisi ticket awal dan output agent sebelumnya, sehingga keputusan dibangun secara bertahap dari klasifikasi sampai jawaban final. Detail arsitektur tersedia di [`docs/architecture.md`](docs/architecture.md).

## Cara Menjalankan

Project ini bisa berjalan dengan Python standard library saja. Tidak perlu install dependency untuk mode mock.

```bash
python3 run.py list-tickets
python3 run.py run --mode mock --ticket-id damaged-ceramic-delivery
```

Output akan dibuat di folder `runs/<run-id>/`.

Contoh custom ticket:

```bash
python3 run.py run --mode mock --ticket-text "Pesanan QH-10001 belum sampai padahal estimasi kemarin. Tolong dicek."
```

Contoh konsultasi produk:

```bash
python3 run.py run --mode mock --ticket-id damp-wall-paint-advice
```

## Web Chatbox Demo

Jalankan:

```bash
python3 run.py web
```

Buka:

- **Customer Chat**: `http://127.0.0.1:8000/` — tampilan chat bersih untuk pelanggan.
- **Staff Dashboard**: `http://127.0.0.1:8000/staff` — dashboard internal dengan ticket queue dan triage panel.

Kedua halaman terpisah secara desain, seperti sistem CS sesungguhnya. Customer hanya melihat chat, staff melihat antrian ticket dan keputusan 5 agent.

Ticket otomatis masuk ke staff dashboard saat customer mengirim pesan. Staff bisa filter ticket berdasarkan status: Semua, Perlu Staff, Menunggu Info, atau Resolved.

Jika pelanggan membalas lagi, pesan baru dianalisis bersama history chat sehingga status internal bisa berubah dari `waiting_info` menjadi `needs_staff` atau `resolved`.

Contoh sales/order flow:

- Customer menanyakan order bahan bangunan dan pengiriman.
- Agent mencatat alamat, daftar item, jumlah, dan metode bayar.
- Jika nomor HP/WhatsApp belum ada, agent meminta kontak aktif.
- Staff dashboard menandai ticket sebagai `Menunggu Info` sampai kontak lengkap.
- Estimasi tiba, ongkir, armada, dan stok tidak dijanjikan AI; semuanya masuk follow-up staff toko/logistik.

## Data Source

Agent tidak mengambil keputusan dari data yang tidak terlihat. Semua konteks demo berada di:

- `data/knowledge_base.json`: policy support dan product guides.
- `data/sample_tickets.json`: contoh ticket pelanggan.

Contoh product guide yang tersedia:

- rekomendasi cat untuk dinding lembab,
- kebocoran kamar mandi,
- pemilihan keramik lantai,
- pemilihan lampu LED.

Database cloud belum dipakai di MVP agar juri bisa menjalankan project tanpa setup eksternal. Jika perusahaan ingin implementasi production, `data/knowledge_base.json` bisa diganti dengan MariaDB/SumoPod database atau knowledge base internal.

## SumoPod AI

Project ini dirancang untuk API yang kompatibel dengan OpenAI SDK.

```bash
AI_API_KEY=
AI_BASE_URL=https://ai.sumopod.com/v1
AI_MODEL=gpt-4o-mini
```

Jalankan live mode:

```bash
python3 run.py run --mode live --ticket-id damaged-ceramic-delivery
```

Jangan commit API key ke repository. `.env.example` aman karena hanya template, sedangkan `.env` berisi secret dan sudah masuk `.gitignore`.

## Test

```bash
python3 -m unittest discover -s tests
```

## Struktur Project

```text
data/
  knowledge_base.json       Sample policy/FAQ/product guides QHome Mart
  sample_tickets.json       Sample customer tickets
docs/
  architecture.md           Detail arsitektur
  architecture.png          Diagram arsitektur (image)
src/qhome_ai_agent/
  agents.py                 Definisi 5 agent
  orchestrator.py           Workflow multi-agent
  llm.py                    Client SumoPod OpenAI-compatible
  mock_llm.py               Mode mock reproducible
  web.py                    Web server + session store
  report.py                 Markdown report generator
web/
  customer.html             Halaman chat pelanggan (/)
  customer.js               Logic chat pelanggan
  staff.html                Dashboard staff (/staff)
  staff.js                  Logic dashboard + ticket queue
  styles.css                Shared styles
```

## Deliverable Lomba

- Deskripsi AI Agent minimal 500 karakter.
- Video presentasi 3-5 menit.
- Repository GitHub publik berisi dokumentasi dan cara menjalankan project.
