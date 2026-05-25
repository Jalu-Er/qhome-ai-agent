# Video Script 3-5 Menit

## 0:00-0:30 Problem

Customer support retail sering menerima ticket dengan konteks berbeda: barang rusak saat pengiriman, retur, keterlambatan, pembayaran, atau instalasi. Jika semua ticket dibaca manual, respon bisa lambat dan prioritas kasus berisiko bisa terlambat terdeteksi.

## 0:30-1:15 Solution

QHome AI Agent membantu triage ticket dan konsultasi produk dengan sistem multi-agent. Fokusnya bukan chat biasa, tetapi pembagian kerja antar agent yang jelas: klasifikasi intent, pencarian knowledge base, perencanaan solusi/rekomendasi, prioritas eskalasi, dan QA jawaban final.

## 1:15-2:10 Architecture

Tampilkan `docs/architecture.md`. Jelaskan workflow sequential:

```text
Ticket -> Intent -> Knowledge -> Solution -> Priority -> Final Response
```

Tekankan bahwa setiap agent membaca shared state dari agent sebelumnya dan semua output dicatat di `interactions.jsonl`.

## 2:10-3:20 Demo

Jalankan:

```bash
python3 run.py list-tickets
python3 run.py run --mode mock --ticket-id damaged-ceramic-delivery
```

Tampilkan web chatbox:

```bash
python3 run.py web
```

Demo pertanyaan produk:

```text
Saya butuh cat dinding nih, tapi dinding rumah saya lembab dan ada sedikit jamur. Baiknya pakai apa ya?
```

Tampilkan file hasil:

```bash
runs/<run-id>/final_output.json
runs/<run-id>/report.md
runs/<run-id>/interactions.jsonl
```

Jika live mode SumoPod sudah stabil, jalankan:

```bash
python3 run.py run --mode live --ticket-id damaged-ceramic-delivery
```

## 3:20-4:20 Business Impact

Jelaskan impact:

- Support bisa mendapat ringkasan ticket dan prioritas lebih cepat.
- Kasus rusak/retur/keterlambatan bisa dieskalasi berdasarkan risiko.
- Jawaban lebih konsisten karena memakai knowledge base.
- Pertanyaan produk bisa diarahkan dengan product guide, bukan jawaban bebas tanpa konteks.
- Log agent membuat proses bisa diaudit dan dievaluasi.

## 4:20-5:00 Closing

Tutup dengan definisi sukses: sistem multi-agent ini modular, reproducible, dapat berjalan dengan SumoPod AI, dan tetap bisa diuji melalui mock mode tanpa API key.
