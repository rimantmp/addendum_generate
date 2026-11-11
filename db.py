import os
from datetime import date
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import (
    Base, Distributor, Kios, SKRealokasi, JenisPupuk, PerjanjianInduk, Addendum, DetailAlokasi
)

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "addendum.db")
DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    Base.metadata.create_all(bind=engine)

def seed_sample_data():
    init_db()
    session = SessionLocal()

    # 1. Distributor
    dist = session.query(Distributor).first()
    if not dist:
        dist = Distributor(
            nama_perusahaan="CV. SUBUR ANUGERAH SEJAHTERA",
            nama_pimpinan="LIBERTINY YUEALLA Z. P.",
            jabatan="DIREKTUR",
            alamat="Jl. Pembangunan No. 12 Kel. Penanian Kec. Rantepao",
            kecamatan="Rantepao",
            kabupaten="Kabupaten Tana Toraja",
            provinsi="Sulawesi Selatan"
        )
        session.add(dist)
        session.flush()

    # 2. Kios
    kios1 = session.query(Kios).filter(Kios.nama_kios == "UD UNGGUL TANI").first()
    if not kios1:
        kios1 = Kios(
            nama_kios="UD UNGGUL TANI",
            nama_pemilik="JON TANDI TABANG",
            jabatan="PIMPINAN",
            alamat="Bittuang Kecamatan Bittuang",
            kecamatan="BITTUANG",
            kabupaten="Tana Toraja",
            kode_kios="K-001"
        )
        session.add(kios1)
        session.flush()

    # 3. Jenis Pupuk (Urutan: UREA, NPK, SP36, ORGANIK)
    if not session.query(JenisPupuk).first():
        pupuk_urea = JenisPupuk(kode="UREA", nama="UREA", satuan="Ton/Liter", urutan=1)
        pupuk_npk = JenisPupuk(kode="NPK", nama="NPK", satuan="Ton/Liter", urutan=2)
        pupuk_sp36 = JenisPupuk(kode="SP36", nama="SP36", satuan="Ton/Liter", urutan=3)
        pupuk_organik = JenisPupuk(kode="ORGANIK", nama="ORGANIK", satuan="Ton/Liter", urutan=4)
        session.add_all([pupuk_urea, pupuk_npk, pupuk_sp36, pupuk_organik])
        session.flush()
    else:
        urea = session.query(JenisPupuk).filter(JenisPupuk.kode == "UREA").first()
        npk = session.query(JenisPupuk).filter(JenisPupuk.kode == "NPK").first()
        sp36 = session.query(JenisPupuk).filter(JenisPupuk.kode == "SP36").first()
        org = session.query(JenisPupuk).filter(JenisPupuk.kode == "ORGANIK").first()
        if urea: urea.urutan = 1
        if npk: npk.urutan = 2
        if sp36: sp36.urutan = 3
        if org: org.urutan = 4
        session.flush()

    # 4. SK Realokasi
    sk_prov = session.query(SKRealokasi).filter(SKRealokasi.tingkat == "Provinsi").first()
    if not sk_prov:
        sk_prov = SKRealokasi(
            tingkat="Provinsi",
            nama_pejabat_dinas="Kepala Dinas Tanaman Pangan Hortikultura dan Perkebunan Provinsi Sulawesi Selatan",
            nama_daerah="Provinsi Sulawesi Selatan",
            nomor_sk="521/11502/12/2022/DTPH-BUN",
            tanggal_sk=date(2022, 12, 7),
            realokasi_ke="Realokasi V (Kelima)",
            tahun_anggaran=2022
        )
        session.add(sk_prov)
        session.flush()

    sk_kab = session.query(SKRealokasi).filter(SKRealokasi.tingkat == "Kabupaten").first()
    if not sk_kab:
        sk_kab = SKRealokasi(
            tingkat="Kabupaten",
            nama_pejabat_dinas="Kepala Dinas Pertanian Kabupaten Tana Toraja",
            nama_daerah="Kabupaten Tana Toraja",
            nomor_sk="049/110/DP/XII/2022",
            tanggal_sk=date(2022, 12, 21),
            realokasi_ke="Realokasi V (Kelima)",
            tahun_anggaran=2022
        )
        session.add(sk_kab)
        session.flush()

    # 5. Perjanjian Induk
    pi1 = session.query(PerjanjianInduk).filter(PerjanjianInduk.kios_id == kios1.id).first()
    if not pi1:
        pi1 = PerjanjianInduk(
            nomor_surat="01/SP/CV.ST/I/2022",
            tanggal_surat=date(2022, 1, 3),
            tanggal_berlaku_sampai=date(2022, 12, 31),
            distributor_id=dist.id,
            kios_id=kios1.id
        )
        session.add(pi1)
        session.flush()

    # 6. Addendum 1 untuk UD Unggul Tani
    addendum1 = session.query(Addendum).filter(Addendum.id == 1).first()
    if not addendum1:
        addendum1 = Addendum(
            id=1,
            addendum_ke="I",
            nomor_addendum="01/SP/CV/ST/XII/2022",
            nomor_lampiran_2="01/SP/CV.STXII/2022",
            kota_ttd="Kabupaten Tana Toraja",
            tanggal_ttd=date(2022, 12, 21),
            tanggal_berlaku_efektif=date(2022, 12, 21),
            tahun_anggaran=2022,
            perjanjian_induk_id=pi1.id,
            sk_provinsi_id=sk_prov.id,
            sk_kabupaten_id=sk_kab.id
        )
        session.add(addendum1)
        session.flush()

        # Alokasi 12 Bulan (Persis data dokumen PDF)
        pupuk_npk = session.query(JenisPupuk).filter(JenisPupuk.kode == "NPK").first()
        pupuk_urea = session.query(JenisPupuk).filter(JenisPupuk.kode == "UREA").first()
        pupuk_sp36 = session.query(JenisPupuk).filter(JenisPupuk.kode == "SP36").first()
        pupuk_organik = session.query(JenisPupuk).filter(JenisPupuk.kode == "ORGANIK").first()

        npk_values = [10, 20, 30, 40, 10, 15, 35, 15, 25, 15, 15, 25]
        urea_values = [0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0]
        sp36_values = [0] * 12
        org_values = [0] * 12

        for bulan in range(1, 13):
            idx = bulan - 1
            session.add(DetailAlokasi(addendum_id=addendum1.id, kecamatan="BITTUANG", bulan=bulan, jenis_pupuk_id=pupuk_npk.id, kuota=float(npk_values[idx])))
            session.add(DetailAlokasi(addendum_id=addendum1.id, kecamatan="BITTUANG", bulan=bulan, jenis_pupuk_id=pupuk_urea.id, kuota=float(urea_values[idx])))
            session.add(DetailAlokasi(addendum_id=addendum1.id, kecamatan="BITTUANG", bulan=bulan, jenis_pupuk_id=pupuk_sp36.id, kuota=float(sp36_values[idx])))
            session.add(DetailAlokasi(addendum_id=addendum1.id, kecamatan="BITTUANG", bulan=bulan, jenis_pupuk_id=pupuk_organik.id, kuota=float(org_values[idx])))

    session.commit()
    session.close()

if __name__ == "__main__":
    seed_sample_data()
    print("Database SQLite seed verified!")
