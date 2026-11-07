# Deploy SpaceForge AI ke Vercel

Repository ini menyediakan `vercel.json` untuk menjalankan Next.js dan FastAPI sebagai dua Vercel Services dalam satu project dan domain. Docker Compose tetap dipakai untuk development lokal. Database cloud berasal dari integrasi PostgreSQL di Marketplace.

## Langkah di dashboard

1. Masuk ke Vercel memakai akun GitHub `wahyupepep`, lalu import `wahyupepep/SpaceForge_AI`.
2. Gunakan **Root Directory `./`**, bukan `frontend/`. Konfigurasi `services` mengatur root dan build masing-masing service. Jangan menambahkan Build Command atau Framework override di tingkat project.
3. Hubungkan **Neon PostgreSQL** melalui Storage/Marketplace di project Vercel. Pilih paket yang sesuai, periksa harga/kuotanya sebelum menyetujui, dan hubungkan database ke environment Production. Integrasi menyediakan `DATABASE_URL`; jika tersedia, `DATABASE_URL_UNPOOLED` digunakan otomatis untuk migrasi.
4. Tambahkan `OPENAI_API_KEY` melalui **Settings → Environment Variables** untuk environment Production. Gunakan nilai dari `.env` lokal di dashboard yang aman, bukan melalui Git atau chat.
5. Deploy/redeploy setelah database dan API key tersedia. Jika import awal mencoba build sebelum database terhubung, build tersebut akan gagal; hubungkan integrasi, lalu redeploy.
6. Buka deployment, daftar akun pada `/login`, lalu uji pembuatan proyek, upload evidence, dan analisis. `/api/v1/health` harus menampilkan status database `ok`.

Gunakan database/branch terpisah untuk Preview, misalnya melalui dukungan branching integrasi Neon. Build menjalankan migrasi; jangan menghubungkan kode Preview yang belum dipercaya ke database Production. Environment Development di Vercel juga berbeda dari `.env` Docker lokal.

## Environment deployment

| Variable | Pengaturan |
| --- | --- |
| `DATABASE_URL` | Diisi integrasi PostgreSQL. URL `postgres://` dan `postgresql://` dikonversi otomatis untuk asyncpg, termasuk parameter TLS `sslmode`. |
| `DATABASE_URL_UNPOOLED` | Opsional; URL langsung dari integrasi untuk migrasi. |
| `OPENAI_API_KEY` | Secret server untuk AI. |
| `BACKEND_URL` | Jangan diisi manual pada Vercel Services; service binding menyediakannya otomatis. |
| `NEXT_PUBLIC_API_BASE_URL` | Tidak perlu diisi; default `/api/v1` mengakses API dalam domain frontend. Hapus override `localhost` lama jika ada. |

Jangan mengimpor seluruh `.env` Docker ke Vercel. Nilai seperti `db`, `http://backend:8000`, `/data/files`, dan cookie development tidak sesuai dengan deployment cloud.

Saat `VERCEL=1` disediakan platform, backend memakai default berikut jika variable terkait tidak di-override:

- `APP_ENV=production`, `AUTH_REQUIRED=true`, dan `AUTH_COOKIE_SECURE=true`.
- `FILE_STORAGE_BACKEND=database`: evidence dan prototype kecil disimpan dalam tabel PostgreSQL `stored_files`, bukan disk sementara instance. Evidence dibatasi 4 MiB; untuk file besar atau volume tinggi, gunakan adapter object storage di masa depan.
- `DATABASE_POOLING=false`: koneksi aplikasi tidak ditahan dalam pool lokal lintas invocation.
- `ORCHESTRATOR_MAX_STAGES_PER_REQUEST=1`: progres disimpan per tahap; browser melanjutkan request berikutnya sampai keputusan pengguna diperlukan.
- `OPENAI_TIMEOUT_SECONDS=75`, `OPENAI_MAX_RETRIES=0`, dan batas request 4.400.000 byte. Variable model dan batas token tetap dapat dikonfigurasi pada server.

`maxDuration` backend disetel ke 300 detik. Tahap flow, arsitektur teknis, dan prototype dijalankan dalam request terpisah. Jika provider AI timeout, periksa error lalu lanjutkan dari UI; retry otomatis yang memperpanjang satu invocation dinonaktifkan secara default.

