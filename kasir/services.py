"""services.py - logika bisnis kasir (tanpa UI).

Berisi class TokoService (kelola produk, checkout, laporan) dan fungsi bantu.
"""
from datetime import datetime

from .algoritma import binary_search, cari_linear, kunci_urut, merge_sort
from .models import BATAS_STOK_MENIPIS, Produk, Transaksi
from .validasi import METODE, ValidasiError, validasi_produk


def rupiah(angka):
    """Format angka menjadi 'Rp 15.000'."""
    return "Rp " + f"{int(angka):,}".replace(",", ".")


def hitung_total(*angka):
    """Jumlahkan sejumlah angka (memakai *args), misal total pendapatan."""
    total = 0
    for a in angka:
        total += a
    return total


# Aturan filter produk: nama kriteria -> fungsi lambda (produk, nilai) -> bool
ATURAN_FILTER = {
    "kategori": lambda p, v: p.kategori == v,
    "harga_min": lambda p, v: p.harga >= v,
    "harga_maks": lambda p, v: p.harga <= v,
    "stok_maks": lambda p, v: p.stok <= v,
}


# Kolom yang boleh dipakai untuk pengurutan (mencegah akses atribut sembarangan)
KOLOM_URUT_PRODUK = ("sku", "nama", "kategori", "harga", "hpp", "stok")
KOLOM_URUT_TRX = ("id", "waktu", "items", "total", "metode")


def urutkan_objek(data, kolom, terbalik, kolom_boleh):
    """Urutkan list objek menurut atribut `kolom` memakai merge_sort buatan sendiri.

    Raise ValidasiError bila `kolom` tidak termasuk `kolom_boleh`.
    """
    if kolom not in kolom_boleh:
        raise ValidasiError(f"Kolom urut tidak dikenal: {kolom}")
    return merge_sort(data, key=lambda o: kunci_urut(getattr(o, kolom)), reverse=terbalik)


