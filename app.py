"""Aplikasi Streamlit: Sistem Peminjaman Barang HMJ Administrasi Bisnis."""

from datetime import date, timedelta

import pandas as pd
import streamlit as st

import db

st.set_page_config(
    page_title="Peminjaman Barang HMJ",
    page_icon="📦",
    layout="wide",
)

def admin_dari_secrets():
    """Ambil akun admin dari Streamlit Secrets bila tersedia."""
    try:
        return (
            str(st.secrets.get("ADMIN_USERNAME", db.USERNAME_DEFAULT)),
            str(st.secrets.get("ADMIN_PASSWORD", db.PASSWORD_DEFAULT)),
        )
    except Exception:
        return db.USERNAME_DEFAULT, db.PASSWORD_DEFAULT


db.init_db(*admin_dari_secrets())

st.markdown(
    """
    <style>
        .block-container { padding-top: 1.8rem; }
        h1, h2, h3 { color: #123c63; }
        div[data-testid="stMetric"] {
            background: #f4f7fb;
            border: 1px solid #dde6f0;
            border-radius: 10px;
            padding: 12px 16px;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

if "flash" in st.session_state:
    pesan, ikon = st.session_state.pop("flash")
    st.success(pesan, icon=ikon)


# ---------------------------------------------------------------------------
# Login petugas
# ---------------------------------------------------------------------------

def halaman_login():
    st.title("📦 Sistem Peminjaman Barang HMJ")
    st.caption("HMJ Administrasi Bisnis · Politeknik Negeri Semarang")
    st.info(
        "Masuk sebagai petugas/pengurus HMJ untuk mengelola inventaris "
        "dan transaksi peminjaman."
    )

    with st.form("form_login"):
        username = st.text_input("Username", placeholder="admin")
        password = st.text_input("Password", type="password")
        masuk = st.form_submit_button("Masuk", type="primary",
                                      use_container_width=True)

    if masuk:
        petugas = db.verifikasi_login(username, password)
        if petugas is None:
            st.error("Username atau password salah.")
        else:
            st.session_state["petugas"] = {
                "id": petugas["id"],
                "username": petugas["username"],
                "nama": petugas["nama"],
            }
            st.rerun()

    st.caption("Hubungi pengurus HMJ jika belum memiliki akun petugas.")


if "petugas" not in st.session_state:
    halaman_login()
    st.stop()


# ---------------------------------------------------------------------------
# Pembantu tampilan
# ---------------------------------------------------------------------------

def flash(pesan, ikon="✅"):
    st.session_state["flash"] = (pesan, ikon)


def tanggal_indo(nilai):
    if not nilai:
        return "-"
    try:
        return date.fromisoformat(str(nilai)).strftime("%d-%m-%Y")
    except ValueError:
        return str(nilai)


def ke_dataframe(rows):
    return pd.DataFrame([dict(r) for r in rows])


def format_tanggal(df, kolom):
    for nama in kolom:
        if nama in df.columns:
            df[nama] = df[nama].map(tanggal_indo)
    return df


def unduh_csv(df, nama_file, key):
    st.download_button(
        "⬇️ Unduh CSV",
        df.to_csv(index=False).encode("utf-8-sig"),
        file_name=nama_file,
        mime="text/csv",
        key=key,
    )


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

def halaman_dashboard():
    st.header("🏠 Dashboard")
    st.caption("Ringkasan inventaris dan transaksi HMJ Administrasi Bisnis.")

    s = db.statistik()
    kolom = st.columns(5)
    kolom[0].metric("Jenis Barang", s["jenis_barang"])
    kolom[1].metric("Total Unit", s["total_unit"])
    kolom[2].metric("Tersedia", s["tersedia"])
    kolom[3].metric("Sedang Dipinjam", s["dipinjam"])
    kolom[4].metric("Transaksi Berjalan", s["transaksi_berjalan"])

    if s["terlambat"]:
        st.warning(
            f"⚠️ Ada **{s['terlambat']} transaksi** yang melewati batas waktu "
            "pengembalian. Segera tindak lanjuti."
        )
    else:
        st.info("✅ Tidak ada transaksi yang terlambat.")

    st.subheader("Transaksi Berjalan")
    loans = db.list_peminjaman_aktif()
    if not loans:
        st.caption("Belum ada transaksi berjalan.")
    else:
        df = ke_dataframe(loans)
        df["Keterangan"] = df["hari_terlambat"].map(
            lambda h: f"Terlambat {h} hari" if h > 0 else "-"
        )
        df = df.rename(
            columns={
                "id": "ID",
                "nama": "Peminjam",
                "nim": "NIM",
                "tujuan": "Tujuan",
                "tanggal_pinjam": "Tgl Pinjam",
                "batas_kembali": "Batas Kembali",
                "sisa_barang": "Sisa Barang",
                "status_tampil": "Status",
            }
        )
        df = format_tanggal(df, ["Tgl Pinjam", "Batas Kembali"])
        st.dataframe(
            df[["ID", "Peminjam", "NIM", "Tujuan", "Tgl Pinjam", "Batas Kembali",
                "Sisa Barang", "Status", "Keterangan"]],
            hide_index=True,
        )

    st.subheader("Barang Tidak Tersedia")
    habis = [b for b in db.list_barang() if b["jumlah_tersedia"] == 0]
    if not habis:
        st.caption("Semua jenis barang memiliki stok tersedia.")
    else:
        df = ke_dataframe(habis)[["kode", "nama", "kategori", "jumlah_total", "kondisi"]]
        df = df.rename(
            columns={
                "kode": "Kode",
                "nama": "Nama Barang",
                "kategori": "Kategori",
                "jumlah_total": "Total",
                "kondisi": "Kondisi",
            }
        )
        st.dataframe(df, hide_index=True)


# ---------------------------------------------------------------------------
# Data barang
# ---------------------------------------------------------------------------

def halaman_barang():
    st.header("📦 Data Barang")
    st.caption("Kelola kode, nama, kategori, jumlah, kondisi, dan lokasi inventaris.")

    tab_daftar, tab_tambah, tab_ubah = st.tabs(
        ["📋 Daftar Barang", "➕ Tambah Barang", "✏️ Ubah / Hapus"]
    )

    with tab_daftar:
        cari = st.text_input(
            "Cari barang", placeholder="Kode, nama, kategori, atau lokasi...",
            key="cari_barang",
        )
        rows = db.list_barang(cari)
        if not rows:
            st.info("Barang tidak ditemukan.")
        else:
            df = ke_dataframe(rows)
            df["Dipinjam"] = df["jumlah_total"] - df["jumlah_tersedia"]
            df = df.rename(
                columns={
                    "kode": "Kode",
                    "nama": "Nama Barang",
                    "kategori": "Kategori",
                    "jumlah_total": "Total",
                    "jumlah_tersedia": "Tersedia",
                    "kondisi": "Kondisi",
                    "lokasi": "Lokasi",
                }
            )
            st.dataframe(
                df[["Kode", "Nama Barang", "Kategori", "Total", "Tersedia",
                    "Dipinjam", "Kondisi", "Lokasi"]],
                hide_index=True,
            )
            unduh_csv(df, "data_barang.csv", "unduh_barang")

    with tab_tambah:
        with st.form("form_tambah_barang", clear_on_submit=True):
            kode = st.text_input("Kode Barang *", placeholder="Contoh: BRG-011")
            nama = st.text_input("Nama Barang *", placeholder="Contoh: Proyektor Mini")
            kategori = st.text_input("Kategori *", value="Elektronik")
            c1, c2 = st.columns(2)
            jumlah = c1.number_input("Jumlah Total *", min_value=1, value=1, step=1)
            kondisi = c2.selectbox("Kondisi *", db.KONDISI_BARANG)
            lokasi = st.text_input("Lokasi Penyimpanan *", value="Gudang HMJ")

            if st.form_submit_button("Simpan Barang", type="primary"):
                if not kode.strip() or not nama.strip() or not kategori.strip():
                    st.error("Kode, nama, dan kategori barang wajib diisi.")
                elif not lokasi.strip():
                    st.error("Lokasi penyimpanan wajib diisi.")
                else:
                    try:
                        db.tambah_barang(kode, nama, kategori, jumlah, kondisi, lokasi)
                        flash(f"Barang '{nama.strip()}' berhasil ditambahkan.")
                        st.rerun()
                    except ValueError as e:
                        st.error(str(e))

    with tab_ubah:
        rows = db.list_barang()
        if not rows:
            st.info("Belum ada data barang.")
        else:
            opsi = {b["id"]: f'{b["kode"]} — {b["nama"]}' for b in rows}
            pilihan = st.selectbox(
                "Pilih barang", list(opsi), format_func=lambda i: opsi[i],
                key="ubah_barang_pilih",
            )
            barang = db.get_barang(pilihan)

            with st.form("form_ubah_barang"):
                kode = st.text_input("Kode Barang *", value=barang["kode"])
                nama = st.text_input("Nama Barang *", value=barang["nama"])
                kategori = st.text_input("Kategori *", value=barang["kategori"])
                c1, c2 = st.columns(2)
                jumlah = c1.number_input(
                    "Jumlah Total *", min_value=1,
                    value=int(barang["jumlah_total"]), step=1,
                )
                kondisi = c2.selectbox(
                    "Kondisi *", db.KONDISI_BARANG,
                    index=db.KONDISI_BARANG.index(barang["kondisi"])
                    if barang["kondisi"] in db.KONDISI_BARANG else 0,
                )
                lokasi = st.text_input("Lokasi Penyimpanan *", value=barang["lokasi"])

                if st.form_submit_button("Simpan Perubahan", type="primary"):
                    if not kode.strip() or not nama.strip() or not kategori.strip():
                        st.error("Kode, nama, dan kategori barang wajib diisi.")
                    else:
                        try:
                            db.ubah_barang(
                                pilihan, kode, nama, kategori, jumlah, kondisi, lokasi
                            )
                            flash(f"Barang '{nama.strip()}' berhasil diperbarui.")
                            st.rerun()
                        except ValueError as e:
                            st.error(str(e))

            st.divider()
            st.markdown("**Hapus barang**")
            st.caption(
                "Barang yang sudah dipakai dalam transaksi tidak dapat dihapus."
            )
            konfirmasi = st.checkbox(
                f"Ya, hapus {barang['kode']} — {barang['nama']}",
                key="konfirmasi_hapus_barang",
            )
            if st.button("Hapus Barang", disabled=not konfirmasi,
                         key="tombol_hapus_barang"):
                try:
                    db.hapus_barang(pilihan)
                    flash(f"Barang '{barang['nama']}' berhasil dihapus.")
                    st.rerun()
                except ValueError as e:
                    st.error(str(e))


# ---------------------------------------------------------------------------
# Data peminjam
# ---------------------------------------------------------------------------

def halaman_peminjam():
    st.header("👥 Data Peminjam")
    st.caption("Identitas mahasiswa yang mengajukan peminjaman barang HMJ.")

    tab_daftar, tab_tambah, tab_ubah = st.tabs(
        ["📋 Daftar Peminjam", "➕ Tambah Peminjam", "✏️ Ubah / Hapus"]
    )

    with tab_daftar:
        cari = st.text_input(
            "Cari peminjam", placeholder="Nama, NIM, kelas, atau kontak...",
            key="cari_peminjam",
        )
        rows = db.list_peminjam(cari)
        if not rows:
            st.info("Peminjam tidak ditemukan.")
        else:
            df = ke_dataframe(rows)[["nama", "nim", "kelas", "kontak"]]
            df = df.rename(
                columns={
                    "nama": "Nama",
                    "nim": "NIM",
                    "kelas": "Kelas / Prodi",
                    "kontak": "Kontak",
                }
            )
            st.dataframe(df, hide_index=True)
            unduh_csv(df, "data_peminjam.csv", "unduh_peminjam")

    with tab_tambah:
        with st.form("form_tambah_peminjam", clear_on_submit=True):
            nama = st.text_input("Nama Lengkap *")
            c1, c2 = st.columns(2)
            nim = c1.text_input("NIM *", placeholder="3.51.25.1.xx")
            kelas = c2.text_input("Kelas / Program Studi *", placeholder="AB 1A")
            kontak = st.text_input("Kontak *", placeholder="No. HP / WhatsApp")

            if st.form_submit_button("Simpan Peminjam", type="primary"):
                if not all(x.strip() for x in [nama, nim, kelas, kontak]):
                    st.error("Semua kolom bertanda * wajib diisi.")
                else:
                    try:
                        db.tambah_peminjam(nama, nim, kelas, kontak)
                        flash(f"Peminjam '{nama.strip()}' berhasil ditambahkan.")
                        st.rerun()
                    except ValueError as e:
                        st.error(str(e))

    with tab_ubah:
        rows = db.list_peminjam()
        if not rows:
            st.info("Belum ada data peminjam.")
        else:
            opsi = {p["id"]: f'{p["nama"]} — {p["nim"]}' for p in rows}
            pilihan = st.selectbox(
                "Pilih peminjam", list(opsi), format_func=lambda i: opsi[i],
                key="ubah_peminjam_pilih",
            )
            peminjam = next(p for p in rows if p["id"] == pilihan)

            with st.form("form_ubah_peminjam"):
                nama = st.text_input("Nama Lengkap *", value=peminjam["nama"])
                c1, c2 = st.columns(2)
                nim = c1.text_input("NIM *", value=peminjam["nim"])
                kelas = c2.text_input("Kelas / Program Studi *", value=peminjam["kelas"])
                kontak = st.text_input("Kontak *", value=peminjam["kontak"])

                if st.form_submit_button("Simpan Perubahan", type="primary"):
                    if not all(x.strip() for x in [nama, nim, kelas, kontak]):
                        st.error("Semua kolom bertanda * wajib diisi.")
                    else:
                        try:
                            db.ubah_peminjam(pilihan, nama, nim, kelas, kontak)
                            flash(f"Data peminjam '{nama.strip()}' berhasil diperbarui.")
                            st.rerun()
                        except ValueError as e:
                            st.error(str(e))

            st.divider()
            st.markdown("**Hapus peminjam**")
            st.caption(
                "Peminjam yang memiliki riwayat transaksi tidak dapat dihapus."
            )
            konfirmasi = st.checkbox(
                f"Ya, hapus {peminjam['nama']}", key="konfirmasi_hapus_peminjam"
            )
            if st.button("Hapus Peminjam", disabled=not konfirmasi,
                         key="tombol_hapus_peminjam"):
                try:
                    db.hapus_peminjam(pilihan)
                    flash(f"Peminjam '{peminjam['nama']}' berhasil dihapus.")
                    st.rerun()
                except ValueError as e:
                    st.error(str(e))


# ---------------------------------------------------------------------------
# Peminjaman baru
# ---------------------------------------------------------------------------

def halaman_peminjaman():
    st.header("📝 Peminjaman Baru")
    st.caption("Satu transaksi dapat memuat beberapa jenis barang sekaligus.")

    daftar_peminjam = db.list_peminjam()
    daftar_barang = [b for b in db.list_barang() if b["jumlah_tersedia"] > 0]

    if not daftar_peminjam:
        st.warning("Belum ada data peminjam. Tambahkan dahulu di menu **Data Peminjam**.")
        return
    if not daftar_barang:
        st.warning("Tidak ada barang dengan stok tersedia.")
        return

    opsi_peminjam = {
        p["id"]: f'{p["nama"]} — {p["nim"]} ({p["kelas"]})' for p in daftar_peminjam
    }
    pilihan_peminjam = st.selectbox(
        "Peminjam *", list(opsi_peminjam), format_func=lambda i: opsi_peminjam[i],
        key="pinjam_peminjam",
    )

    c1, c2 = st.columns(2)
    tgl_pinjam = c1.date_input("Tanggal Pinjam *", value=date.today(), key="pinjam_tgl")
    batas_kembali = c2.date_input(
        "Batas Waktu Pengembalian *",
        value=date.today() + timedelta(days=3),
        key="pinjam_batas",
    )

    tujuan = st.text_area(
        "Tujuan Penggunaan / Kegiatan *",
        placeholder="Contoh: Rapat pengurus HMJ di Gedung A",
        key="pinjam_tujuan",
    )
    c3, c4 = st.columns(2)
    petugas = c3.text_input(
        "Petugas yang Menyetujui *", value="Pengurus HMJ", key="pinjam_petugas"
    )
    catatan = c4.text_input("Catatan (opsional)", key="pinjam_catatan")

    st.markdown("**Barang yang Dipinjam**")
    opsi_barang = {
        b["id"]: f'{b["kode"]} — {b["nama"]} (tersedia {b["jumlah_tersedia"]})'
        for b in daftar_barang
    }
    dipilih = st.multiselect(
        "Pilih barang *", list(opsi_barang),
        format_func=lambda i: opsi_barang[i], key="pinjam_barang",
    )

    jumlah = {}
    if dipilih:
        kolom = st.columns(3)
        for posisi, barang_id in enumerate(dipilih):
            barang = next(b for b in daftar_barang if b["id"] == barang_id)
            with kolom[posisi % 3]:
                jumlah[barang_id] = st.number_input(
                    f'{barang["nama"]} (maks. {barang["jumlah_tersedia"]})',
                    min_value=1,
                    max_value=int(barang["jumlah_tersedia"]),
                    value=1,
                    step=1,
                    key=f"pinjam_qty_{barang_id}",
                )

    st.divider()
    if st.button("Simpan Peminjaman", type="primary", key="simpan_peminjaman"):
        if not tujuan.strip():
            st.error("Tujuan penggunaan wajib diisi.")
        elif not petugas.strip():
            st.error("Nama petugas yang menyetujui wajib diisi.")
        elif batas_kembali < tgl_pinjam:
            st.error("Batas waktu pengembalian tidak boleh sebelum tanggal pinjam.")
        elif not dipilih:
            st.error("Pilih minimal satu barang.")
        else:
            try:
                items = [(bid, jumlah[bid]) for bid in dipilih]
                baru = db.buat_peminjaman(
                    pilihan_peminjam, tujuan, tgl_pinjam.isoformat(),
                    batas_kembali.isoformat(), petugas, catatan, items,
                )
                for key in list(st.session_state.keys()):
                    if key == "pinjam_barang" or key.startswith("pinjam_qty_"):
                        del st.session_state[key]
                flash(f"Transaksi peminjaman #{baru} berhasil dicatat.")
                st.rerun()
            except ValueError as e:
                st.error(str(e))


# ---------------------------------------------------------------------------
# Pengembalian
# ---------------------------------------------------------------------------

def halaman_pengembalian():
    st.header("📤 Pengembalian Barang")
    st.caption("Catat jumlah dan kondisi barang setelah digunakan.")

    loans = db.list_peminjaman_aktif()
    if not loans:
        st.info("Tidak ada transaksi yang menunggu pengembalian.")
        return

    opsi = {
        l["id"]: f'#{l["id"]} — {l["nama"]} ({l["nim"]}) · batas '
                 f'{tanggal_indo(l["batas_kembali"])}'
        for l in loans
    }
    pilihan = st.selectbox(
        "Pilih transaksi", list(opsi), format_func=lambda i: opsi[i],
        key="kembali_pilih",
    )
    loan = db.get_peminjaman(pilihan)
    detail = db.detail_peminjaman(pilihan)
    hari_ini = date.today().isoformat()

    c1, c2, c3 = st.columns(3)
    c1.metric("Peminjam", loan["nama"])
    c2.metric("Batas Kembali", tanggal_indo(loan["batas_kembali"]))
    c3.metric("Sisa Barang", loan["sisa_barang"])

    st.caption(
        f'Tujuan: {loan["tujuan"]} · Petugas: {loan["petugas"]}'
        + (f' · Catatan: {loan["catatan"]}' if loan["catatan"] else "")
    )

    if loan["status"] != "Selesai" and loan["batas_kembali"] < hari_ini:
        selisih = (date.today() - date.fromisoformat(loan["batas_kembali"])).days
        st.warning(f"⚠️ Transaksi ini terlambat {selisih} hari.")

    df = pd.DataFrame(
        [
            {
                "Kode": d["kode"],
                "Barang": d["nama"],
                "Jumlah": d["jumlah"],
                "Sudah Kembali": d["jumlah_kembali"],
                "Sisa": d["sisa"],
                "Kondisi Awal": d["kondisi_awal"] or "-",
                "Kondisi Akhir": d["kondisi_kembali"] or "-",
                "Tindak Lanjut": d["tindak_lanjut"] or "-",
            }
            for d in detail
        ]
    )
    st.dataframe(df, hide_index=True)

    sisa_items = [d for d in detail if d["sisa"] > 0]
    if not sisa_items:
        st.info("Semua barang pada transaksi ini sudah dikembalikan.")
        return

    st.subheader("Form Pengembalian")
    tanggal_kembali = st.date_input(
        "Tanggal Pengembalian", value=date.today(), key="kembali_tanggal"
    )

    hasil = {}
    for d in sisa_items:
        st.markdown(
            f'**{d["kode"]} — {d["nama"]}** · sisa **{d["sisa"]} unit** · '
            f'kondisi saat dipinjam: {d["kondisi_awal"] or "-"}'
        )
        c1, c2, c3 = st.columns([1, 1.2, 2])
        qty = c1.number_input(
            "Jumlah dikembalikan",
            min_value=0,
            max_value=int(d["sisa"]),
            value=int(d["sisa"]),
            step=1,
            key=f'kembali_qty_{d["id"]}',
        )
        kondisi = c2.selectbox(
            "Kondisi setelah digunakan", db.KONDISI_KEMBALI,
            key=f'kembali_kondisi_{d["id"]}',
        )
        tindak = c3.text_input(
            "Tindak lanjut / catatan",
            placeholder="Wajib diisi jika rusak atau hilang",
            key=f'kembali_tindak_{d["id"]}',
        )
        hasil[d["id"]] = {
            "jumlah": qty,
            "kondisi": kondisi,
            "tindak_lanjut": tindak,
        }

    st.caption(
        "Barang dengan kondisi **Hilang** akan mengurangi jumlah total inventaris. "
        "Barang rusak akan memperbarui kondisi inventaris."
    )

    if st.button("Proses Pengembalian", type="primary", key="proses_kembali"):
        errors = []
        for d in sisa_items:
            data = hasil[d["id"]]
            if data["jumlah"] > 0 and data["kondisi"] != "Baik" and not data["tindak_lanjut"].strip():
                errors.append(
                    f'Tindak lanjut untuk "{d["nama"]}" wajib diisi karena '
                    f'kondisinya {data["kondisi"]}.'
                )
        if errors:
            for pesan_error in errors:
                st.error(pesan_error)
        else:
            try:
                items = [
                    {
                        "detail_id": detail_id,
                        "jumlah": data["jumlah"],
                        "kondisi": data["kondisi"],
                        "tindak_lanjut": data["tindak_lanjut"],
                    }
                    for detail_id, data in hasil.items()
                ]
                status = db.proses_pengembalian(
                    pilihan, tanggal_kembali.isoformat(), items
                )
                for key in list(st.session_state.keys()):
                    if key.startswith("kembali_qty_") or key.startswith("kembali_kondisi_") or key.startswith("kembali_tindak_"):
                        del st.session_state[key]
                flash(f"Pengembalian berhasil dicatat. Status transaksi: {status}.")
                st.rerun()
            except ValueError as e:
                st.error(str(e))


# ---------------------------------------------------------------------------
# Riwayat transaksi
# ---------------------------------------------------------------------------

def halaman_riwayat():
    st.header("🗂️ Riwayat Transaksi")
    st.caption("Telusuri peminjaman berdasarkan peminjam, status, atau periode.")

    c1, c2 = st.columns([2, 1])
    cari = c1.text_input(
        "Cari", placeholder="Nama, NIM, barang, tujuan, atau petugas...",
        key="riwayat_cari",
    )
    status = c2.multiselect(
        "Status", ["Berjalan", "Sebagian", "Selesai", "Terlambat"],
        key="riwayat_status",
    )

    pakai_periode = st.checkbox("Batasi periode tanggal pinjam", key="riwayat_periode")
    mulai = selesai = None
    if pakai_periode:
        c3, c4 = st.columns(2)
        mulai = c3.date_input(
            "Dari tanggal", value=date.today() - timedelta(days=30),
            key="riwayat_mulai",
        )
        selesai = c4.date_input("Sampai tanggal", value=date.today(), key="riwayat_selesai")

    loans = db.list_peminjaman(status, cari)
    if pakai_periode and mulai and selesai:
        if mulai > selesai:
            st.error("Tanggal awal tidak boleh setelah tanggal akhir.")
            return
        loans = [
            l for l in loans
            if mulai.isoformat() <= l["tanggal_pinjam"] <= selesai.isoformat()
        ]

    if not loans:
        st.info("Tidak ada transaksi yang sesuai filter.")
        return

    df = ke_dataframe(loans)
    df["Keterangan"] = df["hari_terlambat"].map(
        lambda h: f"Terlambat {h} hari" if h > 0 else "-"
    )
    df = df.rename(
        columns={
            "id": "ID",
            "nama": "Peminjam",
            "nim": "NIM",
            "tujuan": "Tujuan",
            "tanggal_pinjam": "Tgl Pinjam",
            "batas_kembali": "Batas Kembali",
            "total_barang": "Total Barang",
            "sisa_barang": "Sisa",
            "status_tampil": "Status",
            "petugas": "Petugas",
        }
    )
    df = format_tanggal(df, ["Tgl Pinjam", "Batas Kembali"])
    kolom_tampil = ["ID", "Peminjam", "NIM", "Tujuan", "Tgl Pinjam",
                    "Batas Kembali", "Total Barang", "Sisa", "Status",
                    "Keterangan", "Petugas"]
    st.dataframe(df[kolom_tampil], hide_index=True)
    unduh_csv(df[kolom_tampil], "riwayat_transaksi.csv", "unduh_riwayat")

    st.divider()
    opsi = {
        l["id"]: f'#{l["id"]} — {l["nama"]} · {tanggal_indo(l["tanggal_pinjam"])} '
                 f'· {l["status_tampil"]}'
        for l in loans
    }
    pilihan = st.selectbox(
        "Lihat detail transaksi", list(opsi), format_func=lambda i: opsi[i],
        key="riwayat_pilih",
    )
    loan = db.get_peminjaman(pilihan)
    detail = db.detail_peminjaman(pilihan)

    st.subheader(f'Detail Transaksi #{loan["id"]}')
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Peminjam", loan["nama"])
    c2.metric("Tanggal Pinjam", tanggal_indo(loan["tanggal_pinjam"]))
    c3.metric("Batas Kembali", tanggal_indo(loan["batas_kembali"]))
    c4.metric("Sisa Barang", loan["sisa_barang"])

    st.caption(
        f'NIM: {loan["nim"]} · Kelas: {loan["kelas"]} · Kontak: {loan["kontak"]}'
    )
    st.caption(f'Tujuan: {loan["tujuan"]} · Petugas: {loan["petugas"]}')
    if loan["catatan"]:
        st.caption(f'Catatan: {loan["catatan"]}')

    if loan["status"] != "Selesai" and loan["batas_kembali"] < date.today().isoformat():
        selisih = (date.today() - date.fromisoformat(loan["batas_kembali"])).days
        st.warning(f"⚠️ Terlambat {selisih} hari.")

    df_detail = pd.DataFrame(
        [
            {
                "Kode": d["kode"],
                "Barang": d["nama"],
                "Jumlah": d["jumlah"],
                "Kembali": d["jumlah_kembali"],
                "Sisa": d["sisa"],
                "Kondisi Awal": d["kondisi_awal"] or "-",
                "Kondisi Akhir": d["kondisi_kembali"] or "-",
                "Tgl Kembali": tanggal_indo(d["tanggal_kembali"]),
                "Tindak Lanjut": d["tindak_lanjut"] or "-",
            }
            for d in detail
        ]
    )
    st.dataframe(df_detail, hide_index=True)


# ---------------------------------------------------------------------------
# Laporan
# ---------------------------------------------------------------------------

def halaman_laporan():
    st.header("📊 Laporan")
    st.caption("Rekap inventaris, keterlambatan, dan riwayat peminjaman.")

    tab_inventaris, tab_terlambat, tab_riwayat = st.tabs(
        ["📦 Rekap Inventaris", "⏰ Transaksi Terlambat", "📄 Riwayat Peminjaman"]
    )

    with tab_inventaris:
        inv = ke_dataframe(db.laporan_inventaris())
        inv = inv.rename(
            columns={
                "kode": "Kode",
                "nama": "Nama Barang",
                "kategori": "Kategori",
                "total": "Total",
                "tersedia": "Tersedia",
                "dipinjam": "Dipinjam",
                "kondisi": "Kondisi",
                "lokasi": "Lokasi",
            }
        )

        c1, c2, c3 = st.columns(3)
        c1.metric("Total Unit", int(inv["Total"].sum()))
        c2.metric("Tersedia", int(inv["Tersedia"].sum()))
        c3.metric("Sedang Dipinjam", int(inv["Dipinjam"].sum()))

        st.dataframe(inv, hide_index=True)
        unduh_csv(inv, "rekap_inventaris.csv", "unduh_inventaris")

        st.divider()
        c4, c5 = st.columns(2)
        with c4:
            st.markdown("**Unit per Kategori**")
            per_kategori = inv.groupby("Kategori")["Total"].sum().to_frame("Unit")
            st.bar_chart(per_kategori)
        with c5:
            st.markdown("**Jumlah Barang per Kondisi**")
            per_kondisi = (
                inv["Kondisi"].value_counts().rename_axis("Kondisi")
                .to_frame("Jumlah")
            )
            st.bar_chart(per_kondisi)

    with tab_terlambat:
        loans = db.list_peminjaman(["Terlambat"])
        if not loans:
            st.info("Tidak ada transaksi yang terlambat.")
        else:
            df = ke_dataframe(loans)
            df["Keterangan"] = df["hari_terlambat"].map(
                lambda h: f"Terlambat {h} hari"
            )
            df = df.rename(
                columns={
                    "id": "ID",
                    "nama": "Peminjam",
                    "nim": "NIM",
                    "kelas": "Kelas",
                    "kontak": "Kontak",
                    "tujuan": "Tujuan",
                    "tanggal_pinjam": "Tgl Pinjam",
                    "batas_kembali": "Batas Kembali",
                    "sisa_barang": "Sisa Barang",
                    "petugas": "Petugas",
                }
            )
            df = format_tanggal(df, ["Tgl Pinjam", "Batas Kembali"])
            kolom = ["ID", "Peminjam", "NIM", "Kelas", "Kontak", "Tujuan",
                     "Tgl Pinjam", "Batas Kembali", "Sisa Barang", "Keterangan",
                     "Petugas"]
            st.dataframe(df[kolom], hide_index=True)
            unduh_csv(df[kolom], "transaksi_terlambat.csv", "unduh_terlambat")

    with tab_riwayat:
        rows = db.laporan_transaksi()
        if not rows:
            st.info("Belum ada riwayat transaksi.")
        else:
            df = ke_dataframe(rows).rename(
                columns={
                    "transaksi": "ID Transaksi",
                    "peminjam": "Peminjam",
                    "nim": "NIM",
                    "kelas": "Kelas",
                    "kode": "Kode Barang",
                    "barang": "Barang",
                    "jumlah": "Jumlah",
                    "kembali": "Kembali",
                    "sisa": "Sisa",
                    "kondisi_awal": "Kondisi Awal",
                    "kondisi_kembali": "Kondisi Akhir",
                    "tindak_lanjut": "Tindak Lanjut",
                    "tanggal_kembali": "Tgl Kembali",
                    "tanggal_pinjam": "Tgl Pinjam",
                    "batas_kembali": "Batas Kembali",
                    "tujuan": "Tujuan",
                    "petugas": "Petugas",
                    "status": "Status",
                }
            )
            df = format_tanggal(df, ["Tgl Pinjam", "Batas Kembali", "Tgl Kembali"])
            st.dataframe(df, hide_index=True)
            unduh_csv(df, "riwayat_peminjaman.csv", "unduh_laporan_riwayat")


# ---------------------------------------------------------------------------
# Navigasi
# ---------------------------------------------------------------------------

MENU = {
    "🏠 Dashboard": halaman_dashboard,
    "📦 Data Barang": halaman_barang,
    "👥 Data Peminjam": halaman_peminjam,
    "📝 Peminjaman Baru": halaman_peminjaman,
    "📤 Pengembalian": halaman_pengembalian,
    "🗂️ Riwayat Transaksi": halaman_riwayat,
    "📊 Laporan": halaman_laporan,
}

with st.sidebar:
    st.markdown("## 📦 Peminjaman Barang")
    st.caption("HMJ Administrasi Bisnis · Politeknik Negeri Semarang")
    pilihan_menu = st.radio("Menu", list(MENU), label_visibility="collapsed")
    st.divider()
    stat = db.statistik()
    st.caption(
        f"📌 {stat['transaksi_berjalan']} transaksi berjalan · "
        f"{stat['terlambat']} terlambat"
    )
    st.caption("🗄️ Database: `data_hmj.db`")
    st.divider()
    st.caption(f"👤 Masuk sebagai **{st.session_state['petugas']['nama']}**")
    if st.button("Keluar", use_container_width=True):
        st.session_state.pop("petugas", None)
        st.rerun()

MENU[pilihan_menu]()
