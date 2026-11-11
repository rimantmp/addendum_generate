# Sistem Otomatisasi Dokumen Addendum & SPJB Pupuk Bersubsidi

Sistem berbasis **Python, Flask, SQLAlchemy & SQLite** untuk mengelola data perjanjian distribusi pupuk bersubsidi, menghasilkan dokumen Addendum resmi dan Surat Perjanjian Jual Beli (SPJB) secara otomatis dalam format **PDF** (ReportLab) dan **Microsoft Word (DOCX)** dengan layout presisi 100% sesuai standar kantor distributor pupuk.

---

## 📌 Fitur Utama

1. **Integrasi Database Relasional (SQLite / SQLAlchemy)**:
   - Master Pihak Pertama (Distributor / CV)
   - Master Pihak Kedua (Kios / Pengecer Resmi) dengan kode kios otomatis (`K-xxx`) dan nomor SPJB
   - Master Jenis Pupuk dengan urutan baku: `UREA, NPK, SP36, ORGANIK`
   - Master Dasar Hukum (SK Realokasi Dinas Pertanian Kabupaten & Provinsi)
   - Matriks Kuota Alokasi 12 Bulan Multi-Kecamatan

2. **Dukungan Kios Multi-Kecamatan (Lampiran 2 & Rekapitulasi)**:
   - Satu kios dapat melayani banyak wilayah kecamatan.
   - Lampiran 2 otomatis membuat tabel 12 bulan terpisah untuk masing-masing kecamatan.
   - Halaman rekapitulasi total otomatis dibuat jika kios melayani lebih dari satu kecamatan.

3. **Dokumen SPJB & Addendum Otomatis**:
   - **Addendum**: Menghasilkan dokumen resmi Addendum (PDF & DOCX) lengkap dengan nomor surat otomatis, konsiderans hukum yang ringkas, dan klausul berlakunya.
   - **SPJB Pokok**: Menghasilkan Surat Perjanjian Jual Beli Pokok per kios (PDF & DOCX) tanpa pasal-pasal panjang, siap cetak dan bermaterai.
   - **Masa Berlaku Dinamis**: Batas akhir masa berlaku SPJB (Poin A) dapat diatur dan diubah kapan saja.

4. **Salin & Tempel Langsung dari Excel (*Copy-Paste from Excel*)**:
   - Tempel data alokasi bulanan langsung ke sel input tabel (*Spreadsheet Mode*).
   - Fitur modal *Paste dari Excel* dengan pratinjau langsung 12 bulan dan pembersihan desimal otomatis.
   - Perhitungan subtotal dan grand total secara *real-time*.

5. **Backup & Pemulihan Database (*Backup & Restore*)**:
   - Unduh cadangan biner SQLite (`.db`) dengan *Online Backup API* yang aman.
   - Unduh skrip dump query SQL (`.sql`).
   - Buat titik pemulihan lokal (*server snapshots*) dan pulihkan data kapan saja dengan perlindungan snapshot darurat otomatis.

6. **Antarmuka Enterprise Sidenav**:
   - Desain antarmuka modern, cepat, dan mudah digunakan oleh staf kantor.
   - Pencarian instan kios, filter tabel real-time, dan indikator status database.

---

## 🚀 Cara Menjalankan Aplikasi

Pastikan Python telah terpasang, lalu jalankan:

```bash
# 1. Jalankan aplikasi web
python app.py
```

Setelah server aktif, buka browser dan akses alamat:
👉 **`http://127.0.0.1:5000`**

---

## 🧪 Pengujian Otomatis

Untuk menjalankan suite pengujian sistem:

```bash
python verify_app.py
```

