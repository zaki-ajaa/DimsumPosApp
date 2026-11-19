"""storage.py - penyimpanan data permanen ke file CSV.

Semua operasi file memakai context manager `with open(...)`.
Mode yang dipakai:
  'r' = membaca produk/transaksi,   'w' = menulis ulang produk,
  'a' = menambah transaksi baru,    'x' = membuat file baru (gagal bila sudah ada).
"""
import csv
import os

from .models import Produk, Transaksi

KOLOM_PRODUK = ["sku", "nama", "kategori", "harga", "hpp", "stok"]
KOLOM_TRX = ["id", "waktu", "items", "subtotal", "diskon", "total", "hpp", "metode"]

# Data awal (dipakai saat produk.csv belum ada atau rusak total)
PRODUK_AWAL = [
    dict(sku="DM001", nama="Dimsum Mentai Original", kategori="Dimsum", harga=15000, hpp=8000, stok=40),
    dict(sku="DM002", nama="Dimsum Mentai Keju", kategori="Dimsum", harga=18000, hpp=10000, stok=35),
    dict(sku="DM003", nama="Dimsum Mentai Pedas", kategori="Dimsum", harga=17000, hpp=9000, stok=30),
    dict(sku="DM004", nama="Dimsum Mentai Ayam Udang", kategori="Dimsum", harga=20000, hpp=11500, stok=25),
    dict(sku="DM005", nama="Dimsum Kukus Polos", kategori="Dimsum", harga=12000, hpp=6000, stok=8),
    dict(sku="TP001", nama="Extra Saus Mentai", kategori="Topping", harga=4000, hpp=1800, stok=60),
    dict(sku="TP002", nama="Extra Keju Leleh", kategori="Topping", harga=5000, hpp=2500, stok=45),
    dict(sku="TP003", nama="Sambal Bawang", kategori="Topping", harga=3000, hpp=1000, stok=50),
    dict(sku="MN001", nama="Es Teh Manis", kategori="Minuman", harga=6000, hpp=1800, stok=50),
    dict(sku="MN002", nama="Es Lemon Tea", kategori="Minuman", harga=9000, hpp=3000, stok=40),
    dict(sku="MN003", nama="Air Mineral", kategori="Minuman", harga=5000, hpp=2000, stok=9),
    dict(sku="PK001", nama="Paket Hemat (3 Mentai + Es Teh)", kategori="Paket", harga=48000, hpp=27000, stok=20),
]


class Storage:
    """Membaca & menulis data produk dan transaksi ke folder `folder`."""

    def __init__(self, folder="data"):
        os.makedirs(folder, exist_ok=True)
        self.file_produk = os.path.join(folder, "produk.csv")
        self.file_trx = os.path.join(folder, "transaksi.csv")
        # Pesan masalah file (hilang/rusak) yang bisa ditampilkan UI sebagai peringatan
        self.peringatan = []
        # Catatan biasa (bukan masalah), mis. file dibuat otomatis saat pertama dijalankan
        self.info = []

    # ---------------- produk ----------------
    def simpan_produk(self, daftar):
        """Tulis ulang seluruh produk ke produk.csv (mode 'w')."""
        with open(self.file_produk, "w", newline="", encoding="utf-8") as f:
            penulis = csv.DictWriter(f, fieldnames=KOLOM_PRODUK)
            penulis.writeheader()
            for p in daftar:
                penulis.writerow({k: getattr(p, k) for k in KOLOM_PRODUK})

    def muat_produk(self):
        """Baca produk.csv (mode 'r') dan kembalikan list Produk.

        - File hilang  -> dibuat dari PRODUK_AWAL (FileNotFoundError ditangani).
        - Baris rusak  -> dilewati dan dicatat di `peringatan` (ValueError/KeyError).
        - File rusak total -> memakai data awal agar aplikasi tidak crash.
        """
        hasil, rusak = [], 0
        try:
            with open(self.file_produk, "r", newline="", encoding="utf-8") as f:
                for no, baris in enumerate(csv.DictReader(f), start=2):
                    try:
                        hasil.append(Produk(
                            sku=baris["sku"], nama=baris["nama"],
                            kategori=baris["kategori"], harga=int(baris["harga"]),
                            hpp=int(baris["hpp"]), stok=int(baris["stok"])))
                    except (KeyError, ValueError, TypeError):
                        rusak += 1
                        self.peringatan.append(f"produk.csv baris {no} rusak, dilewati")
        except FileNotFoundError:
            self.info.append("produk.csv tidak ditemukan, dibuat dari data awal")
            hasil = [Produk(**p) for p in PRODUK_AWAL]
            self.simpan_produk(hasil)
            return hasil
        except (ValueError, csv.Error):  # termasuk UnicodeDecodeError
            self.peringatan.append("produk.csv tidak bisa dibaca, memakai data awal")
            return [Produk(**p) for p in PRODUK_AWAL]

        if not hasil and rusak:  # semua baris rusak -> jangan biarkan toko kosong
            self.peringatan.append("Tidak ada produk valid, memakai data awal")
            hasil = [Produk(**p) for p in PRODUK_AWAL]
        return hasil

    # ---------------- transaksi ----------------
    def _pastikan_file_trx(self):
        """Buat transaksi.csv + header bila belum ada (mode 'x')."""
        try:
            with open(self.file_trx, "x", newline="", encoding="utf-8") as f:
                csv.writer(f).writerow(KOLOM_TRX)
        except FileExistsError:
            pass  # sudah ada: tidak perlu dibuat lagi

    def simpan_transaksi(self, trx):
        """Tambahkan satu transaksi di akhir file (mode 'a')."""
        self._pastikan_file_trx()
        with open(self.file_trx, "a", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow([trx.id, trx.waktu, trx.items, trx.subtotal,
                                    trx.diskon, trx.total, trx.hpp, trx.metode])

    def muat_transaksi(self):
        """Baca transaksi.csv (mode 'r'); baris rusak dilewati."""
        hasil = []
        try:
            with open(self.file_trx, "r", newline="", encoding="utf-8") as f:
                for no, b in enumerate(csv.DictReader(f), start=2):
                    try:
                        hasil.append(Transaksi(
                            id=b["id"], waktu=b["waktu"], items=b["items"],
                            subtotal=int(b["subtotal"]), diskon=int(b["diskon"]),
                            total=int(b["total"]), hpp=int(b["hpp"]), metode=b["metode"]))
                    except (KeyError, ValueError, TypeError):
                        self.peringatan.append(f"transaksi.csv baris {no} rusak, dilewati")
        except FileNotFoundError:
            self._pastikan_file_trx()
        except (ValueError, csv.Error):
            self.peringatan.append("transaksi.csv tidak bisa dibaca, riwayat dikosongkan")
            return []
        return hasil
