# Draft Deskripsi Submission — QHome AI Agent

QHome AI Agent adalah sistem multi-agent AI untuk mengotomatisasi customer support, konsultasi produk, dan pembuatan quotation material bangunan pada konteks retail home improvement QHome Mart Yogyakarta.

Sistem menggunakan Hybrid Triage Router Agent berbasis LLM sebagai gerbang cerdas yang mendeteksi intent pelanggan secara multi-intent, menentukan pipeline optimal, dan memprioritaskan penanganan keluhan di atas penjualan (Complaint-First Business Rule).

Arsitektur terdiri dari 13 agen total yang terbagi dalam dua jalur pipeline: 5-Agent Support Pipeline untuk penanganan komplain, pencarian kebijakan, perencanaan solusi, penilaian prioritas eskalasi, dan penyusunan respons final; serta 7-Agent Renovation & Quotation Pipeline untuk ekstraksi kebutuhan proyek, pengambilan SKU produk dari database SQLite, pengecekan inventori cabang, kalkulasi material deterministik (waste +10%), pembuatan draf penawaran harga otomatis (kode QTE-XXXX), audit kepatuhan kebijakan melalui critic debate loop, dan penyusunan instruksi handoff staf.

Fitur unggulan sistem ini adalah Dynamic Pipeline Switching: AI secara otomatis berpindah antara pipeline support dan renovation berdasarkan pesan terbaru pelanggan tanpa intervensi staf. Seluruh data operasional tersimpan persisten di SQLite (tiket, quotation, riwayat agen, katalog produk). Web demo menyediakan Customer Chat UI dan Staff Dashboard dengan visualisasi live agent trace per langkah agen. Sistem diuji dengan 56 unit test dan 5 skenario evaluasi otomatis (skor rata-rata 99/100) yang memvalidasi akurasi routing, kepatuhan kebijakan, dan kualitas kalkulasi. Seluruh workflow dapat dijalankan tanpa dependency eksternal berat — cukup Python 3.11+ dan SQLite bawaan.
