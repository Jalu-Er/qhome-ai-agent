# Video Script (3-5 Menit)

## 0:00–0:30 — Problem Statement

Customer support toko material bangunan menerima pesan dengan konteks yang beragam: barang rusak, retur, konsultasi produk, sampai permintaan estimasi biaya renovasi. Jika semua ditangani manual, respon lambat, prioritas terlewat, dan pelanggan kecewa.

Lebih buruk lagi: pelanggan sering mengirim **multi-intent** dalam satu percakapan — komplain barang pecah sekaligus minta pesan material baru. Sistem biasa tidak bisa menangani ini dengan baik.

## 0:30–1:30 — Solution: QHome AI Agent

QHome AI Agent adalah sistem **multi-agent AI** dengan 13 agen yang bekerja secara kolaboratif.

Tampilkan diagram arsitektur (`docs/system_architecture.png`):
- **Triage Router**: Gerbang cerdas yang mendeteksi intent dan memutuskan pipeline
- **5-Agent Support Pipeline**: Untuk komplain, retur, eskalasi
- **7-Agent Renovation Pipeline**: Untuk estimasi material, quotation otomatis

Fitur utama:
- **Complaint-First Priority**: Jika ada komplain + pesanan, komplain selalu diprioritaskan
- **Dynamic Pipeline Switching**: AI otomatis berpindah pipeline berdasarkan pesan terbaru

Tampilkan diagram switching (`docs/pipeline_switching.png`).

## 1:30–3:00 — Live Demo

Jalankan server:
```bash
python3 run.py web
```

### Demo Skenario 1: Komplain → Dynamic Switch ke Quotation

Customer Chat:
1. "Pesanan baru sampai pagi ini, tapi 6 dus keramik pecah dan retak."
   → Tunjukkan Staff Dashboard: pipeline = `support`, triage routing info
2. "Nomor saya 08123456789, hubungi saya ya"
   → AI hanya acknowledge, tidak mengulang jawaban lama (anti-looping)
3. "Saya juga ingin renovasi kamar mandi 2x2m, berapa estimasinya?"
   → **DYNAMIC SWITCH!** Pipeline berubah ke `renovation_quote`
   → Staff Dashboard menampilkan 7 agent trace baru
   → AI mengeluarkan tabel estimasi biaya material

### Demo Skenario 2: Konsultasi Produk

"Dinding kamar lembab dan ada jamur, luas 12m². Saya butuh cat yang cocok."
→ Tunjukkan: rekomendasi produk, peringatan keselamatan, dan estimasi biaya

### Tunjukkan Staff Dashboard:
- Live agent trace per langkah agen
- Detail triage routing (primary_intent, secondary_intents, priority_rule)
- Nomor WhatsApp pelanggan (highlight hijau)
- Draf quotation dengan kode QTE-XXXX

## 3:00–4:00 — Technical Excellence

- **Kalkulasi deterministik**: Bukan tebakan LLM — menggunakan formula matematika Python dengan waste +10%
- **SQLite persisten**: Semua data tersimpan (tiket, quotation, riwayat agen)
- **20 unit test + 7 eval suite**: Skor rata-rata 28.29/30
- **Zero heavy dependencies**: Hanya Python stdlib + SQLite
- **Mock + Live mode**: Bisa dijalankan tanpa API key (mock) atau dengan SumoPod API (live)

```bash
python3 -m unittest discover -s tests -v   # 20/20 OK
python3 run.py eval                          # 7/7 PASS, 28.29/30
```

## 4:00–4:30 — Business Impact

- Staff mendapat ringkasan tiket dan prioritas secara instan
- Kasus berisiko otomatis dieskalasi berdasarkan SLA
- Estimasi material akurat dan reproducible
- Log agen membuat proses bisa diaudit
- Pelanggan dilayani lebih cepat tanpa kehilangan konteks

## 4:30–5:00 — Closing

QHome AI Agent adalah contoh nyata bagaimana multi-agent AI bisa menghasilkan output bisnis terukur: dari triage otomatis, kalkulasi material, sampai draf penawaran — semua dalam satu percakapan. Sistem ini modular, reproducible, dan siap dijalankan langsung dari repository GitHub.
