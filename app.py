import os
import io
import re
import shutil
import sqlite3
import zipfile
from collections import OrderedDict
from datetime import date, datetime
from flask import Flask, render_template, request, redirect, url_for, send_file, flash, g
from sqlalchemy import func
from sqlalchemy.orm import joinedload

from models import (
    Base, Distributor, Kios, SKRealokasi, JenisPupuk, PerjanjianInduk, Addendum, DetailAlokasi
)
from db import SessionLocal, init_db, seed_sample_data, DB_PATH
from generator import generate_docx, generate_pdf, generate_spjb_docx, generate_spjb_pdf
from terbilang import BULAN_INDONESIA, generate_nomor_surat_addendum, generate_nomor_spjb

app = Flask(__name__)
app.secret_key = "addendum-secret-key-office-distributor"

init_db()
seed_sample_data()

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "generated_docs")
os.makedirs(OUTPUT_DIR, exist_ok=True)
BACKUP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backups")
os.makedirs(BACKUP_DIR, exist_ok=True)

def get_db():
    if "db" not in g:
        g.db = SessionLocal()
    return g.db

@app.teardown_appcontext
def teardown_db(exception=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()

def generate_next_kode_kios(db):
    kios_codes = db.query(Kios.kode_kios).filter(Kios.kode_kios.isnot(None)).all()
    max_num = 0
    for (k_code,) in kios_codes:
        if k_code:
            match = re.search(r"K-(\d+)", k_code, re.IGNORECASE)
            if match:
                num = int(match.group(1))
                if num > max_num:
                    max_num = num
            else:
                match_digits = re.search(r"(\d+)", k_code)
                if match_digits:
                    num = int(match_digits.group(1))
                    if num > max_num:
                        max_num = num

    if max_num > 0:
        next_num = max_num + 1
    else:
        next_num = db.query(Kios).count() + 1
    return f"K-{next_num:03d}"

def generate_next_nomor_spjb(db, tahun: int = 2022):
    spjb_list = db.query(Kios.nomor_spjb).filter(Kios.nomor_spjb.isnot(None)).all()
    max_num = 0
    for (spjb,) in spjb_list:
        if spjb:
            match = re.search(r"^(\d+)/SP/", spjb, re.IGNORECASE)
            if match:
                num = int(match.group(1))
                if num > max_num:
                    max_num = num
    if max_num > 0:
        next_num = max_num + 1
    else:
        next_num = db.query(Kios).count() + 1
    return generate_nomor_spjb(next_num, tahun)

@app.route("/")
def index():
    db = get_db()
    addendums = (
        db.query(Addendum)
        .options(
            joinedload(Addendum.perjanjian_induk).joinedload(PerjanjianInduk.kios),
            joinedload(Addendum.perjanjian_induk).joinedload(PerjanjianInduk.distributor)
        )
        .order_by(Addendum.id.desc())
        .all()
    )

    for a in addendums:
        total = db.query(func.sum(DetailAlokasi.kuota)).filter(DetailAlokasi.addendum_id == a.id).scalar() or 0.0
        a.total_kuota = int(total) if total.is_integer() else total

        kec_records = db.query(DetailAlokasi.kecamatan).filter(DetailAlokasi.addendum_id == a.id).distinct().all()
        a.daftar_kec = [k[0] for k in kec_records if k[0]]

    total_addendum = len(addendums)
    total_kios = db.query(Kios).count()

    pupuk_npk = db.query(JenisPupuk).filter(JenisPupuk.kode == "NPK").first()
    total_npk = 0.0
    if pupuk_npk:
        total_npk = db.query(func.sum(DetailAlokasi.kuota)).filter(DetailAlokasi.jenis_pupuk_id == pupuk_npk.id).scalar() or 0.0
        total_npk = int(total_npk) if total_npk.is_integer() else total_npk

    sk_terakhir = db.query(SKRealokasi).order_by(SKRealokasi.id.desc()).first()
    tahun_anggaran = addendums[0].tahun_anggaran if addendums else 2022

    return render_template(
        "index.html",
        addendums=addendums,
        total_addendum=total_addendum,
        total_kios=total_kios,
        total_npk=total_npk,
        sk_terakhir=sk_terakhir,
        tahun_anggaran=tahun_anggaran
    )


@app.route("/addendum/<int:addendum_id>")
def addendum_detail(addendum_id):
    db = get_db()
    addendum = (
        db.query(Addendum)
        .options(
            joinedload(Addendum.perjanjian_induk).joinedload(PerjanjianInduk.kios),
            joinedload(Addendum.perjanjian_induk).joinedload(PerjanjianInduk.distributor),
            joinedload(Addendum.sk_provinsi),
            joinedload(Addendum.sk_kabupaten)
        )
        .filter(Addendum.id == addendum_id)
        .first()
    )
    if not addendum:
        flash("Addendum tidak ditemukan", "danger")
        return redirect(url_for("index"))

    jenis_pupuk_list = db.query(JenisPupuk).order_by(JenisPupuk.urutan).all()
    detail_records = db.query(DetailAlokasi).filter(DetailAlokasi.addendum_id == addendum.id).all()

    kios_kec = addendum.perjanjian_induk.kios.kecamatan or "BITTUANG"
    kecamatan_set = OrderedDict()
    for rec in detail_records:
        k = (rec.kecamatan or kios_kec).strip().upper()
        kecamatan_set[k] = True

    if not kecamatan_set:
        kecamatan_set[kios_kec.strip().upper()] = True

    daftar_kecamatan = list(kecamatan_set.keys())

    kecamatan_tables = []
    grand_totals = {p.id: 0.0 for p in jenis_pupuk_list}

    for kec in daftar_kecamatan:
        matriks = {b: {p.id: 0.0 for p in jenis_pupuk_list} for b in range(1, 13)}
        tot_per_pupuk = {p.id: 0.0 for p in jenis_pupuk_list}

        for rec in detail_records:
            rec_kec = (rec.kecamatan or kios_kec).strip().upper()
            if rec_kec == kec:
                if rec.bulan in matriks and rec.jenis_pupuk_id in matriks[rec.bulan]:
                    matriks[rec.bulan][rec.jenis_pupuk_id] = int(rec.kuota) if rec.kuota.is_integer() else rec.kuota
                    tot_per_pupuk[rec.jenis_pupuk_id] += rec.kuota
                    grand_totals[rec.jenis_pupuk_id] += rec.kuota

        totals_formatted = []
        for p in jenis_pupuk_list:
            tot = tot_per_pupuk[p.id]
            totals_formatted.append(int(tot) if tot.is_integer() else tot)

        kecamatan_tables.append({
            "kecamatan": kec,
            "matriks": matriks,
            "totals": totals_formatted
        })

    rows_data = [
        {"no": b, "bulan": BULAN_INDONESIA.get(b, "").upper()} for b in range(1, 13)
    ]

    grand_totals_formatted = [
        int(grand_totals[p.id]) if grand_totals[p.id].is_integer() else grand_totals[p.id]
        for p in jenis_pupuk_list
    ]

    return render_template(
        "addendum_detail.html",
        addendum=addendum,
        jenis_pupuk_list=jenis_pupuk_list,
        daftar_kecamatan=daftar_kecamatan,
        kecamatan_tables=kecamatan_tables,
        grand_totals=grand_totals_formatted,
        rows_data=rows_data
    )


@app.route("/addendum/<int:addendum_id>/update-allocation", methods=["POST"])
def update_allocation(addendum_id):
    db = get_db()
    addendum = db.query(Addendum).filter(Addendum.id == addendum_id).first()
    if not addendum:
        flash("Addendum tidak ditemukan", "danger")
        return redirect(url_for("index"))

    jenis_pupuk_list = db.query(JenisPupuk).order_by(JenisPupuk.urutan).all()
    kecamatan_list = request.form.getlist("kecamatan_list")
    if not kecamatan_list:
        flash("Tidak ada kecamatan yang diperbarui.", "danger")
        return redirect(url_for("addendum_detail", addendum_id=addendum_id))

    for kec in kecamatan_list:
        kec_clean = kec.strip().upper()
        for b in range(1, 13):
            for p in jenis_pupuk_list:
                field_name = f"kuota_{kec_clean}_{b}_{p.id}"
                val_str = request.form.get(field_name, "0")
                try:
                    val = float(val_str)
                except ValueError:
                    val = 0.0

                rec = db.query(DetailAlokasi).filter(
                    DetailAlokasi.addendum_id == addendum.id,
                    DetailAlokasi.kecamatan == kec_clean,
                    DetailAlokasi.bulan == b,
                    DetailAlokasi.jenis_pupuk_id == p.id
                ).first()

                if rec:
                    rec.kuota = val
                else:
                    db.add(DetailAlokasi(
                        addendum_id=addendum.id,
                        kecamatan=kec_clean,
                        bulan=b,
                        jenis_pupuk_id=p.id,
                        kuota=val
                    ))

    db.commit()
    flash("Perubahan kuota seluruh tabel kecamatan berhasil disimpan!", "success")
    return redirect(url_for("addendum_detail", addendum_id=addendum_id))


@app.route("/addendum/<int:addendum_id>/add-kecamatan", methods=["POST"])
def add_kecamatan_to_addendum(addendum_id):
    db = get_db()
    addendum = db.query(Addendum).filter(Addendum.id == addendum_id).first()
    if not addendum:
        flash("Addendum tidak ditemukan", "danger")
        return redirect(url_for("index"))

    nama_kecamatan = request.form.get("nama_kecamatan", "").strip().upper()
    if not nama_kecamatan:
        flash("Nama kecamatan tidak boleh kosong!", "danger")
        return redirect(url_for("addendum_detail", addendum_id=addendum_id))

    existing = db.query(DetailAlokasi).filter(
        DetailAlokasi.addendum_id == addendum.id,
        DetailAlokasi.kecamatan == nama_kecamatan
    ).first()

    if existing:
        flash(f"Tabel untuk Kecamatan {nama_kecamatan} sudah ada pada addendum ini!", "danger")
        return redirect(url_for("addendum_detail", addendum_id=addendum_id))

    jenis_pupuk_list = db.query(JenisPupuk).order_by(JenisPupuk.urutan).all()
    for b in range(1, 13):
        for p in jenis_pupuk_list:
            db.add(DetailAlokasi(
                addendum_id=addendum.id,
                kecamatan=nama_kecamatan,
                bulan=b,
                jenis_pupuk_id=p.id,
                kuota=0.0
            ))

    db.commit()
    flash(f"Tabel Alokasi untuk Kecamatan {nama_kecamatan} berhasil ditambahkan!", "success")
    return redirect(url_for("addendum_detail", addendum_id=addendum_id))


@app.route("/addendum/<int:addendum_id>/delete-kecamatan", methods=["POST"])
def delete_kecamatan_from_addendum(addendum_id):
    db = get_db()
    nama_kecamatan = request.form.get("nama_kecamatan", "").strip().upper()

    distinct_kec = db.query(DetailAlokasi.kecamatan).filter(DetailAlokasi.addendum_id == addendum_id).distinct().all()
    if len(distinct_kec) <= 1:
        flash("Minimal harus ada 1 tabel kecamatan dalam dokumen addendum!", "danger")
        return redirect(url_for("addendum_detail", addendum_id=addendum_id))

    db.query(DetailAlokasi).filter(
        DetailAlokasi.addendum_id == addendum_id,
        DetailAlokasi.kecamatan == nama_kecamatan
    ).delete()

    db.commit()
    flash(f"Tabel alokasi untuk Kecamatan {nama_kecamatan} berhasil dihapus!", "success")
    return redirect(url_for("addendum_detail", addendum_id=addendum_id))


@app.route("/addendum/create", methods=["GET", "POST"])
def create_addendum():
    db = get_db()

    if request.method == "POST":
        perjanjian_induk_id = int(request.form.get("perjanjian_induk_id"))
        addendum_ke = request.form.get("addendum_ke", "I").strip().upper()
        nomor_addendum = request.form.get("nomor_addendum", "").strip()
        nomor_lampiran_2 = request.form.get("nomor_lampiran_2", "").strip()
        tanggal_ttd_str = request.form.get("tanggal_ttd")
        tanggal_berlaku_str = request.form.get("tanggal_berlaku_efektif")
        sk_prov_id = int(request.form.get("sk_provinsi_id")) if request.form.get("sk_provinsi_id") else None
        sk_kab_id = int(request.form.get("sk_kabupaten_id")) if request.form.get("sk_kabupaten_id") else None

        tanggal_ttd = datetime.strptime(tanggal_ttd_str, "%Y-%m-%d").date()
        tanggal_berlaku = datetime.strptime(tanggal_berlaku_str, "%Y-%m-%d").date()

        # Update masa berlaku SPJB induk jika dikirim dari form
        tgl_spjb_sampai_str = request.form.get("tanggal_spjb_sampai")
        if tgl_spjb_sampai_str:
            pi_target = db.query(PerjanjianInduk).filter(PerjanjianInduk.id == perjanjian_induk_id).first()
            if pi_target:
                try:
                    pi_target.tanggal_berlaku_sampai = datetime.strptime(tgl_spjb_sampai_str, "%Y-%m-%d").date()
                except Exception:
                    pass

        new_addendum = Addendum(
            addendum_ke=addendum_ke,
            nomor_addendum=nomor_addendum,
            nomor_lampiran_2=nomor_lampiran_2,
            kota_ttd="Kabupaten Tana Toraja",
            tanggal_ttd=tanggal_ttd,
            tanggal_berlaku_efektif=tanggal_berlaku,
            tahun_anggaran=tanggal_berlaku.year,
            perjanjian_induk_id=perjanjian_induk_id,
            sk_provinsi_id=sk_prov_id,
            sk_kabupaten_id=sk_kab_id
        )
        db.add(new_addendum)
        db.flush()

        jenis_pupuk_list = db.query(JenisPupuk).order_by(JenisPupuk.urutan).all()

        # Baca seluruh blok tabel kecamatan yang disubmit
        blocks = request.form.getlist("kecamatan_blocks")
        if not blocks:
            # Fallback jika hanya ada format lama
            pi = db.query(PerjanjianInduk).filter(PerjanjianInduk.id == perjanjian_induk_id).first()
            fallback_kec = (pi.kios.kecamatan if (pi and pi.kios) else "BITTUANG").strip().upper()
            blocks = ["default"]
            request.form = dict(request.form)
            request.form["kecamatan_name_default"] = fallback_kec

        for b_key in blocks:
            kec_name = request.form.get(f"kecamatan_name_{b_key}", "").strip().upper()
            if not kec_name:
                continue

            for b in range(1, 13):
                for p in jenis_pupuk_list:
                    # Cek dengan key blok baru, atau fallback ke key lama
                    field_name = f"kuota_{b_key}_{b}_{p.id}"
                    val_str = request.form.get(field_name)
                    if val_str is None:
                        field_name_fallback = f"kuota_{b}_{p.id}"
                        val_str = request.form.get(field_name_fallback, "0")
                    try:
                        val = float(val_str)
                    except (ValueError, TypeError):
                        val = 0.0

                    db.add(DetailAlokasi(
                        addendum_id=new_addendum.id,
                        kecamatan=kec_name,
                        bulan=b,
                        jenis_pupuk_id=p.id,
                        kuota=val
                    ))

        db.commit()
        flash("Dokumen Addendum baru berhasil dibuat lengkap dengan seluruh tabel kecamatan!", "success")
        return redirect(url_for("addendum_detail", addendum_id=new_addendum.id))

    perjanjian_induk_list = db.query(PerjanjianInduk).options(joinedload(PerjanjianInduk.kios)).all()
    sk_provinsi_list = db.query(SKRealokasi).filter(SKRealokasi.tingkat == "Provinsi").all()
    sk_kabupaten_list = db.query(SKRealokasi).filter(SKRealokasi.tingkat == "Kabupaten").all()
    jenis_pupuk_list = db.query(JenisPupuk).order_by(JenisPupuk.urutan).all()

    bulan_list = [(b, BULAN_INDONESIA.get(b, "").upper()) for b in range(1, 13)]
    today = date.today()
    default_date = today.strftime("%Y-%m-%d")

    total_existing = db.query(Addendum).count()
    suggested_urut = total_existing + 1
    suggested_nomor = generate_nomor_surat_addendum(suggested_urut, today)
    suggested_lampiran = generate_nomor_surat_addendum(suggested_urut, today, format_lampiran=True)

    # Siapkan data default kecamatan kios
    default_kios_kec = "BITTUANG"
    if perjanjian_induk_list and perjanjian_induk_list[0].kios:
        default_kios_kec = perjanjian_induk_list[0].kios.kecamatan.upper()

    return render_template(
        "addendum_form.html",
        perjanjian_induk_list=perjanjian_induk_list,
        sk_provinsi_list=sk_provinsi_list,
        sk_kabupaten_list=sk_kabupaten_list,
        jenis_pupuk_list=jenis_pupuk_list,
        bulan_list=bulan_list,
        default_date=default_date,
        suggested_urut=suggested_urut,
        suggested_nomor=suggested_nomor,
        suggested_lampiran=suggested_lampiran,
        default_kios_kec=default_kios_kec
    )


@app.route("/addendum/<int:addendum_id>/pdf")
def download_pdf(addendum_id):
    db = get_db()
    addendum = db.query(Addendum).filter(Addendum.id == addendum_id).first()
    if not addendum:
        return "Addendum tidak ditemukan", 404

    kios_name = addendum.perjanjian_induk.kios.nama_kios.replace(" ", "_")
    filename = f"ADDENDUM_{addendum.addendum_ke}_{kios_name}.pdf"
    file_path = os.path.join(OUTPUT_DIR, filename)

    generate_pdf(addendum_id, file_path)
    return send_file(file_path, as_attachment=True, download_name=filename, mimetype="application/pdf")


@app.route("/addendum/<int:addendum_id>/docx")
def download_docx(addendum_id):
    db = get_db()
    addendum = db.query(Addendum).filter(Addendum.id == addendum_id).first()
    if not addendum:
        return "Addendum tidak ditemukan", 404

    kios_name = addendum.perjanjian_induk.kios.nama_kios.replace(" ", "_")
    filename = f"ADDENDUM_{addendum.addendum_ke}_{kios_name}.docx"
    file_path = os.path.join(OUTPUT_DIR, filename)

    generate_docx(addendum_id, file_path)
    return send_file(file_path, as_attachment=True, download_name=filename, mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document")


@app.route("/batch/zip")
def batch_zip():
    db = get_db()
    addendums = db.query(Addendum).all()

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for item in addendums:
            kios_name = item.perjanjian_induk.kios.nama_kios.replace(" ", "_")
            pdf_name = f"PDF/ADDENDUM_{item.addendum_ke}_{kios_name}.pdf"
            docx_name = f"DOCX/ADDENDUM_{item.addendum_ke}_{kios_name}.docx"

            temp_pdf = os.path.join(OUTPUT_DIR, f"temp_{item.id}.pdf")
            temp_docx = os.path.join(OUTPUT_DIR, f"temp_{item.id}.docx")

            generate_pdf(item.id, temp_pdf)
            generate_docx(item.id, temp_docx)

            zip_file.write(temp_pdf, arcname=pdf_name)
            zip_file.write(temp_docx, arcname=docx_name)

            if os.path.exists(temp_pdf): os.remove(temp_pdf)
            if os.path.exists(temp_docx): os.remove(temp_docx)

    zip_buffer.seek(0)
    zip_filename = f"BATCH_ADDENDUM_{date.today().strftime('%Y%m%d')}.zip"
    return send_file(
        zip_buffer,
        as_attachment=True,
        download_name=zip_filename,
        mimetype="application/zip"
    )


@app.route("/addendum/<int:addendum_id>/update-spjb-expiry", methods=["POST"])
def update_spjb_expiry(addendum_id):
    db = get_db()
    addendum = db.query(Addendum).filter(Addendum.id == addendum_id).first()
    if not addendum:
        flash("Addendum tidak ditemukan", "danger")
        return redirect(url_for("index"))

    tgl_exp_str = request.form.get("tanggal_berlaku_sampai")
    if tgl_exp_str and addendum.perjanjian_induk:
        try:
            addendum.perjanjian_induk.tanggal_berlaku_sampai = datetime.strptime(tgl_exp_str, "%Y-%m-%d").date()
            db.commit()
            flash(f"Masa berlaku SPJB berhasil diperbarui menjadi {addendum.perjanjian_induk.tanggal_berlaku_sampai.strftime('%d-%m-%Y')}!", "success")
        except Exception as e:
            flash(f"Gagal memperbarui tanggal: {str(e)}", "danger")
    return redirect(url_for("addendum_detail", addendum_id=addendum_id))


# ==========================================
# MASTER KIOS: LIST, CREATE, EDIT, DELETE & SPJB
# ==========================================
@app.route("/kios")
def kios_list():
    db = get_db()
    kios = db.query(Kios).order_by(Kios.nama_kios).all()
    next_kode_kios = generate_next_kode_kios(db)
    next_nomor_spjb = generate_next_nomor_spjb(db)
    return render_template("kios_list.html", kios=kios, next_kode_kios=next_kode_kios, next_nomor_spjb=next_nomor_spjb)


@app.route("/kios/create", methods=["POST"])
def create_kios():
    db = get_db()
    nama_kios = request.form.get("nama_kios", "").strip().upper()
    nama_pemilik = request.form.get("nama_pemilik", "").strip().upper()
    jabatan = request.form.get("jabatan", "PIMPINAN").strip().upper()
    alamat = request.form.get("alamat", "").strip()
    kecamatan = request.form.get("kecamatan", "").strip()
    
    kode_kios = request.form.get("kode_kios", "").strip().upper()
    if not kode_kios:
        kode_kios = generate_next_kode_kios(db)

    nomor_spjb = request.form.get("nomor_spjb", "").strip()
    if not nomor_spjb:
        nomor_spjb = generate_next_nomor_spjb(db)

    tgl_exp_str = request.form.get("tanggal_berlaku_sampai", "2022-12-31")
    try:
        tgl_exp = datetime.strptime(tgl_exp_str, "%Y-%m-%d").date()
    except Exception:
        tgl_exp = date(2022, 12, 31)

    new_kios = Kios(
        nama_kios=nama_kios,
        nama_pemilik=nama_pemilik,
        jabatan=jabatan,
        alamat=alamat,
        kecamatan=kecamatan,
        kabupaten="Tana Toraja",
        kode_kios=kode_kios,
        nomor_spjb=nomor_spjb
    )
    db.add(new_kios)
    db.flush()

    dist = db.query(Distributor).first()
    if dist:
        pi = PerjanjianInduk(
            nomor_surat=nomor_spjb,
            tanggal_surat=date(2022, 1, 3),
            tanggal_berlaku_sampai=tgl_exp,
            distributor_id=dist.id,
            kios_id=new_kios.id
        )
        db.add(pi)

    db.commit()
    flash(f"Kios {nama_kios} ({kode_kios}) berhasil ditambahkan!", "success")
    return redirect(url_for("kios_list"))


@app.route("/kios/<int:kios_id>/edit", methods=["POST"])
def edit_kios(kios_id):
    db = get_db()
    kios = db.query(Kios).filter(Kios.id == kios_id).first()
    if not kios:
        flash("Kios tidak ditemukan", "danger")
        return redirect(url_for("kios_list"))

    kios.nama_kios = request.form.get("nama_kios", kios.nama_kios).strip().upper()
    kios.nama_pemilik = request.form.get("nama_pemilik", kios.nama_pemilik).strip().upper()
    kios.jabatan = request.form.get("jabatan", kios.jabatan).strip().upper()
    kios.alamat = request.form.get("alamat", kios.alamat).strip()
    kios.kecamatan = request.form.get("kecamatan", kios.kecamatan).strip()
    kios.kode_kios = request.form.get("kode_kios", kios.kode_kios).strip().upper()
    kios.nomor_spjb = request.form.get("nomor_spjb", kios.nomor_spjb or "").strip()

    # Sinkronisasi dengan PerjanjianInduk jika ada
    pi = db.query(PerjanjianInduk).filter(PerjanjianInduk.kios_id == kios.id).first()
    if pi:
        if kios.nomor_spjb:
            pi.nomor_surat = kios.nomor_spjb
        tgl_exp_str = request.form.get("tanggal_berlaku_sampai")
        if tgl_exp_str:
            try:
                pi.tanggal_berlaku_sampai = datetime.strptime(tgl_exp_str, "%Y-%m-%d").date()
            except Exception:
                pass

    db.commit()
    flash(f"Data kios {kios.nama_kios} berhasil diperbarui!", "success")
    return redirect(url_for("kios_list"))


@app.route("/kios/<int:kios_id>/delete", methods=["POST"])
def delete_kios(kios_id):
    db = get_db()
    kios = db.query(Kios).filter(Kios.id == kios_id).first()
    if not kios:
        flash("Kios tidak ditemukan", "danger")
        return redirect(url_for("kios_list"))

    nama_kios = kios.nama_kios
    db.delete(kios)
    db.commit()
    flash(f"Kios {nama_kios} berhasil dihapus beserta perjanjian induk terkait!", "success")
    return redirect(url_for("kios_list"))


@app.route("/kios/<int:kios_id>/spjb/pdf")
def spjb_pdf(kios_id):
    db = get_db()
    kios = db.query(Kios).filter(Kios.id == kios_id).first()
    if not kios:
        flash("Kios tidak ditemukan", "danger")
        return redirect(url_for("kios_list"))

    clean_kios_name = re.sub(r'[^a-zA-Z0-9_\-]', '_', kios.nama_kios)
    filename = f"SPJB_{clean_kios_name}.pdf"
    filepath = os.path.join(OUTPUT_DIR, filename)
    generate_spjb_pdf(kios_id, filepath)
    return send_file(filepath, as_attachment=True, download_name=filename, mimetype="application/pdf")


@app.route("/kios/<int:kios_id>/spjb/docx")
def spjb_docx(kios_id):
    db = get_db()
    kios = db.query(Kios).filter(Kios.id == kios_id).first()
    if not kios:
        flash("Kios tidak ditemukan", "danger")
        return redirect(url_for("kios_list"))

    clean_kios_name = re.sub(r'[^a-zA-Z0-9_\-]', '_', kios.nama_kios)
    filename = f"SPJB_{clean_kios_name}.docx"
    filepath = os.path.join(OUTPUT_DIR, filename)
    generate_spjb_docx(kios_id, filepath)
    return send_file(
        filepath,
        as_attachment=True,
        download_name=filename,
        mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )


# ==========================================
# MASTER SK REALOKASI
# ==========================================
@app.route("/sk")
def sk_list():
    db = get_db()
    sk_items = db.query(SKRealokasi).order_by(SKRealokasi.tanggal_sk.desc()).all()
    return render_template("sk_list.html", sk_list=sk_items)


@app.route("/sk/create", methods=["POST"])
def create_sk():
    tingkat = request.form.get("tingkat")
    realokasi_ke = request.form.get("realokasi_ke")
    nomor_sk = request.form.get("nomor_sk")
    tanggal_sk_str = request.form.get("tanggal_sk")
    tahun_anggaran = int(request.form.get("tahun_anggaran", 2022))
    nama_pejabat_dinas = request.form.get("nama_pejabat_dinas")
    nama_daerah = request.form.get("nama_daerah")

    tanggal_sk = datetime.strptime(tanggal_sk_str, "%Y-%m-%d").date()

    db = get_db()
    new_sk = SKRealokasi(
        tingkat=tingkat,
        realokasi_ke=realokasi_ke,
        nomor_sk=nomor_sk,
        tanggal_sk=tanggal_sk,
        tahun_anggaran=tahun_anggaran,
        nama_pejabat_dinas=nama_pejabat_dinas,
        nama_daerah=nama_daerah
    )
    db.add(new_sk)
    db.commit()
    flash(f"SK {nomor_sk} berhasil ditambahkan!", "success")
    return redirect(url_for("sk_list"))


# ==========================================
# BACKUP & RESTORE DATABASE
# ==========================================
@app.route("/backup")
def backup_view():
    db = get_db()
    total_kios = db.query(Kios).count()
    total_addendum = db.query(Addendum).count()
    total_alokasi = db.query(DetailAlokasi).count()

    db_size_kb = 0
    if os.path.exists(DB_PATH):
        db_size_kb = round(os.path.getsize(DB_PATH) / 1024, 1)

    local_backups = []
    if os.path.exists(BACKUP_DIR):
        for f in sorted(os.listdir(BACKUP_DIR), reverse=True):
            if f.endswith(('.db', '.sqlite', '.sqlite3')) and not f.startswith("temp_"):
                fp = os.path.join(BACKUP_DIR, f)
                st = os.stat(fp)
                dt_str = datetime.fromtimestamp(st.st_mtime).strftime("%d/%m/%Y %H:%M:%S")
                local_backups.append({
                    "name": f,
                    "size_kb": round(st.st_size / 1024, 1),
                    "time_str": dt_str
                })

    return render_template(
        "backup.html",
        db_size_kb=db_size_kb,
        total_kios=total_kios,
        total_addendum=total_addendum,
        total_alokasi=total_alokasi,
        local_backups=local_backups
    )


@app.route("/backup/download")
def backup_download():
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"backup_addendum_{timestamp}.db"
    dest_path = os.path.join(OUTPUT_DIR, filename)

    src_con = sqlite3.connect(DB_PATH)
    dst_con = sqlite3.connect(dest_path)
    with dst_con:
        src_con.backup(dst_con)
    dst_con.close()
    src_con.close()

    return send_file(
        dest_path,
        as_attachment=True,
        download_name=filename,
        mimetype="application/x-sqlite3"
    )


@app.route("/backup/sql")
def backup_sql():
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"backup_addendum_{timestamp}.sql"
    dest_path = os.path.join(OUTPUT_DIR, filename)

    con = sqlite3.connect(DB_PATH)
    with open(dest_path, "w", encoding="utf-8") as f:
        for line in con.iterdump():
            f.write(f"{line}\n")
    con.close()

    return send_file(
        dest_path,
        as_attachment=True,
        download_name=filename,
        mimetype="text/plain"
    )


@app.route("/backup/create-local", methods=["POST"])
def create_local_snapshot():
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"snapshot_addendum_{timestamp}.db"
    dest_path = os.path.join(BACKUP_DIR, filename)

    src_con = sqlite3.connect(DB_PATH)
    dst_con = sqlite3.connect(dest_path)
    with dst_con:
        src_con.backup(dst_con)
    dst_con.close()
    src_con.close()

    flash(f"Titik pemulihan lokal {filename} berhasil dibuat!", "success")
    return redirect(url_for("backup_view"))


@app.route("/backup/local/<filename>")
def download_local_backup_file(filename):
    safe_name = os.path.basename(filename)
    filepath = os.path.join(BACKUP_DIR, safe_name)
    if not os.path.exists(filepath):
        flash("File backup tidak ditemukan", "danger")
        return redirect(url_for("backup_view"))
    return send_file(filepath, as_attachment=True, download_name=safe_name, mimetype="application/x-sqlite3")


@app.route("/backup/local/<filename>/restore", methods=["POST"])
def restore_from_snapshot(filename):
    safe_name = os.path.basename(filename)
    filepath = os.path.join(BACKUP_DIR, safe_name)
    if not os.path.exists(filepath):
        flash("File snapshot tidak ditemukan", "danger")
        return redirect(url_for("backup_view"))

    teardown_db()

    emergency_name = f"safety_before_restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
    shutil.copy2(DB_PATH, os.path.join(BACKUP_DIR, emergency_name))

    src_con = sqlite3.connect(filepath)
    dst_con = sqlite3.connect(DB_PATH)
    with dst_con:
        src_con.backup(dst_con)
    dst_con.close()
    src_con.close()

    flash(f"Database berhasil dipulihkan dari snapshot {safe_name}! Salinan pengaman otomatis disimpan sebagai {emergency_name}.", "success")
    return redirect(url_for("backup_view"))


@app.route("/backup/restore", methods=["POST"])
def backup_restore():
    if "backup_file" not in request.files:
        flash("Tidak ada file yang dipilih", "danger")
        return redirect(url_for("backup_view"))

    file = request.files["backup_file"]
    if not file.filename:
        flash("Silakan pilih file cadangan .db", "danger")
        return redirect(url_for("backup_view"))

    temp_path = os.path.join(BACKUP_DIR, "temp_restore_upload.db")
    file.save(temp_path)

    try:
        test_con = sqlite3.connect(temp_path)
        cur = test_con.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [t[0] for t in cur.fetchall()]
        test_con.close()

        required_tables = ["kios", "addendum"]
        if not all(tbl in tables for tbl in required_tables):
            os.remove(temp_path)
            flash("File yang diunggah bukan database Addendum yang valid (tabel tidak cocok)!", "danger")
            return redirect(url_for("backup_view"))
    except Exception as e:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        flash(f"File rusak atau bukan format SQLite yang valid: {str(e)}", "danger")
        return redirect(url_for("backup_view"))

    teardown_db()

    emergency_name = f"safety_before_restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
    shutil.copy2(DB_PATH, os.path.join(BACKUP_DIR, emergency_name))

    src_con = sqlite3.connect(temp_path)
    dst_con = sqlite3.connect(DB_PATH)
    with dst_con:
        src_con.backup(dst_con)
    dst_con.close()
    src_con.close()

    if os.path.exists(temp_path):
        os.remove(temp_path)

    flash(f"Database berhasil dipulihkan dari file {file.filename}! Salinan pengaman data lama telah dibuat.", "success")
    return redirect(url_for("backup_view"))


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
