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

```text
Customer Ticket
  -> Intent Classifier
  -> Knowledge Retrieval
  -> Solution Planner
  -> Priority & Escalation
  -> QA & Final Response
  -> final_output.json + report.md + interactions.jsonl
```

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

```text
http://127.0.0.1:8000
```

Web demo menampilkan input chat pelanggan, pilihan mode mock/live, jawaban final, intent, priority, escalation, dan trace 5 agent.

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
  competition-context.md    Konteks lomba
  project-plan.md           Rencana kerja sampai submission
  submission-description.md Draft deskripsi submission
src/qhome_ai_agent/
  agents.py                 Definisi 5 agent
  orchestrator.py           Workflow multi-agent
  llm.py                    Client SumoPod OpenAI-compatible
  mock_llm.py               Mode mock reproducible
  report.py                 Markdown report generator
web/
  index.html                Web chatbox demo
  styles.css
  app.js
```

## Deliverable Lomba

- Deskripsi AI Agent minimal 500 karakter.
- Video presentasi 3-5 menit.
- Repository GitHub publik berisi dokumentasi dan cara menjalankan project.
