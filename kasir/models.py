from dataclasses import dataclass

from .validasi import ValidasiError

BATAS_STOK_MENIPIS = 10 


@dataclass
class Produk:
    sku: str
    nama: str
    kategori: str
    harga: int   
    hpp: int     
    stok: int

    def stok_menipis(self, batas=BATAS_STOK_MENIPIS):
        return self.stok <= batas

    def teks_cari(self):
        return f"{self.sku} {self.nama} {self.kategori}"


@dataclass
class Transaksi:
    id: str
    waktu: str       
    items: str       
    subtotal: int
    diskon: int      
    total: int
    hpp: int         
    metode: str

    @property
    def laba(self):
        return self.total - self.hpp


class Keranjang:

    def __init__(self):
        self._item = {}

    def jumlah(self, sku):
        return self._item[sku][1] if sku in self._item else 0

    def tambah(self, produk, qty=1):
        if qty <= 0:
            raise ValidasiError("Jumlah harus lebih dari 0")
        baru = self.jumlah(produk.sku) + qty
        if baru > produk.stok:
            raise ValidasiError(f"Stok {produk.nama} hanya {produk.stok}")
        self._item[produk.sku] = [produk, baru]

    def kurangi(self, sku):
        if sku in self._item:
            self._item[sku][1] -= 1
            if self._item[sku][1] <= 0:
                del self._item[sku]

    def hapus(self, sku):
        self._item.pop(sku, None)

    def kosongkan(self):
        self._item.clear()

    def kosong(self):
        return not self._item

    def daftar(self):
        return [(p, q) for p, q in self._item.values()]

    def baris(self):
        return [(p.sku, p.nama, q, p.harga * q) for p, q in self._item.values()]

    def subtotal(self):
        return sum(p.harga * q for p, q in self._item.values())

    def hpp_total(self):
        return sum(p.hpp * q for p, q in self._item.values())

    def hitung(self, diskon_persen=0):
        if not 0 <= diskon_persen <= 100:
            raise ValidasiError("Diskon harus antara 0 sampai 100 persen")
        sub = self.subtotal()
        diskon = sub * diskon_persen // 100
        return sub, diskon, sub - diskon

    def ringkas_item(self):
        return "; ".join(f"{p.nama} x{q}" for p, q in self._item.values())
