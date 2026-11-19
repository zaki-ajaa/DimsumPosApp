"""algoritma.py - algoritma pengurutan & pencarian buatan sendiri.

Semua fungsi di sini murni (tidak menyentuh UI/file) sehingga mudah diuji.
"""


def kunci_urut(nilai):
    """Samakan perbandingan teks (abaikan huruf besar/kecil); angka apa adanya."""
    return nilai.lower() if isinstance(nilai, str) else nilai


def merge_sort(data, key=lambda x: x, reverse=False):
    """Merge sort (stabil), kompleksitas O(n log n).

    Args:
        data: list yang akan diurutkan (tidak diubah, hasil berupa list baru).
        key: fungsi pengambil nilai pembanding (default: elemen itu sendiri).
        reverse: True untuk urut menurun.
    """
    assert callable(key), "key harus berupa fungsi"
    if len(data) <= 1:
        return list(data)
    tengah = len(data) // 2
    kiri = merge_sort(data[:tengah], key, reverse)
    kanan = merge_sort(data[tengah:], key, reverse)
    return _gabung(kiri, kanan, key, reverse)


def _gabung(kiri, kanan, key, reverse):
    """Gabungkan dua list yang sudah terurut menjadi satu list terurut."""
    hasil, i, j = [], 0, 0
    while i < len(kiri) and j < len(kanan):
        a, b = key(kiri[i]), key(kanan[j])
        # '<=' / '>=' (bukan '<' / '>') menjaga urutan elemen sama tetap stabil
        ambil_kiri = a >= b if reverse else a <= b
        if ambil_kiri:
            hasil.append(kiri[i])
            i += 1
        else:
            hasil.append(kanan[j])
            j += 1
    hasil.extend(kiri[i:])
    hasil.extend(kanan[j:])
    return hasil


def binary_search(data, target, key=lambda x: x):
    """Binary search O(log n) pada `data` yang SUDAH terurut naik menurut `key`.

    Returns:
        indeks elemen yang cocok, atau -1 bila tidak ditemukan.
    """
    kiri, kanan = 0, len(data) - 1
    while kiri <= kanan:
        tengah = (kiri + kanan) // 2
        nilai = key(data[tengah])
        if nilai == target:
            return tengah
        if nilai < target:
            kiri = tengah + 1
        else:
            kanan = tengah - 1
    return -1


def cari_linear(data, kata, ambil_teks):
    """Pencarian kata kunci (substring, tidak peka huruf besar/kecil).

    Args:
        data: list objek.
        kata: kata kunci; kosong berarti semua data cocok.
        ambil_teks: fungsi yang mengubah satu objek menjadi teks yang dicari.
    """
    kata = kata.strip().lower()
    if not kata:
        return list(data)
    return [d for d in data if kata in ambil_teks(d).lower()]
