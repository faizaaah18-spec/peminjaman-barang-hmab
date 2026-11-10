"""Database SQLite dan logika sistem peminjaman barang HMJ Administrasi Bisnis."""

import hashlib
import hmac
import os
import sqlite3
from contextlib import contextmanager
from datetime import date
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "data_hmj.db"

KONDISI_BARANG = ["Baik", "Rusak Ringan", "Rusak Berat"]
KONDISI_KEMBALI = ["Baik", "Rusak Ringan", "Rusak Berat", "Hilang"]
STATUS = ["Berjalan", "Sebagian", "Selesai"]

USERNAME_DEFAULT = "admin"
PASSWORD_DEFAULT = "admin123"


def hash_password(password, salt=None):
    """Membuat hash PBKDF2 dengan salt acak: 'salt$hash'."""
    salt = salt or os.urandom(16).hex()
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), bytes.fromhex(salt), 100_000
    ).hex()
    return f"{salt}${digest}"


@contextmanager
def koneksi():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db(admin_username=USERNAME_DEFAULT, admin_password=PASSWORD_DEFAULT):
    with koneksi() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS barang (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                kode TEXT NOT NULL UNIQUE,
                nama TEXT NOT NULL,
                kategori TEXT NOT NULL,
                jumlah_total INTEGER NOT NULL DEFAULT 0 CHECK (jumlah_total >= 0),
                jumlah_tersedia INTEGER NOT NULL DEFAULT 0 CHECK (jumlah_tersedia >= 0),
                kondisi TEXT NOT NULL DEFAULT 'Baik',
                lokasi TEXT NOT NULL DEFAULT '-'
            );

            CREATE TABLE IF NOT EXISTS peminjam (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nama TEXT NOT NULL,
                nim TEXT NOT NULL UNIQUE,
                kelas TEXT NOT NULL,
                kontak TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS peminjaman (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                peminjam_id INTEGER NOT NULL REFERENCES peminjam(id),
                tujuan TEXT NOT NULL,
                tanggal_pinjam TEXT NOT NULL,
                batas_kembali TEXT NOT NULL,
                petugas TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'Berjalan',
                catatan TEXT NOT NULL DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS detail_peminjaman (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                peminjaman_id INTEGER NOT NULL
                    REFERENCES peminjaman(id) ON DELETE CASCADE,
                barang_id INTEGER NOT NULL REFERENCES barang(id),
                jumlah INTEGER NOT NULL CHECK (jumlah > 0),
                jumlah_kembali INTEGER NOT NULL DEFAULT 0,
                kondisi_awal TEXT NOT NULL DEFAULT '',
                kondisi_kembali TEXT NOT NULL DEFAULT '',
                tindak_lanjut TEXT NOT NULL DEFAULT '',
                tanggal_kembali TEXT NOT NULL DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS petugas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                nama TEXT NOT NULL,
                password TEXT NOT NULL
            );
            """
        )

        if conn.execute("SELECT COUNT(*) FROM petugas").fetchone()[0] == 0:
            conn.execute(
                "INSERT INTO petugas (username, nama, password) VALUES (?, ?, ?)",
                (admin_username.strip().lower(), "Administrator HMJ",
                 hash_password(admin_password)),
            )

        if conn.execute("SELECT COUNT(*) FROM barang").fetchone()[0] == 0:
            conn.executemany(
                """INSERT INTO barang
                   (kode, nama, kategori, jumlah_total, jumlah_tersedia, kondisi, lokasi)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                [
                    ("BRG-001", "Proyektor Epson", "Elektronik", 2, 2, "Baik", "Lemari Sekretariat"),
                    ("BRG-002", "Kabel HDMI 10 meter", "Elektronik", 3, 3, "Baik", "Lemari Sekretariat"),
                    ("BRG-003", "Mikrofon Wireless", "Elektronik", 2, 2, "Baik", "Lemari Sekretariat"),
                    ("BRG-004", "Speaker Aktif", "Elektronik", 2, 2, "Baik", "Gudang HMJ"),
                    ("BRG-005", "Kamera DSLR", "Dokumentasi", 1, 1, "Baik", "Lemari Sekretariat"),
                    ("BRG-006", "Tripod Kamera", "Dokumentasi", 2, 2, "Baik", "Gudang HMJ"),
                    ("BRG-007", "Standing Banner", "Perlengkapan Acara", 4, 4, "Baik", "Gudang HMJ"),
                    ("BRG-008", "Tenda Lipat", "Perlengkapan Acara", 2, 2, "Baik", "Gudang HMJ"),
                    ("BRG-009", "Kabel Extension", "Elektronik", 3, 3, "Baik", "Gudang HMJ"),
                    ("BRG-010", "Printer Portable", "Elektronik", 1, 1, "Rusak Ringan", "Lemari Sekretariat"),
                ],
            )

        if conn.execute("SELECT COUNT(*) FROM peminjam").fetchone()[0] == 0:
            conn.executemany(
                """INSERT INTO peminjam (nama, nim, kelas, kontak)
                   VALUES (?, ?, ?, ?)""",
                [
                    ("Abidhah Nur Faizah", "3.51.25.1.01", "AB 1A", "0812-0000-0001"),
                    ("Balindra Salwa Deepsidarta", "3.51.25.1.06", "AB 1B", "0812-0000-0002"),
                    ("Gabriella Gladis A. A.", "3.51.25.1.13", "AB 1A", "0812-0000-0003"),
                ],
            )


# ---------------------------------------------------------------------------
# Login petugas
# ---------------------------------------------------------------------------

def verifikasi_login(username, password):
    """Mengembalikan data petugas jika username dan password benar."""
    with koneksi() as conn:
        petugas = conn.execute(
            "SELECT * FROM petugas WHERE username = ?",
            (username.strip().lower(),),
        ).fetchone()

    if petugas is None:
        return None

    salt, tersimpan = petugas["password"].split("$", 1)
    dicek = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), bytes.fromhex(salt), 100_000
    ).hex()
    if hmac.compare_digest(tersimpan, dicek):
        return petugas
    return None


