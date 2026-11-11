from datetime import date
from sqlalchemy import (
    Column, Integer, String, Date, Float, ForeignKey, Text, create_engine
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

class Distributor(Base):
    """Pihak Pertama dalam perjanjian"""
    __tablename__ = "distributor"

    id = Column(Integer, primary_key=True, autoincrement=True)
    nama_perusahaan = Column(String(150), nullable=False)
    nama_pimpinan = Column(String(100), nullable=False)
    jabatan = Column(String(100), default="Direktur")
    alamat = Column(String(255), nullable=False)
    kecamatan = Column(String(100), default="Rantepao")
    kabupaten = Column(String(100), default="Kabupaten Tana Toraja")
    provinsi = Column(String(100), default="Sulawesi Selatan")

    perjanjian_induk = relationship("PerjanjianInduk", back_populates="distributor")


class Kios(Base):
    """Pihak Kedua (Kios Pengecer Resmi)"""
    __tablename__ = "kios"

    id = Column(Integer, primary_key=True, autoincrement=True)
    nama_kios = Column(String(150), nullable=False)
    nama_pemilik = Column(String(100), nullable=False)
    jabatan = Column(String(100), default="PIMPINAN")
    alamat = Column(String(255), nullable=False)
    kecamatan = Column(String(255), nullable=False)
    kabupaten = Column(String(100), default="Tana Toraja")
    kode_kios = Column(String(50), nullable=True)
    nomor_spjb = Column(String(150), nullable=True) # Nomor Surat Perjanjian Jual Beli Pokok (misal: 01/SP/CV.ST/I/2022)

    perjanjian_induk = relationship("PerjanjianInduk", back_populates="kios", cascade="all, delete-orphan")


class SKRealokasi(Base):
    """Dasar hukum penetapan / SK Kepala Dinas"""
    __tablename__ = "sk_realokasi"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tingkat = Column(String(50), nullable=False)
    nama_pejabat_dinas = Column(String(200), nullable=False)
    nama_daerah = Column(String(100), nullable=False)
    nomor_sk = Column(String(150), nullable=False)
    tanggal_sk = Column(Date, nullable=False)
    realokasi_ke = Column(String(50), nullable=False)
    tahun_anggaran = Column(Integer, nullable=False)


class JenisPupuk(Base):
    """Katalog Jenis Pupuk Bersubsidi"""
    __tablename__ = "jenis_pupuk"

    id = Column(Integer, primary_key=True, autoincrement=True)
    kode = Column(String(20), unique=True, nullable=False)
    nama = Column(String(50), nullable=False)
    satuan = Column(String(20), default="Ton/Liter")
    urutan = Column(Integer, default=1)


class PerjanjianInduk(Base):
    """Surat Perjanjian Jual Beli Pokok/Induk (SPJB)"""
    __tablename__ = "perjanjian_induk"

    id = Column(Integer, primary_key=True, autoincrement=True)
    nomor_surat = Column(String(150), nullable=False) # Nomor SPJB (01/SP/CV.ST/I/2022)
    tanggal_surat = Column(Date, nullable=False)
    tanggal_berlaku_sampai = Column(Date, nullable=False)
    distributor_id = Column(Integer, ForeignKey("distributor.id"), nullable=False)
    kios_id = Column(Integer, ForeignKey("kios.id"), nullable=False)

    distributor = relationship("Distributor", back_populates="perjanjian_induk")
    kios = relationship("Kios", back_populates="perjanjian_induk")
    addendums = relationship("Addendum", back_populates="perjanjian_induk", cascade="all, delete-orphan")


class Addendum(Base):
    """Dokumen Addendum Perjanjian Jual Beli"""
    __tablename__ = "addendum"

    id = Column(Integer, primary_key=True, autoincrement=True)
    addendum_ke = Column(String(20), default="I")
    nomor_addendum = Column(String(150), nullable=False)
    nomor_lampiran_2 = Column(String(150), nullable=False)
    kota_ttd = Column(String(100), default="Kabupaten Tana Toraja")
    tanggal_ttd = Column(Date, nullable=False)
    tanggal_berlaku_efektif = Column(Date, nullable=False)
    tahun_anggaran = Column(Integer, default=2022)

    perjanjian_induk_id = Column(Integer, ForeignKey("perjanjian_induk.id"), nullable=False)
    sk_provinsi_id = Column(Integer, ForeignKey("sk_realokasi.id"), nullable=True)
    sk_kabupaten_id = Column(Integer, ForeignKey("sk_realokasi.id"), nullable=True)

    perjanjian_induk = relationship("PerjanjianInduk", back_populates="addendums")
    sk_provinsi = relationship("SKRealokasi", foreign_keys=[sk_provinsi_id])
    sk_kabupaten = relationship("SKRealokasi", foreign_keys=[sk_kabupaten_id])
    alokasi = relationship("DetailAlokasi", back_populates="addendum", cascade="all, delete-orphan")


class DetailAlokasi(Base):
    """Matriks Alokasi Pupuk per Bulan per Kecamatan (Lampiran 2)"""
    __tablename__ = "detail_alokasi"

    id = Column(Integer, primary_key=True, autoincrement=True)
    addendum_id = Column(Integer, ForeignKey("addendum.id"), nullable=False)
    kecamatan = Column(String(100), nullable=False, default="BITTUANG")
    bulan = Column(Integer, nullable=False)
    jenis_pupuk_id = Column(Integer, ForeignKey("jenis_pupuk.id"), nullable=False)
    kuota = Column(Float, default=0.0)

    addendum = relationship("Addendum", back_populates="alokasi")
    jenis_pupuk = relationship("JenisPupuk")


class User(Base):
    """Akun login untuk mengakses sistem"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(150), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    nama = Column(String(100), default="Administrator")