Workflow ini membutuhkan tab terbuka untuk melanjutkan antar-request. Menutup tab menghentikan pengiriman tahap berikutnya; progres yang sudah tersimpan dapat dilanjutkan lagi. Ini belum merupakan antrean worker independen dari browser. Bila diperlukan eksekusi tanpa tab terbuka atau satu tahap AI melewati batas durasi, gunakan durable workflows/queue workers.

## Routing, login, dan akses proyek

`/api/*` dirutekan ke backend; path lain ke Next.js. Login, logout, download, dan prototype menggunakan domain publik yang sama. Cookie sesi `HttpOnly`, `SameSite=Lax`, dan `Secure` pada production dapat diterima browser dan diteruskan server Next.js ketika merender halaman.

Service binding mengisi `BACKEND_URL` untuk pemanggilan server ke backend. Frontend juga mempunyai rewrite `/api/*` untuk development native atau hosting backend terpisah; API dikecualikan dari redirect login pada Next.js proxy.

Dalam mode production, seluruh route proyek memerlukan sesi aktif. Route dengan `project_id`, termasuk requirement, AI, evidence, dan handoff, memeriksa kepemilikan proyek sebelum memanggil service. Health dan login/register tetap dapat diakses tanpa sesi.

## Migrasi dan penyimpanan

Build backend menjalankan `python -m app.db.migrate`. Runner memakai URL unpooled bila tersedia, mengambil PostgreSQL advisory lock untuk mencegah migrasi deployment bersamaan, lalu menjalankan Alembic hingga `head`. Build gagal jika database tidak tersedia atau migrasi gagal.

Migrasi `20261107_0014` menambahkan tabel `stored_files`. Pilihan storage database ditujukan untuk instalasi cloud baru. Mengubah backend storage pada instalasi lama tidak memindahkan file lokal secara otomatis; data lokal dan file yang dibutuhkan harus dimigrasikan secara terpisah.

Untuk Docker/native development, `FILE_STORAGE_BACKEND=local` tetap menjadi default. `.env.example` sekarang mengakses API lewat `/api/v1`; bila `.env` lama masih memakai URL API absolut, ubah ke `/api/v1` untuk mencoba alur proxy yang sama.

## Credential dan validasi

Secret ditempatkan di environment server. `NEXT_PUBLIC_*` masuk ke kode browser dan tidak boleh berisi secret. Environment project Vercel dibagikan ke service; source frontend tidak membaca API key atau credential database, dan nilainya tidak boleh dikembalikan melalui response.

`.gitignore`, `.dockerignore`, dan `.vercelignore` mengecualikan environment private, private key, dan beberapa nama credential umum. Template `.env.example` tetap terlacak Git. Aturan ignore tidak menghapus file yang sudah pernah di-commit; jika secret bocor, rotasi/revoke terlebih dahulu dan evaluasi pembersihan riwayat.

Audit awal pada 2026-11-07 terhadap tiga commit GitHub (318 blob unik), termasuk cadangan lokal, tidak menemukan file env private, private key, pola token provider umum, atau kecocokan secret panjang dari `.env` lokal. Audit ini terarah dan bukan jaminan semua format secret terdeteksi.

Pengujian backend memakai PostgreSQL disposable dengan `TEST_DATABASE_URL`, tanpa panggilan AI berbayar. Selain unit test, verifikasi deployment sebenarnya tetap diperlukan untuk integrasi Neon, cookie HTTPS, dan eksekusi AI. Lihat [Security](SECURITY.md) untuk batasan MVP seperti rate limiting dan pemulihan akun. Aktifkan Deployment Protection selama penyiapan/pengujian akses terbatas.

Referensi resmi diperiksa pada 2026-11-07:

- [Vercel Services](https://vercel.com/docs/services) — layanan ini masih beta.
- [Konfigurasi Services](https://vercel.com/docs/services/config-reference)
- [FastAPI di Vercel](https://vercel.com/docs/frameworks/backend/fastapi)
- [PostgreSQL melalui Marketplace](https://vercel.com/docs/postgres)
- [Batas Vercel Functions](https://vercel.com/docs/functions/limitations)