# ---------------------------------------------------------------------------
# Data barang
# ---------------------------------------------------------------------------

def list_barang(cari=""):
    with koneksi() as conn:
        sql = "SELECT * FROM barang"
        params = ()
        if cari.strip():
            sql += " WHERE kode LIKE ? OR nama LIKE ? OR kategori LIKE ? OR lokasi LIKE ?"
            pola = f"%{cari.strip()}%"
            params = (pola, pola, pola, pola)
        sql += " ORDER BY kode"
        return conn.execute(sql, params).fetchall()


def get_barang(barang_id):
    with koneksi() as conn:
        return conn.execute("SELECT * FROM barang WHERE id = ?", (barang_id,)).fetchone()


def tambah_barang(kode, nama, kategori, jumlah_total, kondisi, lokasi):
    with koneksi() as conn:
        try:
            conn.execute(
                """INSERT INTO barang
                   (kode, nama, kategori, jumlah_total, jumlah_tersedia, kondisi, lokasi)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (kode.strip(), nama.strip(), kategori.strip(), int(jumlah_total),
                 int(jumlah_total), kondisi, lokasi.strip()),
            )
        except sqlite3.IntegrityError:
            raise ValueError(f"Kode barang '{kode}' sudah digunakan.")


def ubah_barang(barang_id, kode, nama, kategori, jumlah_total, kondisi, lokasi):
    with koneksi() as conn:
        lama = conn.execute(
            "SELECT jumlah_total, jumlah_tersedia FROM barang WHERE id = ?", (barang_id,)
        ).fetchone()
        if lama is None:
            raise ValueError("Barang tidak ditemukan.")

        sedang_dipinjam = lama["jumlah_total"] - lama["jumlah_tersedia"]
        if int(jumlah_total) < sedang_dipinjam:
            raise ValueError(
                f"Jumlah total tidak boleh kurang dari {sedang_dipinjam} unit "
                "yang sedang dipinjam."
            )
        try:
            conn.execute(
                """UPDATE barang SET kode = ?, nama = ?, kategori = ?, jumlah_total = ?,
                   jumlah_tersedia = ?, kondisi = ?, lokasi = ? WHERE id = ?""",
                (kode.strip(), nama.strip(), kategori.strip(), int(jumlah_total),
                 int(jumlah_total) - sedang_dipinjam, kondisi, lokasi.strip(), barang_id),
            )
        except sqlite3.IntegrityError:
            raise ValueError(f"Kode barang '{kode}' sudah digunakan.")


def hapus_barang(barang_id):
    with koneksi() as conn:
        try:
            conn.execute("DELETE FROM barang WHERE id = ?", (barang_id,))
        except sqlite3.IntegrityError:
            raise ValueError(
                "Barang tidak dapat dihapus karena sudah pernah dipakai dalam transaksi."
            )


# ---------------------------------------------------------------------------
# Data peminjam
# ---------------------------------------------------------------------------

def list_peminjam(cari=""):
    with koneksi() as conn:
        sql = "SELECT * FROM peminjam"
        params = ()
        if cari.strip():
            sql += " WHERE nama LIKE ? OR nim LIKE ? OR kelas LIKE ? OR kontak LIKE ?"
            pola = f"%{cari.strip()}%"
            params = (pola, pola, pola, pola)
        sql += " ORDER BY nama"
        return conn.execute(sql, params).fetchall()


def tambah_peminjam(nama, nim, kelas, kontak):
    with koneksi() as conn:
        try:
            conn.execute(
                "INSERT INTO peminjam (nama, nim, kelas, kontak) VALUES (?, ?, ?, ?)",
                (nama.strip(), nim.strip(), kelas.strip(), kontak.strip()),
            )
        except sqlite3.IntegrityError:
            raise ValueError(f"NIM '{nim}' sudah terdaftar.")


def ubah_peminjam(peminjam_id, nama, nim, kelas, kontak):
    with koneksi() as conn:
        try:
            conn.execute(
                "UPDATE peminjam SET nama = ?, nim = ?, kelas = ?, kontak = ? WHERE id = ?",
                (nama.strip(), nim.strip(), kelas.strip(), kontak.strip(), peminjam_id),
            )
        except sqlite3.IntegrityError:
            raise ValueError(f"NIM '{nim}' sudah terdaftar.")


def hapus_peminjam(peminjam_id):
    with koneksi() as conn:
        try:
            conn.execute("DELETE FROM peminjam WHERE id = ?", (peminjam_id,))
        except sqlite3.IntegrityError:
            raise ValueError(
                "Peminjam tidak dapat dihapus karena memiliki riwayat transaksi."
            )


# ---------------------------------------------------------------------------
# Peminjaman dan pengembalian
# ---------------------------------------------------------------------------

def buat_peminjaman(peminjam_id, tujuan, tanggal_pinjam, batas_kembali,
                    petugas, catatan, items):
    """items: list pasangan (barang_id, jumlah)."""
    if not items:
        raise ValueError("Pilih minimal satu barang yang akan dipinjam.")

    with koneksi() as conn:
        for barang_id, jumlah in items:
            barang = conn.execute(
                "SELECT nama, jumlah_tersedia FROM barang WHERE id = ?", (barang_id,)
            ).fetchone()
            if barang is None:
                raise ValueError("Barang yang dipilih tidak ditemukan.")
            if int(jumlah) < 1:
                raise ValueError(f"Jumlah barang '{barang['nama']}' minimal 1.")
            if int(jumlah) > barang["jumlah_tersedia"]:
                raise ValueError(
                    f"Stok '{barang['nama']}' tidak cukup. "
                    f"Tersedia {barang['jumlah_tersedia']} unit."
                )

        cursor = conn.execute(
            """INSERT INTO peminjaman
               (peminjam_id, tujuan, tanggal_pinjam, batas_kembali, petugas, status, catatan)
               VALUES (?, ?, ?, ?, ?, 'Berjalan', ?)""",
            (peminjam_id, tujuan.strip(), tanggal_pinjam, batas_kembali,
             petugas.strip(), catatan.strip()),
        )
        peminjaman_id = cursor.lastrowid

        for barang_id, jumlah in items:
            barang = conn.execute(
                "SELECT kondisi FROM barang WHERE id = ?", (barang_id,)
            ).fetchone()
            conn.execute(
                """INSERT INTO detail_peminjaman
                   (peminjaman_id, barang_id, jumlah, kondisi_awal)
                   VALUES (?, ?, ?, ?)""",
                (peminjaman_id, barang_id, int(jumlah), barang["kondisi"]),
            )
            conn.execute(
                "UPDATE barang SET jumlah_tersedia = jumlah_tersedia - ? WHERE id = ?",
                (int(jumlah), barang_id),
            )

        return peminjaman_id


def list_peminjaman(status=None, cari=""):
    """status: list status yang ingin ditampilkan, mis. ['Berjalan', 'Terlambat']."""
    hari_ini = date.today().isoformat()
    pola = f"%{cari.strip()}%" if cari.strip() else "%"
    sql = """
        SELECT * FROM (
            SELECT p.id, p.peminjam_id, p.tujuan, p.tanggal_pinjam, p.batas_kembali,
                   p.petugas, p.status, p.catatan,
                   m.nama, m.nim, m.kelas, m.kontak,
                   (SELECT COUNT(*) FROM detail_peminjaman d
                    WHERE d.peminjaman_id = p.id) AS jenis_barang,
                   (SELECT COALESCE(SUM(d.jumlah), 0) FROM detail_peminjaman d
                    WHERE d.peminjaman_id = p.id) AS total_barang,
                   (SELECT COALESCE(SUM(d.jumlah - d.jumlah_kembali), 0)
                    FROM detail_peminjaman d
                    WHERE d.peminjaman_id = p.id) AS sisa_barang,
                   (SELECT COUNT(*) FROM detail_peminjaman d
                    JOIN barang b ON b.id = d.barang_id
                    WHERE d.peminjaman_id = p.id
                      AND (b.nama LIKE ? OR b.kode LIKE ?)) AS cocok_barang,
                   CASE
                       WHEN p.status = 'Selesai' THEN 'Selesai'
                       WHEN p.batas_kembali < ? THEN 'Terlambat'
                       ELSE p.status
                   END AS status_tampil,
                   CASE
                       WHEN p.status <> 'Selesai' AND p.batas_kembali < ?
                       THEN CAST(julianday(?) - julianday(p.batas_kembali) AS INTEGER)
                       ELSE 0
                   END AS hari_terlambat
            FROM peminjaman p
            JOIN peminjam m ON m.id = p.peminjam_id
        ) WHERE 1 = 1
    """
    params = [pola, pola, hari_ini, hari_ini, hari_ini]

    if status:
        tanda = ",".join("?" for _ in status)
        sql += f" AND status_tampil IN ({tanda})"
        params.extend(status)

    if cari.strip():
        sql += (
            " AND (nama LIKE ? OR nim LIKE ? OR tujuan LIKE ? OR petugas LIKE ?"
            " OR cocok_barang > 0)"
        )
        params.extend([pola, pola, pola, pola])

    sql += " ORDER BY id DESC"

    with koneksi() as conn:
        return conn.execute(sql, params).fetchall()


def list_peminjaman_aktif():
    return list_peminjaman(status=["Berjalan", "Sebagian", "Terlambat"])


def get_peminjaman(peminjaman_id):
    with koneksi() as conn:
        return conn.execute(
            """SELECT p.*, m.nama, m.nim, m.kelas, m.kontak,
                      (SELECT COALESCE(SUM(d.jumlah - d.jumlah_kembali), 0)
                       FROM detail_peminjaman d
                       WHERE d.peminjaman_id = p.id) AS sisa_barang
               FROM peminjaman p
               JOIN peminjam m ON m.id = p.peminjam_id
               WHERE p.id = ?""",
            (peminjaman_id,),
        ).fetchone()


def detail_peminjaman(peminjaman_id):
    with koneksi() as conn:
        return conn.execute(
            """SELECT d.*, b.kode, b.nama, b.kategori,
                      (d.jumlah - d.jumlah_kembali) AS sisa
               FROM detail_peminjaman d
               JOIN barang b ON b.id = d.barang_id
               WHERE d.peminjaman_id = ?
               ORDER BY d.id""",
            (peminjaman_id,),
        ).fetchall()


def proses_pengembalian(peminjaman_id, tanggal_kembali, items):
    """items: list dict {detail_id, jumlah, kondisi, tindak_lanjut}."""
    with koneksi() as conn:
        peminjaman = conn.execute(
            "SELECT * FROM peminjaman WHERE id = ?", (peminjaman_id,)
        ).fetchone()
        if peminjaman is None:
            raise ValueError("Transaksi tidak ditemukan.")
        if peminjaman["status"] == "Selesai":
            raise ValueError("Transaksi ini sudah selesai.")

        ada_item = False
        for item in items:
            jumlah = int(item["jumlah"])
            if jumlah <= 0:
                continue

            detail = conn.execute(
                """SELECT d.*, b.nama FROM detail_peminjaman d
                   JOIN barang b ON b.id = d.barang_id
                   WHERE d.id = ? AND d.peminjaman_id = ?""",
                (item["detail_id"], peminjaman_id),
            ).fetchone()
            if detail is None:
                raise ValueError("Rincian barang tidak ditemukan.")

            sisa = detail["jumlah"] - detail["jumlah_kembali"]
            if jumlah > sisa:
                raise ValueError(
                    f"Jumlah pengembalian '{detail['nama']}' melebihi sisa ({sisa} unit)."
                )

            ada_item = True
            kondisi = item["kondisi"]
            tindak_lanjut = item.get("tindak_lanjut", "").strip()

            if kondisi == "Hilang":
                # Barang hilang: stok total berkurang, tidak menambah stok tersedia.
                conn.execute(
                    "UPDATE barang SET jumlah_total = MAX(jumlah_total - ?, 0) WHERE id = ?",
                    (jumlah, detail["barang_id"]),
                )
            else:
                conn.execute(
                    "UPDATE barang SET jumlah_tersedia = jumlah_tersedia + ? WHERE id = ?",
                    (jumlah, detail["barang_id"]),
                )
                if kondisi != "Baik":
                    conn.execute(
                        "UPDATE barang SET kondisi = ? WHERE id = ?",
                        (kondisi, detail["barang_id"]),
                    )

            conn.execute(
                """UPDATE detail_peminjaman
                   SET jumlah_kembali = jumlah_kembali + ?,
                       kondisi_kembali = ?,
                       tindak_lanjut = ?,
                       tanggal_kembali = ?
                   WHERE id = ?""",
                (jumlah, kondisi, tindak_lanjut or detail["tindak_lanjut"],
                 tanggal_kembali, detail["id"]),
            )

        if not ada_item:
            raise ValueError("Isi jumlah barang yang dikembalikan minimal 1 unit.")

        total = conn.execute(
            "SELECT COALESCE(SUM(jumlah), 0) FROM detail_peminjaman WHERE peminjaman_id = ?",
            (peminjaman_id,),
        ).fetchone()[0]
        kembali = conn.execute(
            """SELECT COALESCE(SUM(jumlah_kembali), 0) FROM detail_peminjaman
               WHERE peminjaman_id = ?""",
            (peminjaman_id,),
        ).fetchone()[0]

        if kembali >= total:
            status = "Selesai"
        elif kembali > 0:
            status = "Sebagian"
        else:
            status = "Berjalan"

        conn.execute(
            "UPDATE peminjaman SET status = ? WHERE id = ?", (status, peminjaman_id)
        )
        return status


# ---------------------------------------------------------------------------
# Dashboard dan laporan
# ---------------------------------------------------------------------------

def statistik():
    hari_ini = date.today().isoformat()
    with koneksi() as conn:
        barang = conn.execute(
            """SELECT COUNT(*) AS jenis,
                      COALESCE(SUM(jumlah_total), 0) AS total,
                      COALESCE(SUM(jumlah_tersedia), 0) AS tersedia
               FROM barang"""
        ).fetchone()
        dipinjam = conn.execute(
            """SELECT COALESCE(SUM(d.jumlah - d.jumlah_kembali), 0)
               FROM detail_peminjaman d
               JOIN peminjaman p ON p.id = d.peminjaman_id
               WHERE p.status <> 'Selesai'"""
        ).fetchone()[0]
        berjalan = conn.execute(
            "SELECT COUNT(*) FROM peminjaman WHERE status <> 'Selesai'"
        ).fetchone()[0]
        terlambat = conn.execute(
            """SELECT COUNT(*) FROM peminjaman
               WHERE status <> 'Selesai' AND batas_kembali < ?""",
            (hari_ini,),
        ).fetchone()[0]
        return {
            "jenis_barang": barang["jenis"],
            "total_unit": barang["total"],
            "tersedia": barang["tersedia"],
            "dipinjam": dipinjam,
            "transaksi_berjalan": berjalan,
            "terlambat": terlambat,
        }


def laporan_inventaris():
    with koneksi() as conn:
        return conn.execute(
            """SELECT kode, nama, kategori, jumlah_total AS total,
                      jumlah_tersedia AS tersedia,
                      (jumlah_total - jumlah_tersedia) AS dipinjam,
                      kondisi, lokasi
               FROM barang ORDER BY kode"""
        ).fetchall()


def laporan_transaksi():
    """Riwayat peminjaman sampai tingkat barang."""
    with koneksi() as conn:
        return conn.execute(
            """SELECT p.id AS transaksi, m.nama AS peminjam, m.nim, m.kelas,
                      b.kode, b.nama AS barang, d.jumlah,
                      d.jumlah_kembali AS kembali,
                      (d.jumlah - d.jumlah_kembali) AS sisa,
                      d.kondisi_awal, d.kondisi_kembali,
                      d.tindak_lanjut, d.tanggal_kembali,
                      p.tanggal_pinjam, p.batas_kembali, p.tujuan,
                      p.petugas, p.status
               FROM detail_peminjaman d
               JOIN peminjaman p ON p.id = d.peminjaman_id
               JOIN peminjam m ON m.id = p.peminjam_id
               JOIN barang b ON b.id = d.barang_id
               ORDER BY p.id DESC, d.id"""
        ).fetchall()
