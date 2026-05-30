# Project Plan: QHome AI Agent

Last updated: 2026-05-29.

## Tujuan

Membangun sistem AI multi-agent untuk AI Agent Competition 2026 yang mendemonstrasikan kolaborasi antar-agen, pengambilan keputusan berbasis LLM, kalkulasi material deterministik, dan output bisnis terukur — dalam konteks retail material bangunan QHome Mart Yogyakarta.

## Arsitektur Final

```text
[Pelanggan] → [Hybrid Triage Router] → [Support Pipeline (5-Agent)] atau [Renovation Pipeline (7-Agent)]
                                      → [SQLite Database]
                                      → [Staff Dashboard]
```

Total: **13 agen** (1 Router + 5 Support + 7 Renovation).

## Fitur yang Sudah Diimplementasikan

- ✅ Hybrid Triage Router Agent (LLM-powered, multi-intent detection)
- ✅ 5-Agent Support Pipeline (intent → knowledge → solution → priority → final)
- ✅ 7-Agent Renovation Pipeline (intake → product → inventory → estimator → quote → risk → handoff)
- ✅ Dynamic Pipeline Switching (switch otomatis berdasarkan pesan terbaru)
- ✅ Complaint-First Business Rule
- ✅ Anti-Looping Logic
- ✅ Latest-Message-First Classification
- ✅ SQLite persistent storage (9 tabel)
- ✅ Customer Chat UI (web)
- ✅ Staff Dashboard (live agent trace)
- ✅ CLI workflow runner
- ✅ Mock mode (offline, deterministik)
- ✅ Live mode (SumoPod API / OpenAI-compatible)
- ✅ 20 unit tests (100% pass)
- ✅ 7 eval scenarios (28.29/30)
- ✅ Deployment guide (systemd + Nginx)

## Batasan Scope (Tidak Dikerjakan)

- UI mobile/responsive kompleks
- Integrasi sistem QHome Mart asli
- Database production (MariaDB/PostgreSQL)
- Auth/user management
- Upload file/gambar di chat
- Integrasi WhatsApp/CRM langsung

## SumoPod AI Config

```bash
AI_API_KEY=sk-...
AI_BASE_URL=https://ai.sumopod.com/v1
AI_MODEL=gpt-4o-mini
```

## Deliverable Kompetisi

- ✅ Deskripsi AI Agent (≥500 karakter) → `docs/submission-description.md`
- ⏳ Video presentasi 3–5 menit → `docs/video-script.md`
- ✅ Repository GitHub publik dengan dokumentasi
