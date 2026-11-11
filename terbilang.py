"""
Modul pembantu untuk konversi angka dan tanggal ke format terbilang Bahasa Indonesia
serta generator penomoran surat otomatis (Addendum & SPJB).
"""

SATUAN = ["", "Satu", "Dua", "Tiga", "Empat", "Lima", "Enam", "Tujuh", "Delapan", "Sembilan", "Sepuluh", "Sebelas"]
HARI_INDONESIA = {
    0: "Senin",
    1: "Selasa",
    2: "Rabu",
    3: "Kamis",
    4: "Jumat",
    5: "Sabtu",
    6: "Minggu"
}
BULAN_INDONESIA = {
    1: "Januari", 2: "Februari", 3: "Maret", 4: "April",
    5: "Mei", 6: "Juni", 7: "Juli", 8: "Agustus",
    9: "September", 10: "Oktober", 11: "November", 12: "Desember"
}
BULAN_ROMALI = {
    1: "I", 2: "II", 3: "III", 4: "IV", 5: "V", 6: "VI",
    7: "VII", 8: "VIII", 9: "IX", 10: "X", 11: "XI", 12: "XII"
}

def terbilang(n: int) -> str:
    """Mengubah bilangan bulat positif menjadi kata terbilang Bahasa Indonesia."""
    if n < 0:
        return "Minus " + terbilang(abs(n))
    if n < 12:
        return SATUAN[n]
    if n < 20:
        return SATUAN[n - 10] + " Belas"
    if n < 100:
        sisa = n % 10
        return SATUAN[n // 10] + " Puluh" + (" " + SATUAN[sisa] if sisa > 0 else "")
    if n < 200:
        sisa = n % 100
        return "Seratus" + (" " + terbilang(sisa) if sisa > 0 else "")
    if n < 1000:
        sisa = n % 100
        return SATUAN[n // 100] + " Ratus" + (" " + terbilang(sisa) if sisa > 0 else "")
    if n < 2000:
        sisa = n % 1000
        return "Seribu" + (" " + terbilang(sisa) if sisa > 0 else "")
    if n < 1000000:
        sisa = n % 1000
        return terbilang(n // 1000) + " Ribu" + (" " + terbilang(sisa) if sisa > 0 else "")
    if n < 1000000000:
        sisa = n % 1000000
        return terbilang(n // 1000000) + " Juta" + (" " + terbilang(sisa) if sisa > 0 else "")
    return str(n)


def format_tanggal_addendum(dt) -> dict:
    hari = HARI_INDONESIA.get(dt.weekday(), "")
    tanggal_terbilang = terbilang(dt.day)
    bulan_terbilang = terbilang(dt.month)
    tahun_terbilang = terbilang(dt.year)
    tanggal_format_angka = dt.strftime("%d-%m-%Y")
    bulan_nama = BULAN_INDONESIA.get(dt.month, "")
    romawi_bulan = BULAN_ROMALI.get(dt.month, "")

    return {
        "hari": hari,
        "tanggal_terbilang": tanggal_terbilang,
        "bulan_terbilang": bulan_terbilang,
        "tahun_terbilang": tahun_terbilang,
        "tanggal_format_angka": tanggal_format_angka,
        "bulan_nama": bulan_nama,
        "romawi_bulan": romawi_bulan,
        "tanggal_lengkap": f"{dt.day} {bulan_nama} {dt.year}"
    }


def generate_nomor_surat_addendum(nomor_urut: int, dt, format_lampiran=False) -> str:
    romawi = BULAN_ROMALI.get(dt.month, "I")
    tahun = dt.year
    urut_str = f"{nomor_urut:02d}"

    if format_lampiran:
        return f"{urut_str}/SP/CV.ST{romawi}/{tahun}"
    return f"{urut_str}/SP/CV/ST/{romawi}/{tahun}"


def generate_nomor_spjb(nomor_urut: int, tahun: int = 2022) -> str:
    """Format Nomor Surat Perjanjian Jual Beli Pokok (SPJB Induk): {nomor_urut:02d}/SP/CV.ST/I/{tahun}"""
    return f"{nomor_urut:02d}/SP/CV.ST/I/{tahun}"
