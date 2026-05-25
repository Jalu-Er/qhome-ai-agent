# AI Agent Competition 2026 Context

Last updated: 2026-05-25, Asia/Jakarta.

## Deadline

Submission: 25-30 Mei 2026.

Pengumuman 5 besar: 2 Juni 2026.

Penjurian final online: 6 Juni 2026.

## Deliverable

- Deskripsi AI Agent minimal 500 karakter, mencakup tujuan, fitur utama, dan nilai unik project.
- Video presentasi 3-5 menit yang menjelaskan konsep, cara kerja, dan demo AI Agent.
- Repository GitHub publik dengan dokumentasi penggunaan dan komponen pendukung.

## Fokus Lomba

Kompetisi menilai desain dan implementasi sistem multi-agent AI. Fokusnya bukan UI atau prompt panjang, tetapi bagaimana agent berpikir, berkolaborasi, mengambil keputusan, dan menghasilkan output bisnis yang terukur.

## Ekspektasi Teknis

- Multi-agent communication.
- Workflow dan orchestration yang jelas.
- Log interaksi antar agent.
- Arsitektur modular dan reproducible.
- Bebas memilih LLM API dan framework.

## Kriteria Penilaian

- Kualitas reasoning agent.
- Kolaborasi antar agent.
- Dampak ke dunia nyata: revenue, efisiensi, atau operasional.
- Kejelasan arsitektur sistem.
- Reproducibility.

## SumoPod AI

SumoPod menyediakan API yang kompatibel dengan OpenAI SDK dan tool seperti n8n OpenAI node.

- Chat completions endpoint: `POST https://ai.sumopod.com/v1/chat/completions`.
- SDK/n8n base URL: `https://ai.sumopod.com/v1`.
- API key format: `sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`.
- Model contoh: `gpt-4o-mini`, `gpt-4o`, `claude-3-haiku`, `deepseek-chat`.

Rekomendasi awal: gunakan `gpt-4o-mini` untuk hemat token. Naik ke `gpt-4o` hanya untuk evaluasi atau reasoning final yang lebih berat.

## Strategi 5 Hari

MVP harus kecil tetapi lengkap:

1. Pilih satu use case bisnis yang jelas.
2. Buat 4-5 agent dengan peran berbeda.
3. Pakai orchestrator eksplisit.
4. Simpan semua log agent.
5. Hasilkan output akhir dalam JSON dan report Markdown/HTML.
6. Siapkan README, diagram arsitektur sederhana, sample input/output, dan video demo.

## Use Case Paling Realistis

Rekomendasi awal: Customer Support Triage Agent atau AI Sales/Product Advisor Agent untuk konteks retail/home improvement. Keduanya mudah didemokan dengan data dummy dan tetap relevan untuk bisnis QHome Mart.
