# Artifact Storage

## Strategy

Artifact memiliki dua lapisan persistence:

1. Metadata relational di PostgreSQL untuk identity, project, type, current version, status, dan timestamps.
2. Immutable `ArtifactVersion` dengan version number, validated JSONB content, creator, dan timestamp.

Update tidak menimpa content lama. Perubahan selalu menghasilkan version baru dan current-version pointer berubah dalam transaction yang sama.

## Relational shape

```text
Artifact
  id UUID
  project_id UUID
  requirement_id UUID nullable
  artifact_type
  current_version
  status
  created_at TIMESTAMPTZ
  updated_at TIMESTAMPTZ

ArtifactVersion
  id UUID
  artifact_id UUID
  version INTEGER
  content_json JSONB
  created_by
  created_at TIMESTAMPTZ
```

Model ini diimplementasikan pada Phase 2 melalui Alembic revision `20260927_0005`. Kombinasi `artifact_id` dan `version` unik. Row artifact dikunci saat membuat revisi agar concurrent writer tidak menghasilkan nomor version yang sama. Isi JSONB divalidasi oleh schema registry sebelum disimpan.

## Generated file storage

HTML prototype, uploaded document, dan exported Markdown disimpan melalui `FileStorageService`. Business logic hanya mengetahui storage key dan metadata; ia tidak menggunakan `Path` atau filesystem API.

Development memakai `LocalFileStorageService` dengan root directory terkonfigurasi dan perlindungan path traversal. Docker menyimpan file pada named volume `generated_files`. Implementasi S3-compatible dapat mengganti adapter tanpa mengubah use case.

Phase 6 memakai abstraction ini untuk setiap self-contained prototype screen. Storage key memuat project, requirement, dan unique generation ID; `UI_PROTOTYPE` ArtifactVersion menyimpan immutable manifest. Browser membaca file melalui project/requirement/artifact/version-scoped endpoint, bukan melalui arbitrary storage key.

Phase 8 menyimpan JSON, Markdown, dan Trello-ready JSON pada unique handoff generation path. `handoff_package_versions` menyimpan storage key setiap format, canonical content JSON, source-version snapshot, serta Development Task version. Package revision tidak menimpa file lama.

## Integrity and safety

- Storage key tidak boleh keluar dari configured root.
- Database menyimpan ownership/reference, content type, size, dan kemudian checksum bila file artifact diperkenalkan.
- Delete mengikuti retention/audit policy; artifact version tidak dihapus sebagai bagian dari revisi biasa.
- Uploaded content harus divalidasi sebelum dipercaya atau diteruskan ke model.
