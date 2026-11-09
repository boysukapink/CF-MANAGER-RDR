# Cloudflare Redirect Manager (Windows Standalone EXE)

Aplikasi desktop Windows mandiri (*standalone executable*) untuk mengelola aturan **Cloudflare Single Redirects (URL Forwarding)** secara langsung melalui Cloudflare API resmi menggunakan protokol HTTPS aman.

Aplikasi ini dirancang khusus untuk administrator web, marketer, dan pengguna nonteknis yang membutuhkan manajemen redirect domain berkecepatan tinggi, aman, dan tanpa perantara pihak ketiga.

---

## 🔒 Kebijakan Keamanan Kredensial & Privasi (Zero-Storage Policy)

Keamanan API Token adalah prioritas utama aplikasi ini:

1. **Tanpa Persistensi Disk:**
   Token API Cloudflare **tidak pernah** ditulis ke file disk, database SQLite, file JSON, YAML, TOML, INI, file `.env`, Windows Registry, Local Storage, maupun cache lokal.
2. **In-Memory Only:**
   Token hanya disimpan dalam memori RAM proses aktif selama sesi berjalan dalam buffer bita (*bytearray*).
3. **Pembersihan Seketika (*Explicit Zeroing*):**
   Saat tombol **Disconnect** ditekan atau jendela aplikasi ditutup, buffer memori token secara eksplisit ditimpa dengan nilai bita nol (`0x00`), semua referensi objek dihapus, dan koneksi HTTP ditutup seketika.
4. **Verifikasi TLS Ketat:**
   Seluruh komunikasi jaringan menggunakan HTTPX dengan verifikasi sertifikat SSL/TLS aktif penuh (`verify=True`). Penerusan otomatis otorisasi header ke host eksternal dinonaktifkan (`follow_redirects=False`).
5. **Transparansi Memori Python:**
   Python mengelola memori melalui *garbage collection* dan *string interning*. Meskipun buffer bita ditimpa dengan nol saat disconnect, salinan string sementara dalam memori proses dapat bertahan hingga proses aplikasi Windows ditutup sepenuhnya oleh sistem operasi. Aplikasi ini tidak menjanjikan jaminan penghapusan RAM 100% yang tidak realistis pada lingkungan runtime bahasa tingkat tinggi.

---

## 💻 Persyaratan Sistem

- **Sistem Operasi:** Windows 10 atau Windows 11 (64-bit)
- **Koneksi Internet:** Diperlukan untuk mengakses API Cloudflare (`https://api.cloudflare.com`)
- **Untuk Menjalankan File EXE:** Tidak memerlukan instalasi Python (semua dependensi sudah terintegrasi di dalam file `.exe`).
- **Untuk Membangun / Menjalankan dari Source Code:**
  - Python 3.12 atau yang lebih baru (64-bit)
  - pip (Python Package Installer)

---

## 🔑 Panduan Membuat Cloudflare API Token

Aplikasi ini menggunakan **Cloudflare Custom API Token** dengan prinsip izin terendah (*Least Privilege*). **Jangan pernah menggunakan Global API Key.**

