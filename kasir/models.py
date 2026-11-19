"""models.py - kelas data: Produk, Transaksi, dan Keranjang."""
from dataclasses import dataclass

from .validasi import ValidasiError

BATAS_STOK_MENIPIS = 10  # stok <= angka ini dianggap menipis


@dataclass
class Produk:
    """Satu baris data produk (satu baris tabel)."""
    sku: str
    nama: str
    kategori: str
    harga: int   # harga jual (Rp)
    hpp: int     # harga pokok penjualan / modal per unit (Rp)
    stok: int

    def stok_menipis(self, batas=BATAS_STOK_MENIPIS):
        """True jika stok sudah di bawah/sama dengan batas."""
        return self.stok <= batas

    def teks_cari(self):
        """Gabungan SKU, nama, kategori - dipakai fitur pencarian kata kunci."""
        return f"{self.sku} {self.nama} {self.kategori}"


@dataclass
class Transaksi:
    """Satu transaksi penjualan yang sudah dibayar."""
    id: str
    waktu: str       # format "YYYY-MM-DD HH:MM"
    items: str       # contoh: "Mentai Original x2; Es Teh x1"
    subtotal: int
    diskon: int      # nominal diskon (Rp)
    total: int
    hpp: int         # total modal barang yang terjual
    metode: str

    @property
    def laba(self):
        """Laba kotor transaksi = total - HPP."""
        return self.total - self.hpp


class Keranjang:
    """Keranjang belanja kasir. Menyimpan {sku: [Produk, qty]}."""

    def __init__(self):
        self._item = {}

    def jumlah(self, sku):
        """Qty produk `sku` di keranjang (0 jika belum ada)."""
        return self._item[sku][1] if sku in self._item else 0

    def tambah(self, produk, qty=1):
        """Tambah produk; raise ValidasiError bila qty <= 0 atau melebihi stok."""
        if qty <= 0:
            raise ValidasiError("Jumlah harus lebih dari 0")
        baru = self.jumlah(produk.sku) + qty
        if baru > produk.stok:
            raise ValidasiError(f"Stok {produk.nama} hanya {produk.stok}")
        self._item[produk.sku] = [produk, baru]

    def kurangi(self, sku):
        """Kurangi qty satu; hapus baris bila qty menjadi 0."""
        if sku in self._item:
            self._item[sku][1] -= 1
            if self._item[sku][1] <= 0:
                del self._item[sku]

    def hapus(self, sku):
        """Hapus produk dari keranjang."""
        self._item.pop(sku, None)

    def kosongkan(self):
        """Kosongkan keranjang."""
        self._item.clear()

    def kosong(self):
        return not self._item

    def daftar(self):
        """List of (Produk, qty)."""
        return [(p, q) for p, q in self._item.values()]

    def baris(self):
        """Baris tabel keranjang: (sku, nama, qty, subtotal)."""
        return [(p.sku, p.nama, q, p.harga * q) for p, q in self._item.values()]

    def subtotal(self):
        return sum(p.harga * q for p, q in self._item.values())

    def hpp_total(self):
        return sum(p.hpp * q for p, q in self._item.values())

    def hitung(self, diskon_persen=0):
        """Hitung (subtotal, diskon_rupiah, total). Diskon harus 0-100 persen."""
        if not 0 <= diskon_persen <= 100:
            raise ValidasiError("Diskon harus antara 0 sampai 100 persen")
        sub = self.subtotal()
        diskon = sub * diskon_persen // 100
        return sub, diskon, sub - diskon

    def ringkas_item(self):
        """Teks ringkas isi keranjang untuk disimpan di riwayat transaksi."""
        return "; ".join(f"{p.nama} x{q}" for p, q in self._item.values())