class TokoService:
    """Mengelola produk, transaksi, dan laporan; menyimpan lewat `storage`."""

    def __init__(self, storage):
        self.storage = storage
        self.produk = storage.muat_produk()
        self.transaksi = storage.muat_transaksi()
        self._indeks_sku = None  # cache list produk terurut SKU untuk binary search

    @property
    def peringatan(self):
        """Pesan masalah file yang terjadi saat data dimuat."""
        return self.storage.peringatan

    # ---------------- produk ----------------
    def _simpan_produk(self):
        """Simpan produk ke file dan buang cache indeks SKU."""
        self._indeks_sku = None
        self.storage.simpan_produk(self.produk)

    def cari_sku(self, sku):
        """Cari satu produk berdasarkan SKU persis (binary search). None bila tidak ada."""
        if self._indeks_sku is None:
            self._indeks_sku = merge_sort(self.produk, key=lambda p: p.sku)
        sku = str(sku).strip().upper()
        pos = binary_search(self._indeks_sku, sku, key=lambda p: p.sku)
        return self._indeks_sku[pos] if pos >= 0 else None

    def tambah_produk(self, **data):
        """Tambah produk baru. `data` = sku, nama, kategori, harga, hpp, stok."""
        bersih = validasi_produk(**data)
        if self.cari_sku(bersih["sku"]):
            raise ValidasiError(f"SKU {bersih['sku']} sudah dipakai")
        self.produk.append(Produk(**bersih))
        self._simpan_produk()

    def ubah_produk(self, sku_lama, **data):
        """Ubah produk dengan SKU `sku_lama`."""
        produk = self.cari_sku(sku_lama)
        if produk is None:
            raise ValidasiError("Produk tidak ditemukan")
        bersih = validasi_produk(**data)
        if bersih["sku"] != produk.sku and self.cari_sku(bersih["sku"]):
            raise ValidasiError(f"SKU {bersih['sku']} sudah dipakai")
        for nama_field, nilai in bersih.items():
            setattr(produk, nama_field, nilai)
        self._simpan_produk()

    def hapus_produk(self, sku):
        """Hapus produk berdasarkan SKU."""
        produk = self.cari_sku(sku)
        if produk is None:
            raise ValidasiError("Produk tidak ditemukan")
        self.produk.remove(produk)
        self._simpan_produk()

    def filter_produk(self, **kriteria):
        """Cari & saring produk memakai **kwargs.

        Kriteria: kata (pencarian kata kunci), kategori, harga_min,
        harga_maks, stok_maks. Nilai None/"" diabaikan.
        """
        hasil = list(self.produk)
        kata = kriteria.pop("kata", "")
        hasil = cari_linear(hasil, kata or "", lambda p: p.teks_cari())
        for nama, nilai in kriteria.items():
            if nilai is None or nilai == "":
                continue
            if nama not in ATURAN_FILTER:
                raise ValidasiError(f"Filter tidak dikenal: {nama}")
            aturan = ATURAN_FILTER[nama]
            hasil = [p for p in hasil if aturan(p, nilai)]
        return hasil

    def daftar_produk(self, urut=None, terbalik=False, **kriteria):
        """Produk hasil filter (`**kriteria`), lalu diurutkan menurut kolom `urut`."""
        hasil = self.filter_produk(**kriteria)
        if urut:
            hasil = urutkan_objek(hasil, urut, terbalik, KOLOM_URUT_PRODUK)
        return hasil

    def stok_menipis(self, batas=BATAS_STOK_MENIPIS):
        """Daftar produk yang stoknya menipis."""
        return self.filter_produk(stok_maks=batas)

    # ---------------- transaksi ----------------
    def _id_baru(self):
        """Buat ID transaksi berikutnya, misal TRX-0007."""
        nomor = 0
        for t in self.transaksi:
            try:
                nomor = max(nomor, int(t.id.split("-")[1]))
            except (IndexError, ValueError):
                continue  # ID tidak sesuai format: abaikan
        return f"TRX-{nomor + 1:04d}"

    def checkout(self, keranjang, metode, diskon_persen=0, uang=0):
        """Proses pembayaran: validasi, kurangi stok, simpan transaksi.

        Returns:
            (Transaksi, kembalian)
        Raises:
            ValidasiError bila keranjang kosong, metode salah, stok kurang,
            atau uang tunai kurang dari total.
        """
        if keranjang.kosong():
            raise ValidasiError("Keranjang masih kosong")
        if metode not in METODE:
            raise ValidasiError("Metode pembayaran tidak valid")
        sub, diskon, total = keranjang.hitung(diskon_persen)
        if metode == "Tunai" and uang < total:
            raise ValidasiError("Uang diterima kurang dari total")
        for produk, qty in keranjang.daftar():
            if self.cari_sku(produk.sku) is not produk:
                raise ValidasiError(f"Produk {produk.nama} sudah tidak tersedia")
            if qty > produk.stok:
                raise ValidasiError(f"Stok {produk.nama} tidak cukup")

        for produk, qty in keranjang.daftar():
            produk.stok -= qty
        trx = Transaksi(id=self._id_baru(),
                        waktu=datetime.now().strftime("%Y-%m-%d %H:%M"),
                        items=keranjang.ringkas_item(), subtotal=sub, diskon=diskon,
                        total=total, hpp=keranjang.hpp_total(), metode=metode)
        self.transaksi.append(trx)
        self._simpan_produk()
        self.storage.simpan_transaksi(trx)
        return trx, (uang - total if metode == "Tunai" else 0)

    def cari_transaksi(self, kata):
        """Cari transaksi berdasarkan kata kunci (ID, waktu, item, metode)."""
        return cari_linear(self.transaksi, kata,
                           lambda t: f"{t.id} {t.waktu} {t.items} {t.metode}")

    def daftar_transaksi(self, kata="", urut="waktu", terbalik=True):
        """Transaksi hasil pencarian kata kunci, diurutkan (default: terbaru dulu)."""
        return urutkan_objek(self.cari_transaksi(kata), urut, terbalik, KOLOM_URUT_TRX)

    def ambil_transaksi(self, id_trx):
        """Satu transaksi berdasarkan ID, atau None."""
        return next((t for t in self.transaksi if t.id == id_trx), None)

    # ---------------- laporan ----------------
    def ringkasan_harian(self):
        """Rekap per tanggal: (tanggal, jumlah_trx, pendapatan, hpp, laba), terbaru dulu."""
        per_hari = {}
        for t in self.transaksi:
            r = per_hari.setdefault(t.waktu[:10], [0, 0, 0])
            r[0] += 1
            r[1] += t.total
            r[2] += t.hpp
        baris = [(tgl, n, pend, hpp, pend - hpp) for tgl, (n, pend, hpp) in per_hari.items()]
        return merge_sort(baris, key=lambda r: r[0], reverse=True)

    def ringkasan_total(self):
        """Total keseluruhan: dict jumlah, pendapatan, hpp, laba."""
        pendapatan = hitung_total(*(t.total for t in self.transaksi))
        hpp = hitung_total(*(t.hpp for t in self.transaksi))
        return {"jumlah": len(self.transaksi), "pendapatan": pendapatan,
                "hpp": hpp, "laba": pendapatan - hpp}


def struk_teks(trx, uang=0, kembalian=0):
    """Susun teks struk untuk ditampilkan/dicetak."""
    garis = "-" * 34
    baris = ["   UNICASHIER DIMSUM MENTAI", garis, f"{trx.id}  {trx.waktu}", garis]
    baris += [f"- {item}" for item in trx.items.split("; ")]
    baris += [garis, f"Subtotal : {rupiah(trx.subtotal)}"]
    if trx.diskon:
        baris.append(f"Diskon   : -{rupiah(trx.diskon)}")
    baris.append(f"TOTAL    : {rupiah(trx.total)}")
    baris.append(f"Metode   : {trx.metode}")
    if trx.metode == "Tunai" and uang:
        baris += [f"Tunai    : {rupiah(uang)}", f"Kembali  : {rupiah(kembalian)}"]
    baris += [garis, "   Terima kasih! Selamat menikmati"]
    return "\n".join(baris)
