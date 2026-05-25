# Project Plan: QHome Customer Support Multi-Agent

Last updated: 2026-05-25.

## Tujuan Utama

Membangun MVP AI Agent untuk AI Agent Competition 2026 yang menunjukkan sistem multi-agent nyata: agent punya peran berbeda, saling berbagi informasi, mengambil keputusan, mencatat log interaksi, dan menghasilkan output terstruktur yang relevan untuk bisnis QHome Mart.

## Use Case Final

Customer Support Triage Agent untuk konteks retail/home improvement.

Sistem menerima pertanyaan atau komplain pelanggan, lalu menghasilkan:

- klasifikasi intent pelanggan,
- tingkat prioritas,
- ringkasan masalah,
- rekomendasi solusi,
- keputusan eskalasi,
- jawaban final untuk pelanggan,
- log reasoning antar agent,
- output JSON yang bisa dievaluasi.

## Batasan Scope

Yang dikerjakan:

- CLI/backend Python untuk menjalankan workflow multi-agent.
- 5 agent dengan peran jelas.
- Sample knowledge base dan sample customer tickets.
- Structured output JSON.
- Log setiap interaksi agent ke file.
- README lengkap untuk setup, run, dan demo.
- Contoh hasil run untuk bahan video.

Yang tidak dikerjakan untuk MVP:

- UI kompleks.
- Integrasi sistem QHome Mart asli.
- Database production.
- Auth/user management.
- n8n sebagai core agent engine.

## Agent

1. Intent Classifier Agent
   - Mengidentifikasi intent, kategori masalah, dan informasi yang kurang.

2. Knowledge Retrieval Agent
   - Mengambil kebijakan/FAQ/data dummy yang relevan dari knowledge base lokal.

3. Solution Planner Agent
   - Menyusun opsi solusi dan langkah tindak lanjut.

4. Priority & Escalation Agent
   - Menilai urgency, risiko bisnis, dan perlu tidaknya eskalasi ke manusia.

5. QA & Final Response Agent
   - Mengecek konsistensi, membuat jawaban final, dan memastikan output sesuai format.

## Arsitektur MVP

Input ticket pelanggan masuk ke orchestrator. Orchestrator menjalankan agent berurutan dengan shared state. Setiap agent menerima state sebelumnya, menambahkan hasil analisisnya, lalu hasilnya dicatat ke log. Agent terakhir menghasilkan final response dan structured JSON.

```text
Customer Ticket
  -> Intent Classifier
  -> Knowledge Retrieval
  -> Solution Planner
  -> Priority & Escalation
  -> QA & Final Response
  -> JSON Output + Markdown Report + Interaction Log
```

## SumoPod AI Config

Gunakan `.env` lokal:

```bash
AI_API_KEY=sk-...
AI_BASE_URL=https://ai.sumopod.com/v1
AI_MODEL=gpt-4o-mini
```

Catatan:

- `.env` tidak boleh dipush.
- `.env.example` boleh dipush karena tidak berisi API key.
- Default model `gpt-4o-mini` untuk hemat token.

## Rencana Eksekusi

### Day 1: Foundation

- Buat struktur Python project.
- Buat OpenAI-compatible client untuk SumoPod.
- Buat schema data ticket, agent result, dan final output.
- Buat knowledge base dummy.
- Buat orchestrator sequential.

### Day 2: Agent Logic

- Implement 5 agent.
- Tambahkan prompt per agent.
- Tambahkan logging JSONL.
- Tambahkan sample tickets dan command untuk menjalankan demo.

### Day 3: Output & Evaluation

- Buat output JSON final.
- Buat report Markdown per run.
- Buat simple evaluation rubric: completeness, escalation correctness, policy match.
- Tambahkan test/mock mode agar repo tetap reproducible tanpa API key.

### Day 4: Documentation

- Perkuat README.
- Tambahkan diagram arsitektur.
- Tambahkan contoh input/output.
- Tulis deskripsi submission minimal 500 karakter.

### Day 5: Final Polish

- Run demo end-to-end.
- Siapkan script video 3-5 menit.
- Push final repo.
- Submit link GitHub, deskripsi, dan video.

## Definition of Done

Project siap submit jika:

- `README.md` menjelaskan setup dan cara menjalankan demo.
- Bisa dijalankan dengan SumoPod API.
- Bisa dijalankan dalam mock mode tanpa API key.
- Ada minimal 3 sample ticket.
- Ada log interaksi agent.
- Ada output JSON dan report.
- Ada dokumen deskripsi submission.
- Tidak ada API key atau secret di GitHub.

## Pitch Singkat

QHome Customer Support Multi-Agent membantu tim support memproses pertanyaan dan komplain pelanggan secara lebih cepat dan konsisten. Sistem membagi pekerjaan ke beberapa agent spesialis: klasifikasi intent, pencarian knowledge base, perencanaan solusi, penilaian prioritas/eskalasi, dan QA jawaban final. Output akhirnya terstruktur, dapat dilacak melalui log interaksi agent, dan bisa dipakai sebagai dasar efisiensi operasional customer service.
