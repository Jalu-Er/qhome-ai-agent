# Database

AgentZ memakai seed JSON untuk data awal demo dan SQLite untuk runtime. Tujuannya agar juri dapat menjalankan sistem dari fresh clone tanpa MariaDB, credential, atau koneksi eksternal.

## Alur Data

```text
data/seed/products.json
data/seed/inventory.json
data/seed/policies.json
        -> python3 run.py init-db
        -> data/qhome_agent.db
        -> workflow AgentZ membaca SQLite
```

Seed JSON hanya sumber awal. Setelah `init-db`, produk, inventory snapshot, ticket, message, quote, quote item, dan agent trace disimpan di SQLite.

## Init Database

```bash
python3 run.py init-db
```

Command ini idempotent. Tabel dibuat jika belum ada, dan seed tidak diduplikasi jika sudah pernah masuk.

## Reset Demo

Database runtime adalah generated file dan tidak di-commit. Untuk reset manual:

```bash
rm data/qhome_agent.db
python3 run.py init-db
```

Jangan lakukan reset jika ingin mempertahankan ticket demo lama.

## Tabel Utama

- `products`: katalog produk demo, coverage, use case, risk note.
- `inventory_snapshots`: snapshot stok demo per SKU dan branch.
- `tickets`: ticket operasional dari chat anonymous.
- `messages`: history pesan per ticket.
- `quotes`: draft quotation per ticket.
- `quote_items`: item dan subtotal quotation.
- `agent_runs`: metadata run agent.
- `agent_steps`: input/output JSON tiap agent.
- `policies`: policy demo untuk guardrail stok, harga, kontak, dan renovasi.

## Kenapa SQLite

SQLite dipilih karena reproducible, zero dependency, mudah dihapus ulang, dan cukup untuk demo multi-agent. Implementasi production dapat mengganti repository dengan adapter database internal tanpa mengubah workflow utama.
