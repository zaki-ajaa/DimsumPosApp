def kunci_urut(nilai):
    return nilai.lower() if isinstance(nilai, str) else nilai


def merge_sort(data, key=lambda x: x, reverse=False):
    assert callable(key), "key harus berupa fungsi"
    if len(data) <= 1:
        return list(data)
    tengah = len(data) // 2
    kiri = merge_sort(data[:tengah], key, reverse)
    kanan = merge_sort(data[tengah:], key, reverse)
    return _gabung(kiri, kanan, key, reverse)


def _gabung(kiri, kanan, key, reverse):
    hasil, i, j = [], 0, 0
    while i < len(kiri) and j < len(kanan):
        a, b = key(kiri[i]), key(kanan[j])
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
    kata = kata.strip().lower()
    if not kata:
        return list(data)
    return [d for d in data if kata in ambil_teks(d).lower()]