### Langkah Pembuatan:
1. Masuk ke dashboard Cloudflare: [https://dash.cloudflare.com/profile/api-tokens](https://dash.cloudflare.com/profile/api-tokens)
2. Klik tombol **Create Token**.
3. Gulir ke bawah ke bagian **Custom Token**, lalu klik **Get started**.
4. Beri nama token, misalnya: `Redirect-Manager-Token`.
5. Atur izin (**Permissions**) minimum:
   - **Zone** &rarr; **Zone** &rarr; **Read** *(Diperlukan untuk membaca daftar domain dan Zone ID)*
   - **Zone** &rarr; **Single Redirect** &rarr; **Edit** *(Diperlukan untuk membaca, menambah, dan menghapus redirect)*
6. Atur **Zone Resources**:
   - Pilih **Include** &rarr; **Specific zone** &rarr; *(Pilih domain yang ingin Anda kelola)*.
   - *Catatan:* Anda dapat memilih *All zones* jika ingin mengelola seluruh domain dalam akun, namun membatasi domain spesifik jauh lebih aman jika token bocor.
7. Biarkan opsi **Client IP Address Filtering** dan **TTL** sesuai kebutuhan Anda.
8. Klik **Continue to summary**, kemudian klik **Create Token**.
9. Salin token yang dihasilkan dan simpan di pengelola sandi aman Anda. *(Cloudflare hanya menampilkan token ini satu kali)*.

> Referensi izin resmi Cloudflare: [Cloudflare API Permissions Reference](https://developers.cloudflare.com/fundamentals/api/reference/permissions/)

---

## 🚀 Cara Menjalankan dari Source Code

1. Buka PowerShell atau Command Prompt di folder proyek:
   ```powershell
   cd C:\Users\boy\Documents\CFMANAGER
   ```
2. Buat dan aktifkan virtual environment (opsional namun disarankan):
   ```powershell
   python -m venv venv
   .\venv\Scripts\activate
   ```
3. Pasang dependensi:
   ```powershell
   pip install -r requirements.txt
   ```
4. Jalankan aplikasi:
   ```powershell
   python src\main.py
   ```

---

## 🔨 Cara Membangun File Mandiri EXE (PyInstaller)

Proyek ini telah dilengkapi skrip otomatisasi satu-klik:

### Menggunakan Skrip Batch:
Cukup klik dua kali atau jalankan file:
```cmd
build_windows.bat
```

Skrip ini akan secara otomatis:
1. Memeriksa instalasi Python.
2. Menyiapkan virtual environment.
3. Menginstal semua dependensi dari `requirements.txt`.
4. Menjalankan seluruh pengujian unit (**pytest**).
5. Membangun executable mandiri tanpa konsol hitam (`--noconsole --onefile`).
6. Menghasilkan file di lokasi:
   ```
   dist\CloudflareRedirectManager.exe
   ```

---

## 📖 Panduan Penggunaan Aplikasi

### 1. Menghubungkan Banyak Akun Cloudflare (Multi-Account API)
- Buka menu **Connect API** pada sidebar kiri.
- Anda dapat menambahkan beberapa akun Cloudflare sekaligus:
  1. Masukkan **Label / Nama Akun** (misalnya: `Akun Utama`, `Akun Klien A`, `Akun PBN`).
  2. Masukkan **API Token Cloudflare** untuk akun tersebut.
  3. Klik **🔗 Hubungkan & Tambah Akun**.
- Aplikasi memverifikasi token ke Cloudflare API dan menyimpan token **hanya di RAM** dalam sesi multi-akun.
- Tabel akun menampilkan seluruh akun yang terhubung, statusnya, jumlah domain, dan tombol untuk:
  - **Gunakan Akun Ini:** Beralih ke akun tersebut sebagai akun aktif.
  - **Putuskan:** Menghapus akun tersebut dari RAM tanpa mempengaruhi akun lainnya.
  - **⚠️ Putuskan Semua Akun:** Menghapus dan menolkan (*zeroing*) semua token akun dari RAM seketika.
- Pada header bagian atas aplikasi, tersedia dropdown **Akun Aktif** untuk berganti akun secara instan kapan saja.

### 2. Melihat & Mencari Domain Lintas Akun (Domain Manager)
- Buka menu **Domains** di sidebar.
- Filter **Akun CF:** Pilih `Semua Akun` untuk melihat agregasi domain dari seluruh akun yang terhubung, atau pilih satu akun tertentu.
- Kolom tabel menampilkan **Nama Domain**, **Akun CF**, **Status**, **Paket Plan**, dan **Zone ID**.
- Klik tombol **Kelola Redirect** di baris domain mana pun untuk langsung diarahkan ke halaman Redirects untuk zona tersebut (aplikasi otomatis menyesuaikan akun yang sesuai).

### 3. Mengelola ALL INCOMING Redirect (301 & 302)
- Buka menu **Redirects** di sidebar.
- Pilih domain zona pada dropdown.
- Klik tombol **➕ Tambah Redirect** untuk membuka formulir:
  - **Cakupan Hostname Sumber:**
    - **Domain Utama & www (Keduanya):** Mengalihkan baik `domainlama.com` maupun `www.domainlama.com`.
    - **Domain Utama saja:** Hanya mengalihkan apex `domainlama.com`.
    - **www saja:** Hanya mengalihkan subdomain `www.domainlama.com`.
  - **URL Tujuan:** contoh `https://domainbaru.com/`.
  - **Status HTTP:**
    - **301 (Permanent Redirect):** Untuk migrasi permanen / SEO.
    - **302 (Temporary Redirect):** Disarankan untuk pengujian awal agar browser tidak menyimpan cache permanen.
  - **Opsi Pengalihan URL:**
    - **Preserve Path:** 
      - **ON:** Mengalihkan seluruh sub-path (`/promo`, `/login`, dll) ke path yang sama di domain tujuan (misal: `domainlama.com/promo` &rarr; `domainbaru.com/promo`).
      - **OFF:** Mengarahkan seluruh request dari halaman mana pun langsung ke halaman utama domain tujuan (`domainlama.com/promo` &rarr; `domainbaru.com/`).
    - **Preserve Query String:**
      - **ON:** Mempertahankan parameter query URL (misal: `?id=123&ref=abc`).
      - **OFF:** Menghapus parameter query string saat pengalihan.
    - **Status Rule:** Centang untuk langsung mengaktifkan (*Enabled*) atau simpan sebagai *Disabled*.
- Klik **Simpan ke Cloudflare**.

### 4. Bulk Redirect Manager (Batch URL Forwarding)
Tombol **⚡ Bulk Redirect** tersedia di menu **Domains** dan **Redirects** untuk mengonfigurasi banyak redirect sekaligus:
- **Tab 1: Pilih Banyak Domain Sekaligus**
  - Centang domain-domain yang ingin dialihkan.
  - Terdapat tombol **📋 Pilih dari Daftar Teks** untuk mencentang otomatis domain berdasarkan daftar nama domain yang ditempelkan (*paste*).
  - Tentukan satu URL Tujuan, status HTTP (301/302), dan cakupan (All Incoming / Apex & www).
  - Klik **Terapkan Bulk Redirect ke Domain Terpilih**.
- **Tab 2: Impor Teks / Format CSV**
  - Mendukung input hanya berupa daftar domain sumber (*satu per baris*). Cukup isi kolom **🎯 URL Tujuan Bersama**, lalu klik **Parse & Validasi**.
  - Tombol **⚡ Tempelkan Target ke Teks** otomatis menambahkan `-> [URL Tujuan]` ke setiap baris teks.
  - Mendukung format kustom per baris:
    - `domain1.com -> https://target.com/ [301/302]`
    - `domain2.com,https://target.com/,301` (CSV)
    - `domain3.com https://target.com/ 302`
- **Tab 3: Hapus Massal 301/302**
  - Membersihkan seluruh Single Redirects pada domain yang dipilih dengan aman.

### 5. Tombol Aksi pada Tabel Redirect
Tabel Redirect menyediakan kolom terstruktur:
`Source Domain | Mode | Destination URL | Status Code | Preserve Path | Status | Actions`
- **✏️ Edit:** Memperbarui parameter URL tujuan, status 301/302, preserve path/query, atau cakupan hostname pada aturan yang dipilih secara aman menggunakan Cloudflare API `PATCH`.
- **⚡ On/Off (Toggle Status):** Mengaktifkan (*Enable*) atau menonaktifkan (*Disable*) aturan tanpa menghapusnya.
- **🧪 Test (Simulasi & Live Probe):** 
  - Menguji logika transformasi URL secara instan (misal menguji apakah `https://domainlama.com/artikel?id=1` cocok dan kemana URL dialihkan).
  - Melakukan probe HTTP langsung (*Live HTTP Request*) untuk memeriksa apakah respons HTTP 301/302 dan header `Location` sudah aktif di jaringan Cloudflare.
- **🗑️ Hapus:** Menghapus aturan dengan konfirmasi aman. Aplikasi memverifikasi Rule ID sebelum penghapusan dan **hanya menghapus aturan tersebut tanpa menyentuh ruleset lain**.

### 6. Catatan Penting DNS Cloudflare (Proxy Status)
Agar Single Redirects dapat bekerja di Cloudflare:
- Pastikan hostname sumber (`domainlama.com` dan `www.domainlama.com`) memiliki **DNS Record (A atau CNAME)** yang aktif di Cloudflare Dashboard.
- Status proxy DNS wajib berada dalam kondisi **Proxied (Awan Oranye / Orange Cloud)** agar lalu lintas HTTP/HTTPS melewati edge server Cloudflare.

### 7. Memutuskan Koneksi (Disconnect & Zero-Memory)
- Klik tombol **Putuskan (Disconnect)** di menu **Connect API** atau tombol cepat **Putuskan** di header.
- Status akan berubah menjadi **Disconnected**, buffer token dinolkan dari RAM, dan seluruh data domain dihapus dari antarmuka.

### 8. Audit Log Sesi & Ekspor
- Buka menu **Keamanan & Privasi**.
- Riwayat seluruh tindakan selama aplikasi terbuka dapat dilihat.
- Anda dapat mengekspor log ke format **CSV** atau **JSON**.
- Log yang diekspor dijamin **bersih dari token**, otorisasi header, maupun kredensial rahasia.

---

## 🧪 Menjalankan Pengujian Unit (Unit Tests)

Jalankan perintah berikut:
```powershell
pytest -v
```

Cakupan pengujian:
- Validasi hostname & konversi IDNA (Punycode).
- Validasi URL tujuan & penolakan skema selain HTTP/HTTPS.
- Penolakan kredensial pengguna tersemat (`user:pass@host`).
- Penolakan karakter kontrol berbahaya.
- Pencegahan redirect loop ke domain yang sama.
- Pemilihan zona paling spesifik (*longest domain suffix match*).
- Pembentukan ekspresi Cloudflare Ruleset (*Root Mode* & *Preserve Path Mode*).
- Penanganan status 301 dan 302.
- Mocking respons HTTP (401 Unauthorized, 403 Forbidden, 404 Not Found, 429 Rate Limit, Network Timeout).
- Keamanan penghapusan aturan dengan verifikasi Rule ID.
- Siklus hidup sesi memori dan pembersihan saat keluar (*zeroing buffer*).
- Pengujian antarmuka GUI secara *offscreen*.

---

## 🛠️ Panduan Troubleshooting

| Masalah | Penyebab Umum | Solusi |
|---|---|---|
| **Windows SmartScreen muncul saat membuka EXE** | Aplikasi belum memiliki sertifikat Code Signing komersial (*unsigned binary*). | Klik tautan **More info** (*Informasi selengkapnya*) &rarr; klik tombol **Run anyway** (*Tetap jalankan*). |
| **Peringatan Antivirus / False Positive** | PyInstaller mengemas Python runtime ke dalam satu file binary, yang terkadang dicurigai oleh heuristik antivirus baru. | Masukkan file `CloudflareRedirectManager.exe` ke daftar pengecualian (*whitelist*) antivirus Anda atau bangun sendiri dari source code menggunakan `build_windows.bat`. |
| **Error: HTTP 401 Unauthorized** | Token salah diketik atau telah dicabut di Cloudflare Dashboard. | Buat token baru di [dash.cloudflare.com/profile/api-tokens](https://dash.cloudflare.com/profile/api-tokens) dan hubungkan kembali. |
| **Error: HTTP 403 Forbidden** | Izin API token kurang (*missing permissions*). | Pastikan token memiliki izin: `Zone -> Zone -> Read` dan `Zone -> Single Redirect -> Edit`. Periksa juga apakah Zone Resources mencakup domain yang Anda kelola. |
| **Domain tidak muncul di tabel** | Akun Cloudflare tidak memiliki zona, atau token dibatasi ke zona yang berbeda. | Buka Cloudflare Dashboard dan pastikan status domain adalah *Active*, serta token diberikan akses ke zona tersebut. |
| **Error: Timeout / Koneksi Gagal** | Firewall kantor, VPN, atau koneksi internet memblokir akses ke `api.cloudflare.com`. | Periksa koneksi internet Anda dan pastikan port 443 HTTPS terbuka tanpa interferensi proxy SSL. |

---

## 📜 Lisensi & Integritas Kode
Dibuat untuk pengelolaan Cloudflare yang aman, efisien, dan andal. Bebas digunakan dan dimodifikasi untuk kebutuhan operasional Anda.
