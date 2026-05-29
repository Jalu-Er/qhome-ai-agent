# External Database Adapter

Demo default AgentZ memakai SQLite dari seed JSON. Ini sengaja dibuat agar juri dapat menjalankan project tanpa credential atau setup database eksternal.

Pada implementasi real, produk dan inventory dapat berasal dari database perusahaan. Struktur database eksternal boleh berbeda dari schema demo. Mapping dilakukan lewat adapter/config, misalnya `config/product_source.example.json`.

## Prinsip Integrasi

- External DB bersifat optional.
- External DB mode harus read-only.
- Sistem tidak melakukan migration ke database eksternal.
- Credential hanya dibaca dari `.env`.
- Jika external DB gagal, fallback ke SQLite demo agar workflow tetap berjalan.
- Adapter bertanggung jawab memetakan kolom internal seperti `sku`, `name`, `category`, `price`, `unit`, dan `stock_qty`.

## Contoh Config

```json
{
  "provider": "external_sql",
  "dialect": "mysql",
  "read_only": true,
  "tables": {
    "product_table": "barang",
    "inventory_table": "stok_gudang"
  },
  "columns": {
    "sku": "kode_barang",
    "name": "nama_barang",
    "category": "kategori",
    "price": "harga_jual",
    "unit": "satuan",
    "stock_qty": "jumlah_stok"
  }
}
```

Project ini belum membuka koneksi eksternal penuh karena itu akan menambah risiko setup. Boundary repository sudah disiapkan melalui `ProductRepository` dan `InventoryRepository`.
