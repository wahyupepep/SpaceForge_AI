# Development Guide

## Prerequisite

- Node.js 20 atau lebih baru
- Python 3.12 atau lebih baru
- Docker dan Docker Compose untuk full local stack

## Setup

Ikuti perintah pada root `README.md`. Configuration lokal memakai environment variable; mulai dari `.env.example` dan jangan commit secret.

## Working agreements

- Baca dokumentasi yang relevan sebelum implementasi fase.
- Pertahankan arah dependency clean architecture.
- Letakkan business invariant di domain/application, bukan route atau React component.
- Semua AI output penting harus memiliki Pydantic/JSON schema.
- Revisi artifact membuat versi baru.
- Catat perubahan keputusan arsitektur di `ARCHITECTURE_DECISIONS.md`.
- Perbarui dokumentasi dan changelog bersama perubahan behavior.

## Backend conventions

Route hanya menangani HTTP concern. Use case mengorkestrasi domain dan port. Adapter database/provider mengimplementasikan port. Gunakan type annotation, schema eksplisit, dan test untuk success serta failure path. Jalankan:

```bash
cd backend
ruff check .
pytest
```

Semua route product berada di `/api/v1`. Database I/O memakai async SQLAlchemy repository. Buat Alembic revision untuk setiap perubahan schema; jangan gunakan manual DDL atau `metadata.create_all()` sebagai deployment mechanism.

## Frontend conventions

Gunakan Server Component sebagai default dan Client Component hanya bila interaksi browser dibutuhkan. UI menampilkan authoritative state dari backend dan tidak mereplikasi state-machine rule. Gunakan semantic HTML, keyboard-accessible control, serta explicit loading, empty, and error state. Jalankan:

```bash
cd frontend
npm run lint
npm run typecheck
npm run build
```

HTTP request harus melalui `services/api-client.ts`. Jangan mengakses database, OpenAI, atau server secret dari frontend.

## Definition of done per phase

- Scope fase bekerja tanpa menghapus behavior sebelumnya.
- Validation dan failure state relevan ditangani.
- Test baru dan existing lulus.
- Dokumentasi arsitektur/kontrak terkait diperbarui.
- `CHANGELOG.md` diperbarui.
- Tidak ada secret, generated cache, atau dependency directory di commit.
