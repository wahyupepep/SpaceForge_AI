# Project Context

## Latar belakang

Tim produk sering menerima kebutuhan software dalam bentuk percakapan, catatan singkat, atau dokumen yang tidak konsisten. System analyst kemudian harus menemukan konteks, mengklarifikasi ketidakpastian, memahami sistem yang sudah berjalan, dan menerjemahkan semuanya menjadi spesifikasi lintas fungsi. Proses manual ini penting tetapi lambat, sulit ditelusuri, dan hasilnya sangat bergantung pada pengalaman analis.

## Masalah yang diselesaikan

SpaceForge AI mengurangi jarak antara ide bisnis dan pekerjaan engineering. Sistem membantu mencegah requirement ambigu, keputusan yang tidak memiliki dasar, hilangnya aturan bisnis, desain teknis yang dibuat terlalu dini, dan test yang tidak dapat ditelusuri kembali ke kebutuhan awal.

## Konsep Virtual System Analyst

SpaceForge AI bertindak sebagai Virtual System Analyst: sebuah workspace terpandu yang mengumpulkan konteks, mengajukan klarifikasi, menyusun analisis, mengusulkan solusi, dan menghasilkan artifact terstruktur. AI mendukung pekerjaan analisis; AI tidak menggantikan keputusan pemilik produk, subject-matter expert, system analyst, architect, atau developer.

## Target user

- Product owner dan business analyst yang perlu menajamkan kebutuhan.
- System analyst yang ingin mempercepat analisis dan menjaga konsistensi artifact.
- Engineering lead dan developer yang memerlukan handoff yang dapat ditindaklanjuti.
- QA analyst yang membutuhkan traceability dari requirement ke acceptance criteria dan test.
- Tim delivery kecil yang belum memiliki fungsi analisis khusus.

## Tujuan sistem

1. Mengubah input bebas menjadi requirement yang eksplisit dan tervalidasi.
2. Menjaga traceability dari konteks sampai development task.
3. Menempatkan persetujuan manusia pada keputusan yang berdampak besar.
4. Menghasilkan Development Handoff Package yang konsisten dan versioned.
5. Memungkinkan workflow dipulihkan, diaudit, dan direvisi tanpa kehilangan riwayat.

## Scope MVP

- Intake untuk `NEW_SYSTEM`, `NEW_FEATURE`, dan `ENHANCEMENT`.
- Requirement clarification dan readiness gate.
- Research dan analisis existing system.
- Solution design dengan approval manusia.
- Process flow, prototype HTML, desain database, dan spesifikasi API.
- Test scenario, acceptance criteria, consistency review, dan revision loop terbatas.
- Development Handoff Package dalam JSON dan Markdown.
- Workflow multi-agent yang persisten dan resumable.

## Out of scope MVP

- Mengimplementasikan aplikasi bisnis yang sedang dispesifikasikan.
- Men-deploy hasil rancangan ke production.
- Mengubah source code, database, atau API sistem target secara otomatis.
- Menggantikan legal, security, compliance, atau architecture review manusia.
- Integrasi langsung ke project-management tools seperti Trello.
- Pelatihan atau fine-tuning model sendiri.

## Development Handoff Package

Development Handoff Package adalah kumpulan artifact yang sudah melalui approval dan quality gate. Paket memuat project context, baseline requirement, research, analisis AS-IS, functional specification, flow TO-BE, prototype, database design, API specification, technical specification, test scenario, acceptance criteria, dan development task yang dependency-aware. Setiap bagian memiliki versi dan referensi ke requirement sumbernya.

## Konsep multi-agent

Setiap agent adalah specialist dengan satu responsibility dan kontrak input/output yang jelas. Agent berkomunikasi melalui artifact terstruktur, bukan percakapan bebas sebagai state utama. Orchestrator mengatur urutan, gate, retry, dan revision routing; ia tidak mengambil alih tanggung jawab specialist.

## Human approval

Keputusan solusi memerlukan approval eksplisit sebelum technical design dimulai. User dapat menyetujui, meminta revisi dengan catatan, atau menolak. Sistem harus menunjukkan apa yang disetujui, siapa yang melakukan aksi, versi yang terkena aksi, dan kapan aksi dilakukan.

## Structured artifact

Output penting harus mengikuti schema, tervalidasi sebelum disimpan, immutable per versi, dan memiliki status lifecycle. Narasi dapat menjadi bagian dari content, tetapi state workflow tidak boleh bergantung pada parsing teks bebas.

## Prinsip AS-IS sebelum TO-BE

Untuk `ENHANCEMENT`, sistem wajib memahami current flow, actor, business rule, masalah, dan requested change sebelum mengusulkan TO-BE. Bila konteks AS-IS belum cukup, workflow berhenti pada klarifikasi. Artifact TO-BE selalu mempertahankan hubungan eksplisit dengan baseline AS-IS dan gap yang hendak ditutup.

## Project context gate

Project dimulai sebagai `DRAFT`. Submission ke requirement analysis mengevaluasi context di backend. `NEW_SYSTEM` dan `NEW_FEATURE` dapat menjadi `READY_FOR_ANALYSIS` setelah informasi inti tersimpan. `ENHANCEMENT` hanya dapat menjadi ready bila current flow, current actors, current business rules, current problem, dan requested change semuanya terisi. Submission yang gagal disimpan sebagai `CONTEXT_INCOMPLETE`; TO-BE tetap terlarang.
