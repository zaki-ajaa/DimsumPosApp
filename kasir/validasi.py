"""validasi.py - aturan validasi input.

Modul ini murni logika (tanpa UI) sehingga mudah diuji dengan unittest.
"""

# Pilihan tetap yang dipakai di seluruh aplikasi
KATEGORI = ("Dimsum", "Topping", "Minuman", "Paket")
METODE = ("Tunai", "QRIS", "Transfer")


class ValidasiError(ValueError):
    """Error khusus untuk input yang tidak valid.

    Turunan ValueError, jadi `except ValueError` juga menangkapnya.
    """


def ke_int(nilai, nama_field):
    """Ubah `nilai` menjadi int; raise ValidasiError bila bukan angka bulat."""
    try:
        return int(str(nilai).strip())
    except ValueError:
        # `from None` menyembunyikan traceback ValueError bawaan agar pesan bersih
        raise ValidasiError(f"{nama_field} harus berupa angka bulat") from None


def validasi_produk(sku, nama, kategori, harga, hpp, stok):
    """Validasi satu data produk dan kembalikan dict yang sudah dibersihkan.

    Aturan: SKU & nama wajib diisi, kategori harus dikenal,
    harga/HPP/stok tidak boleh negatif, HPP tidak boleh melebihi harga jual.
    """
    sku = str(sku).strip().upper()
    nama = str(nama).strip()
    if not sku:
        raise ValidasiError("SKU wajib diisi")
    if not nama:
        raise ValidasiError("Nama produk wajib diisi")
    if kategori not in KATEGORI:
        raise ValidasiError("Kategori tidak valid")

    harga = ke_int(harga, "Harga")
    hpp = ke_int(hpp, "HPP")
    stok = ke_int(stok, "Stok")
    if harga < 0:
        raise ValidasiError("Harga tidak boleh negatif")
    if hpp < 0:
        raise ValidasiError("HPP tidak boleh negatif")
    if stok < 0:
        raise ValidasiError("Stok tidak boleh negatif")
    if hpp > harga:
        raise ValidasiError("HPP tidak boleh melebihi harga jual")

    return {"sku": sku, "nama": nama, "kategori": kategori,
            "harga": harga, "hpp": hpp, "stok": stok}
