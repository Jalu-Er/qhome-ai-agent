# Demo Scenarios

## 1. Renovasi Kamar Mandi 2x2m

Customer:

```text
Saya mau renovasi kamar mandi ukuran 2x2m. Butuh keramik lantai anti slip, waterproofing, perekat keramik, nat, shower, dan exhaust fan. Budget maksimal 3 juta. Alamat di Jalan Kaliurang, Sleman. Warna keramik abu-abu.
```

Yang ditunjukkan:

- Requirement extraction.
- Product retrieval dari SQLite.
- Estimasi box/liter.
- Draft quote.
- Risk verifier.
- Staff handoff.

## 2. Dinding Lembab

Customer:

```text
Dinding kamar lembab dan ada jamur, luas kira-kira 12 m2. Saya butuh cat atau waterproofing yang cocok, warna putih.
```

Yang ditunjukkan:

- Kategori cat dan waterproofing.
- Caveat sumber lembab perlu dicek.
- Stok snapshot, bukan real-time.
- Customer diminta kontak jika ingin follow-up staff.

## 3. Komplain Barang Rusak

Customer:

```text
Pesanan QH-77881 sampai tapi 2 box keramik pecah. Saya komplain karena mau dipasang minggu ini.
```

Yang ditunjukkan:

- Sistem tetap membuat ticket operasional.
- Tidak meminta upload di chat.
- Staff handoff tetap aman untuk after-sales.

## 4. Complaint-First Priority

Customer:

```text
Keramik saya pecah 3 dus saat sampai. Oh ya, kalau mau nambah beli semen 2 sak harganya berapa?
```

Yang ditunjukkan:

- Sistem mendeteksi `damaged_item` (komplain) dan `renovation_quote` (sales).
- Routing difokuskan ke `support` pipeline untuk empati pada komplain.
- Order semen dicatat di `secondary_intents` agar staff tahu ada peluang upsell *setelah* masalah selesai.

## 5. Dynamic Pipeline Switching

Customer (Chat 1):

```text
Pesanan keramik saya pecah 1 dus.
```
*(Agen menyelesaikan komplain)*

Customer (Chat 2):

```text
Nomor WA saya 08123456789.
Saya juga ingin pesan batu bata 3000 pcs untuk pagar, berapa estimasinya?
```

Yang ditunjukkan:

- Sistem mendeteksi pesan terbaru adalah pesanan baru murni (tanpa kata komplain di pesan terakhir).
- Triage Router memutus alur `support` dan secara dinamis *switch* ke `renovation_quote` (7-agent pipeline).
- Quotation batu bata di-generate otomatis tanpa terhambat status komplain sebelumnya.
