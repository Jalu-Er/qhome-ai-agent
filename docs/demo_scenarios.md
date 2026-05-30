# Skenario Demo QHome AI Agent

Dokumen ini menjabarkan skenario demo untuk presentasi dan video kompetisi.

---

## Skenario 1 — Komplain Barang Rusak (Support Pipeline)

**Input Pelanggan:**

```text
Pesanan QH-77881 sampai tapi 2 box keramik pecah.
Saya komplain karena mau dipasang minggu ini.
```

**Yang Ditunjukkan:**
- Hybrid Triage Router mengenali intent `damaged_item`
- Support Pipeline (5 agent) diaktifkan
- Support Case Packet digenerate dengan instruksi staf:
  - Jika nomor WA belum ada: "Minta nomor WhatsApp pelanggan terlebih dahulu"
  - Jika nomor WA ada: "Segera hubungi pelanggan via WhatsApp"
- Respons empatik, tidak langsung menawarkan penjualan baru

---

## Skenario 2 — Quotation Renovasi Kamar Mandi (Renovation Pipeline)

**Input Pelanggan:**

```text
Saya mau renovasi kamar mandi ukuran 2x2m.
Butuh keramik lantai anti slip, waterproofing, perekat, dan nat.
Budget maksimal 3 juta. Alamat di Jalan Kaliurang, Sleman.
```

**Yang Ditunjukkan:**
- Router mendeteksi `renovation_quote`
- Renovation Pipeline (7 agent) diaktifkan
- Quantity Estimator kalkulasi kebutuhan material (tile formula, waste +10%)
- Quote Builder generate kode `QTE-XXXX` dengan line items
- Risk Verifier validasi kelengkapan dan kesesuaian budget
- Staff Dashboard menampilkan 7 langkah agent trace

---

## Skenario 3 — Dinding Lembab & Cat (Product Consultation)

**Input Pelanggan:**

```text
Dinding kamar lembab dan ada jamur, luas kira-kira 12 m2.
Saya butuh cat atau waterproofing yang cocok.
```

**Yang Ditunjukkan:**
- Router mendeteksi `product_advice` → Support Pipeline
- Knowledge Retrieval mencari rekomendasi produk anti-lembab
- Respons mengandung klausa "draf awal / perlu verifikasi stok"
- Staff Dashboard menampilkan trace 5 agent Support Pipeline

---

## Skenario 4 — Complaint-First Priority (Multi-Intent)

**Input Pelanggan:**

```text
Keramik saya pecah 3 dus saat sampai.
Oh ya, kalau mau nambah beli semen 2 sak harganya berapa?
```

**Yang Ditunjukkan:**
- Router mendeteksi `multi_intent = true` (komplain + pesanan dalam 1 pesan)
- `priority_rule = "complaint_first"` — routing ke Support Pipeline
- Pesanan semen dicatat di `secondary_intents` dan `staff_handoff_notes`
- Respons fokus pada empati komplain, tidak langsung menjual

---

## Skenario 5 — Dynamic Pipeline Switching

**Chat 1 (Riwayat):**

```text
Pesanan keramik saya pecah 1 dus.
```

*(Support Pipeline menangani komplain)*

**Chat 2 (Pesan Baru):**

```text
Saya juga ingin pesan batu bata 3000 pcs untuk pagar.
Berapa estimasinya?
```

**Yang Ditunjukkan:**
- Router menganalisis pesan terbaru (pesan 2) — tidak ada komplain baru
- `priority_rule = "dynamic_pipeline_switch"` — otomatis switch ke Renovation Pipeline
- Quotation batu bata digenerate tanpa terhambat status komplain lama
- Staff Dashboard menampilkan trace dari pipeline baru

---

## Skenario 6 — Produk Tidak Ditemukan (Fallback)

**Input Pelanggan:**

```text
Apakah ada marmer impor Italia warna bianco?
```

**Yang Ditunjukkan:**
- Product Retrieval tidak menemukan produk di katalog
- System memberikan respons `product_not_found` yang aman
- Staf diberitahu untuk manual cek dan follow-up pelanggan

---

## Skenario 7 — Out-of-Scope Guard

**Input Pelanggan:**

```text
Bisa tolong buatkan script Python untuk scrape harga material di internet?
```

**Yang Ditunjukkan:**
- Router mendeteksi `out_of_scope_coding`
- Respons menolak dengan sopan dan mengarahkan kembali ke layanan QHome Mart
- Tidak ada informasi berbahaya yang bocor

---

## Urutan Demo yang Direkomendasikan

1. Buka `http://127.0.0.1:8000/` (Customer Chat UI)
2. Pilih mode **"Live"** (pastikan `.env` sudah terisi API key)
3. Demonstrasikan Skenario 2 (Renovation Quote) — paling visual dan lengkap
4. Buka Staff Dashboard `http://127.0.0.1:8000/staff` — tunjukkan AI Tracking
5. Demonstrasikan Skenario 4 (Complaint-First) — tunjukkan business rule
6. Demonstrasikan Skenario 5 (Dynamic Switch) — tunjukkan adaptasi konteks
7. Tunjukkan Support Case Packet dan instruksi staf di Staff Dashboard
