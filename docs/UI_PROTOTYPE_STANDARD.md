# UI Prototype Standard

## Purpose and gate

UI Prototype adalah executable specification setelah exact current Solution version disetujui dan Process Flow tervalidasi. Ia membantu user memeriksa screen, navigation, state, dan interaction tanpa mengimplementasikan aplikasi target.

## Source standard

Setiap screen merupakan file `.html` mandiri yang:

- memakai semantic HTML;
- menyertakan CSS melalui `<style>` dan vanilla JavaScript melalui `<script>`;
- dapat dibuka langsung di browser dan memakai sample/in-memory state saja;
- tidak memakai framework, remote asset, external link, data URL, network call, atau image mockup;
- menggunakan filename lowercase yang aman, misalnya `list.html`, `form.html`, `detail.html`, atau `approval.html`;
- menyebut minimal satu requirement reference.

Screen dapat bernavigasi ke filename prototype lain dengan relative link. Prototype bukan production UI dan bukan source implementation.

## Artifact and file storage

Raw HTML disimpan melalui `FileStorageService` pada unique generation path. `UI_PROTOTYPE` artifact menyimpan manifest filename, title, purpose, storage key, content type, size, requirement references, interaction summary, dan aggregate traceability.

Revision membuat ArtifactVersion baru dan file lama tidak ditimpa. Jika persistence gagal, file dari attempt tersebut dibersihkan.

## Browser isolation

Endpoint file mengembalikan HTML dengan CSP sandbox. Inline CSS dan JavaScript diizinkan agar prototype bekerja, tetapi network connection, remote resource, image, object, dan base URL dinonaktifkan. Response juga memakai `nosniff` dan `no-referrer`.

## Traceability

Setiap screen harus terkait dengan Requirement Baseline. Interaction dan navigation harus dapat dipetakan ke main, alternative, atau exception flow. Unsupported behavior tidak boleh diperkenalkan sebagai requirement baru.
