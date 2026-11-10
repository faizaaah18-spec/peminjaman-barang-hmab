# Sistem Peminjaman Barang HMJ Administrasi Bisnis

Aplikasi sederhana berbasis **Streamlit + SQLite** untuk mengelola inventaris,
peminjaman, dan pengembalian barang HMJ Administrasi Bisnis Politeknik Negeri
Semarang. Aplikasi dilindungi dengan **login petugas**.

## Fitur

- Login petugas/pengurus HMJ sebelum mengakses aplikasi.
- Dashboard ringkasan inventaris, transaksi berjalan, dan keterlambatan.
- Pengelolaan data barang: kode, nama, kategori, jumlah, kondisi, lokasi.
- Pengelolaan data peminjam: nama, NIM, kelas/prodi, kontak.
- Pencatatan peminjaman dengan beberapa barang dalam satu transaksi.
- Pencatatan pengembalian beserta jumlah dan kondisi setelah digunakan.
- Stok tersedia otomatis berkurang saat dipinjam dan bertambah saat kembali.
- Penandaan transaksi terlambat dan pencatatan tindak lanjut kerusakan/hilang.
- Riwayat transaksi dengan filter status, pencarian, dan periode.
- Laporan inventaris, transaksi terlambat, dan riwayat peminjaman (unduh CSV).

## Akun Login Bawaan

| Username | Password |
|---|---|
| `admin` | `admin123` |

Akun dibuat otomatis saat database pertama kali dijalankan. Untuk deployment
publik, ganti kredensial lewat **Streamlit Secrets** (lihat bagian Deploy)
sebelum aplikasi pertama kali dijalankan.

## Cara Menjalankan

Virtual environment sudah dibuat di folder `.venv`.

```powershell
# 1. Aktifkan virtual environment
.\.venv\Scripts\Activate.ps1

# 2. Instal dependensi (jika belum)
pip install -r requirements.txt

# 3. Jalankan aplikasi
streamlit run app.py
```

Tanpa mengaktifkan venv:

```powershell
.\.venv\Scripts\streamlit.exe run app.py
```

Aplikasi akan terbuka di `http://localhost:8501`.

## Struktur File

| File | Keterangan |
|---|---|
| `app.py` | Tampilan, login, dan navigasi Streamlit |
| `db.py` | Skema SQLite dan logika data |
| `data_hmj.db` | Database (dibuat otomatis saat pertama dijalankan) |
| `requirements.txt` | Dependensi Python |

## Deploy ke Streamlit Community Cloud

1. Buat repository baru di GitHub, lalu unggah folder ini (tanpa `.venv` dan
   `data_hmj.db`, keduanya sudah masuk `.gitignore`).
2. Buka [share.streamlit.io](https://share.streamlit.io), login dengan GitHub,
   lalu klik **Create app**.
3. Pilih repository, branch `main`, dan **Main file path**: `app.py`.
4. (Disarankan) Buka **Advanced settings → Secrets**, lalu isi:

   ```toml
   ADMIN_USERNAME = "admin"
   ADMIN_PASSWORD = "password-baru-yang-kuat"
   ```

   Salin contohnya dari `.streamlit/secrets.toml.example`.
5. Klik **Deploy**. Setelah selesai, aplikasi mendapat URL publik
   `https://nama-app.streamlit.app` yang bisa dibuka siapa saja.

### Penting: penyimpanan data

Streamlit Community Cloud memakai filesystem sementara. File `data_hmj.db`
bisa kembali ke data awal ketika aplikasi tidur, restart, atau di-redeploy.
Untuk demo/tugas ini biasanya cukup. Jika data harus permanen, gunakan
database eksternal (misalnya Supabase/PostgreSQL) atau platform dengan
persistent disk.

## Catatan

- Database otomatis dibuat dan diisi contoh barang/peminjam saat aplikasi
  pertama kali dijalankan.
- Untuk mengulang dari data kosong, hentikan aplikasi lalu hapus
  `data_hmj.db` (akun `admin` akan dibuat ulang).
- Barang/peminjam yang sudah dipakai dalam transaksi tidak dapat dihapus agar
  riwayat tetap utuh.
