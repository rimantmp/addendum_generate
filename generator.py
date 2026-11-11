import os
from collections import OrderedDict
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT, TA_RIGHT

from models import Addendum, DetailAlokasi, JenisPupuk, Kios, Distributor, PerjanjianInduk, SKRealokasi
from db import SessionLocal
from terbilang import format_tanggal_addendum, BULAN_INDONESIA

def set_table_borders_docx(table, color="000000", sz="4", val="single"):
    tblPr = table._tbl.tblPr
    borders = parse_xml(
        f'<w:tblBorders {nsdecls("w")}>'
        f'<w:top w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>'
        f'<w:bottom w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>'
        f'<w:insideH w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>'
        f'<w:insideV w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>'
        f'<w:left w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>'
        f'<w:right w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>'
        f'</w:tblBorders>'
    )
    tblPr.append(borders)

def get_addendum_context(addendum_id: int):
    session = SessionLocal()
    addendum = session.query(Addendum).filter(Addendum.id == addendum_id).first()
    if not addendum:
        session.close()
        raise ValueError(f"Addendum ID {addendum_id} tidak ditemukan")

    pi = addendum.perjanjian_induk
    kios = pi.kios
    dist = pi.distributor
    sk_prov = addendum.sk_provinsi
    sk_kab = addendum.sk_kabupaten

    # Nomor SPJB Kios
    nomor_spjb = kios.nomor_spjb or pi.nomor_surat or "01/SP/CV.ST/I/2022"

    t_ttd = format_tanggal_addendum(addendum.tanggal_ttd)
    t_berlaku = format_tanggal_addendum(addendum.tanggal_berlaku_efektif)
    t_sk_prov = format_tanggal_addendum(sk_prov.tanggal_sk) if sk_prov else {}
    t_sk_kab = format_tanggal_addendum(sk_kab.tanggal_sk) if sk_kab else {}
    t_pi_exp = format_tanggal_addendum(pi.tanggal_berlaku_sampai)

    jenis_pupuk_list = session.query(JenisPupuk).order_by(JenisPupuk.urutan).all()

    detail_records = session.query(DetailAlokasi).filter(DetailAlokasi.addendum_id == addendum.id).all()

    kecamatan_set = OrderedDict()
    for rec in detail_records:
        kec = (rec.kecamatan or kios.kecamatan or "BITTUANG").strip().upper()
        kecamatan_set[kec] = True

    if not kecamatan_set:
        kecamatan_set[kios.kecamatan.upper() if kios.kecamatan else "BITTUANG"] = True

    daftar_kecamatan = list(kecamatan_set.keys())

    kecamatan_data_list = []
    grand_totals = {p.id: 0.0 for p in jenis_pupuk_list}

    for kec in daftar_kecamatan:
        matriks = {b: {p.id: 0.0 for p in jenis_pupuk_list} for b in range(1, 13)}
        tot_per_pupuk = {p.id: 0.0 for p in jenis_pupuk_list}

        for rec in detail_records:
            rec_kec = (rec.kecamatan or kios.kecamatan or "BITTUANG").strip().upper()
            if rec_kec == kec:
                if rec.bulan in matriks and rec.jenis_pupuk_id in matriks[rec.bulan]:
                    matriks[rec.bulan][rec.jenis_pupuk_id] = rec.kuota
                    tot_per_pupuk[rec.jenis_pupuk_id] += rec.kuota
                    grand_totals[rec.jenis_pupuk_id] += rec.kuota

        rows_data = []
        for b in range(1, 13):
            nama_bulan = BULAN_INDONESIA.get(b, "").upper()
            vals = []
            for p in jenis_pupuk_list:
                v = matriks[b][p.id]
                vals.append(int(v) if v.is_integer() else v)
            rows_data.append({
                "no": b,
                "bulan": nama_bulan,
                "values": vals
            })

        totals_formatted = []
        for p in jenis_pupuk_list:
            tot = tot_per_pupuk[p.id]
            totals_formatted.append(int(tot) if tot.is_integer() else tot)

        kecamatan_data_list.append({
            "kecamatan": kec,
            "rows_data": rows_data,
            "totals": totals_formatted,
            "matriks": matriks
        })

    grand_totals_formatted = []
    for p in jenis_pupuk_list:
        gtot = grand_totals[p.id]
        grand_totals_formatted.append(int(gtot) if gtot.is_integer() else gtot)

    ctx = {
        "addendum": addendum,
        "pi": pi,
        "kios": kios,
        "nomor_spjb": nomor_spjb,
        "dist": dist,
        "sk_prov": sk_prov,
        "sk_kab": sk_kab,
        "t_ttd": t_ttd,
        "t_berlaku": t_berlaku,
        "t_sk_prov": t_sk_prov,
        "t_sk_kab": t_sk_kab,
        "t_pi_exp": t_pi_exp,
        "jenis_pupuk_list": jenis_pupuk_list,
        "daftar_kecamatan": daftar_kecamatan,
        "kecamatan_data_list": kecamatan_data_list,
        "grand_totals": grand_totals_formatted,
        "has_multiple_kecamatan": len(daftar_kecamatan) > 1,
        "satuan": jenis_pupuk_list[0].satuan if jenis_pupuk_list else "Ton/Liter"
    }
    session.close()
    return ctx


# ==========================================
# 1. GENERATOR ADDENDUM DOCX (WORD)
# ==========================================
def generate_docx(addendum_id: int, output_path: str):
    ctx = get_addendum_context(addendum_id)
    doc = Document()

    for section in doc.sections:
        section.top_margin = Inches(0.8)
        section.bottom_margin = Inches(0.8)
        section.left_margin = Inches(1.0)
        section.right_margin = Inches(1.0)
        section.page_width = Inches(8.27)
        section.page_height = Inches(11.69)

    def add_p(text="", align=WD_ALIGN_PARAGRAPH.JUSTIFY, bold=False, space_after=4, space_before=0, font_size=11):
        p = doc.add_paragraph()
        p.alignment = align
        p.paragraph_format.space_after = Pt(space_after)
        p.paragraph_format.space_before = Pt(space_before)
        p.paragraph_format.line_spacing = 1.15
        if text:
            run = p.add_run(text)
            run.bold = bold
            run.font.name = "Arial"
            run.font.size = Pt(font_size)
            run.font.color.rgb = RGBColor(0, 0, 0)
        return p

    # --- HALAMAN 1 ---
    add_p(f"ADDENDUM {ctx['addendum'].addendum_ke}", align=WD_ALIGN_PARAGRAPH.CENTER, bold=True, font_size=11, space_after=1)
    add_p("SURAT PERJANJIAN", align=WD_ALIGN_PARAGRAPH.CENTER, bold=True, font_size=11, space_after=1)
    add_p("antara", align=WD_ALIGN_PARAGRAPH.CENTER, bold=False, font_size=11, space_after=1)
    add_p(ctx['dist'].nama_perusahaan, align=WD_ALIGN_PARAGRAPH.CENTER, bold=True, font_size=11, space_after=1)
    add_p("dengan", align=WD_ALIGN_PARAGRAPH.CENTER, bold=False, font_size=11, space_after=1)
    add_p(ctx['kios'].nama_kios, align=WD_ALIGN_PARAGRAPH.CENTER, bold=True, font_size=11, space_after=1)
    add_p("tentang", align=WD_ALIGN_PARAGRAPH.CENTER, bold=False, font_size=11, space_after=1)
    add_p("JUAL BELI PUPUK BERSUBSIDI", align=WD_ALIGN_PARAGRAPH.CENTER, bold=True, font_size=11, space_after=6)

    p_line = doc.add_paragraph()
    p_line.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_line.paragraph_format.space_after = Pt(4)
    run_line = p_line.add_run("―" * 46)
    run_line.bold = True

    add_p(f"NOMOR : {ctx['addendum'].nomor_addendum}", align=WD_ALIGN_PARAGRAPH.CENTER, bold=True, font_size=11, space_after=8)

    p_intro = add_p()
    p_intro.paragraph_format.line_spacing = 1.15
    p_intro.paragraph_format.space_after = Pt(8)
    p_intro.add_run(f"Addendum– {ctx['addendum'].addendum_ke} atas Surat Perjanjian antara ")
    r_dist = p_intro.add_run(ctx['dist'].nama_perusahaan)
    r_dist.bold = True
    p_intro.add_run(" dengan ")
    r_k = p_intro.add_run(ctx['kios'].nama_kios)
    r_k.bold = True
    p_intro.add_run(
        f" Nomor: {ctx['addendum'].nomor_addendum} tentang Jual Beli Pupuk Bersubsidi ( selanjutnya "
        f"disebut “Addendum- {ctx['addendum'].addendum_ke}” ) dibuat dan ditandatangani di {ctx['addendum'].kota_ttd}, pada hari ini {ctx['t_ttd']['hari']} "
        f"tanggal {ctx['t_ttd']['tanggal_terbilang']} bulan {ctx['t_ttd']['bulan_terbilang']} tahun {ctx['t_ttd']['tahun_terbilang']} ( {ctx['t_ttd']['tanggal_format_angka']} ), oleh "
        f"dan antara yang bertanda tangan di bawah ini :"
    )

    table_pihak = doc.add_table(rows=2, cols=3)
    table_pihak.alignment = WD_TABLE_ALIGNMENT.CENTER
    table_pihak.autofit = False
    col_widths = [Inches(2.2), Inches(0.2), Inches(4.2)]
    for row in table_pihak.rows:
        for idx, width in enumerate(col_widths):
            row.cells[idx].width = width

    # Row 1: Distributor
    c1 = table_pihak.cell(0, 0).paragraphs[0]
    r = c1.add_run(ctx['dist'].nama_pimpinan)
    r.bold = True
    table_pihak.cell(0, 1).paragraphs[0].add_run(":")
    c3 = table_pihak.cell(0, 2).paragraphs[0]
    c3.paragraph_format.line_spacing = 1.15
    c3.add_run(
        f"Selaku {ctx['dist'].jabatan.title()}, dengan demikian bertindak untuk dan atas nama {ctx['dist'].nama_perusahaan}, "
        f"suatu perusahaan yang didirikan dan dijalankan berdasarkan hukum Negara Republik Indonesia, "
        f"berkedudukan di {ctx['dist'].alamat} {ctx['dist'].provinsi}.\n"
        f"Selanjutnya disebut “PIHAK PERTAMA”."
    )

    # Row 2: Kios
    c1_k = table_pihak.cell(1, 0).paragraphs[0]
    r = c1_k.add_run(ctx['kios'].nama_pemilik)
    r.bold = True
    table_pihak.cell(1, 1).paragraphs[0].add_run(":")
    c3_k = table_pihak.cell(1, 2).paragraphs[0]
    c3_k.paragraph_format.line_spacing = 1.15
    c3_k.add_run(
        f"Selaku {ctx['kios'].jabatan.title()}, dengan demikian bertindak untuk dan atas nama {ctx['kios'].nama_kios} "
        f"berkedudukan di {ctx['kios'].alamat}.\n"
        f"Selanjutnya disebut “PIHAK KEDUA”."
    )

    p_hub = add_p(space_before=6, space_after=6, font_size=10.5)
    p_hub.add_run(
        "PIHAK PERTAMA dan PIHAK KEDUA ( selanjutnya secara bersama- sama disebut “PARA PIHAK”), "
        "terlebih dahulu menerangkan hal-hal sebagai berikut :"
    )

    # Poin A memuat Nomor SPJB Kios, Poin B Surat Keputusan Kabupaten
    konsiderans = [
        ("A.", f"Bahwa Para Pihak telah membuat, menandatangani dan melaksanakan Surat Perjanjian tentang Jual Beli Pupuk Bersubsidi Nomor : {ctx['nomor_spjb']} yang berlaku efektif sampai dengan tanggal {ctx['t_pi_exp']['tanggal_lengkap']} ( selanjutnya disebut sebagai “ Perjanjian Induk “)."),
        ("B.", f"Surat Keputusan {ctx['sk_kab'].nama_pejabat_dinas} Nomor : {ctx['sk_kab'].nomor_sk} Tanggal {ctx['t_sk_kab']['tanggal_lengkap']} Tentang {ctx['sk_kab'].realokasi_ke} Kebutuhan Pupuk Bersubsidi Untuk Sektor Pertanian {ctx['sk_kab'].nama_daerah} Tahun Anggaran {ctx['sk_kab'].tahun_anggaran}"),
        ("C.", f"Bahwa berdasarkan hal tersebut di atas, PARA PIHAK sepakat melakukan perubahan terhadap kebutuhan Pupuk Bersubsidi untuk sektor pertanian di tingkat Kabupaten/Kota Tahun Anggaran {ctx['addendum'].tahun_anggaran}.")
    ]

    for huruf, isi in konsiderans:
        p_k = doc.add_paragraph()
        p_k.paragraph_format.left_indent = Inches(0.3)
        p_k.paragraph_format.first_line_indent = Inches(-0.3)
        p_k.paragraph_format.space_after = Pt(4)
        p_k.paragraph_format.line_spacing = 1.15
        r_h = p_k.add_run(f"{huruf} ")
        r_h.bold = True
        p_k.add_run(isi)

    # --- HALAMAN 2 ---
    doc.add_page_break()
    add_p(
        f"Berdasarkan hal tersebut diatas, PARA PIHAK sepakat membuat dan menandatangani ADDENDUM- {ctx['addendum'].addendum_ke} "
        "dengan ketentuan dan syarat – syarat sebagai berikut :",
        space_after=8, font_size=10.5
    )

    pasal = [
        ("1.", f"Melakukan perubahan terhadap Lampiran 2 perjanjian induk Sebagaimana terlampir dalam ADDENDUM- {ctx['addendum'].addendum_ke} ini, dan mulai berlaku sejak tanggal {ctx['t_berlaku']['tanggal_lengkap']}."),
        ("2.", f"Ketentuan dan persyaratan lainnya dari perjanjian induk sepanjang tidak diubah atau diatur lain dalam ADDENDUM- {ctx['addendum'].addendum_ke} ini tetap berlaku."),
        ("3.", f"ADDENDUM- {ctx['addendum'].addendum_ke} ini merupakan satu kesatuan dan bagian yang tidak dapat terpisahkan dengan perjanjian induk.")
    ]

    for no, isi in pasal:
        p_p = doc.add_paragraph()
        p_p.paragraph_format.left_indent = Inches(0.3)
        p_p.paragraph_format.first_line_indent = Inches(-0.3)
        p_p.paragraph_format.space_after = Pt(6)
        p_p.paragraph_format.line_spacing = 1.15
        r_no = p_p.add_run(f"{no} ")
        r_no.bold = True
        p_p.add_run(isi)

    add_p(
        f"Demikian ADDENDUM- {ctx['addendum'].addendum_ke} ini dibuat dan ditandatangani oleh PARA PIHAK pada hari dan tanggal tersebut diatas "
        "dalam rangkap 2 ( dua ) asli, dan mempunyai kekuatan hukum yang sama.",
        space_before=10, space_after=24, font_size=10.5
    )

    table_ttd = doc.add_table(rows=3, cols=2)
    table_ttd.alignment = WD_TABLE_ALIGNMENT.CENTER
    table_ttd.autofit = False
    for row in table_ttd.rows:
        row.cells[0].width = Inches(3.3)
        row.cells[1].width = Inches(3.3)

    p_kios_hdr = table_ttd.cell(0, 0).paragraphs[0]
    r = p_kios_hdr.add_run(f"PIHAK KEDUA\n{ctx['kios'].nama_kios}")
    r.bold = True

    p_dist_hdr = table_ttd.cell(0, 1).paragraphs[0]
    r = p_dist_hdr.add_run(f"PIHAK PERTAMA\n{ctx['dist'].nama_perusahaan}")
    r.bold = True

    table_ttd.cell(1, 0).paragraphs[0].add_run("\n\n\n\n")
    table_ttd.cell(1, 1).paragraphs[0].add_run("\n\n\n\n")

    p_kios_fn = table_ttd.cell(2, 0).paragraphs[0]
    r = p_kios_fn.add_run(f"{ctx['kios'].nama_pemilik}\n")
    r.bold = True; r.underline = True
    r_j = p_kios_fn.add_run(ctx['kios'].jabatan.upper())
    r_j.bold = True

    p_dist_fn = table_ttd.cell(2, 1).paragraphs[0]
    r = p_dist_fn.add_run(f"{ctx['dist'].nama_pimpinan}\n")
    r.bold = True; r.underline = True
    r_jd = p_dist_fn.add_run(ctx['dist'].jabatan.upper())
    r_jd.bold = True

    # --- HALAMAN LAMPIRAN 2 ---
    num_pupuk = len(ctx['jenis_pupuk_list'])
    total_cols = 2 + num_pupuk

    for k_data in ctx['kecamatan_data_list']:
        doc.add_page_break()

        add_p("Lampiran 2 : Perjanjian Jual Beli Pupuk Bersubsidi", space_after=1, font_size=10)
        add_p(f"Nomor      : {ctx['addendum'].nomor_lampiran_2}", space_after=1, font_size=10)
        add_p(f"Tanggal    : {ctx['t_berlaku']['tanggal_lengkap']}", space_after=12, font_size=10)

        judul_lampiran = (
            "JENIS, JUMLAH DAN JADWAL PENJUALAN PUPUK BERSUBSIDI\n"
            f"DARI PIHAK PERTAMA KEPADA PIHAK KEDUA\n"
            f"KECAMATAN : {k_data['kecamatan']}\n"
            f"TAHUN {ctx['addendum'].tahun_anggaran}"
        )
        add_p(judul_lampiran, align=WD_ALIGN_PARAGRAPH.CENTER, bold=True, space_after=4, font_size=11)
        add_p(f"Satuan : {ctx['satuan']}", align=WD_ALIGN_PARAGRAPH.RIGHT, bold=False, space_after=4, font_size=9.5)

        table_alloc = doc.add_table(rows=15, cols=total_cols)
        table_alloc.alignment = WD_TABLE_ALIGNMENT.CENTER
        set_table_borders_docx(table_alloc)

        table_alloc.columns[0].width = Inches(0.6)
        table_alloc.columns[1].width = Inches(2.0)
        for idx in range(num_pupuk):
            table_alloc.columns[2 + idx].width = Inches(1.0)

        hdr_no = table_alloc.cell(0, 0)
        hdr_no.text = "NO"
        hdr_no.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
        hdr_no.paragraphs[0].runs[0].bold = True

        hdr_bulan = table_alloc.cell(0, 1)
        hdr_bulan.text = "BULAN"
        hdr_bulan.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
        hdr_bulan.paragraphs[0].runs[0].bold = True

        hdr_pupuk_span = table_alloc.cell(0, 2)
        hdr_pupuk_span.text = "JENIS PUPUK"
        hdr_pupuk_span.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
        hdr_pupuk_span.paragraphs[0].runs[0].bold = True
        for c_idx in range(3, total_cols):
            hdr_pupuk_span.merge(table_alloc.cell(0, c_idx))

        for idx, p in enumerate(ctx['jenis_pupuk_list']):
            sub_cell = table_alloc.cell(1, 2 + idx)
            sub_cell.text = p.kode
            sub_cell.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
            sub_cell.paragraphs[0].runs[0].bold = True

        for b_idx, row_data in enumerate(k_data['rows_data']):
            r_num = 2 + b_idx
            c_no = table_alloc.cell(r_num, 0)
            c_no.text = str(row_data['no'])
            c_no.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER

            c_bln = table_alloc.cell(r_num, 1)
            c_bln.text = row_data['bulan']
            c_bln.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.LEFT

            for p_idx, val in enumerate(row_data['values']):
                c_val = table_alloc.cell(r_num, 2 + p_idx)
                c_val.text = str(val)
                c_val.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER

        r_tot = 14
        c_tot_no = table_alloc.cell(r_tot, 0)
        c_tot_no.text = "-"
        c_tot_no.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
        c_tot_no.paragraphs[0].runs[0].bold = True

        c_tot_lbl = table_alloc.cell(r_tot, 1)
        c_tot_lbl.text = "JUMLAH"
        c_tot_lbl.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
        c_tot_lbl.paragraphs[0].runs[0].bold = True

        for p_idx, tot_val in enumerate(k_data['totals']):
            c_tot_val = table_alloc.cell(r_tot, 2 + p_idx)
            c_tot_val.text = str(tot_val)
            c_tot_val.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
            c_tot_val.paragraphs[0].runs[0].bold = True

    if ctx['has_multiple_kecamatan']:
        doc.add_page_break()
        add_p("Lampiran 2 : Rekapitulasi Seluruh Kecamatan", space_after=1, font_size=10)
        add_p(f"Nomor      : {ctx['addendum'].nomor_lampiran_2}", space_after=1, font_size=10)
        add_p(f"Tanggal    : {ctx['t_berlaku']['tanggal_lengkap']}", space_after=14, font_size=10)

        add_p(
            "REKAPITULASI TOTAL ALOKASI PUPUK BERSUBSIDI\n"
            f"DARI PIHAK PERTAMA KEPADA PIHAK KEDUA ({ctx['kios'].nama_kios})\n"
            f"TAHUN {ctx['addendum'].tahun_anggaran}",
            align=WD_ALIGN_PARAGRAPH.CENTER, bold=True, space_after=8, font_size=11
        )

        rekap_table = doc.add_table(rows=len(ctx['kecamatan_data_list']) + 2, cols=total_cols)
        rekap_table.alignment = WD_TABLE_ALIGNMENT.CENTER
        set_table_borders_docx(rekap_table)

        rekap_table.columns[0].width = Inches(0.6)
        rekap_table.columns[1].width = Inches(2.0)
        for idx in range(num_pupuk):
            rekap_table.columns[2 + idx].width = Inches(1.0)

        rekap_table.cell(0, 0).text = "NO"
        rekap_table.cell(0, 0).paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
        rekap_table.cell(0, 0).paragraphs[0].runs[0].bold = True

        rekap_table.cell(0, 1).text = "KECAMATAN"
        rekap_table.cell(0, 1).paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
        rekap_table.cell(0, 1).paragraphs[0].runs[0].bold = True

        for p_idx, p in enumerate(ctx['jenis_pupuk_list']):
            c = rekap_table.cell(0, 2 + p_idx)
            c.text = p.kode
            c.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
            c.paragraphs[0].runs[0].bold = True

        for k_idx, k_item in enumerate(ctx['kecamatan_data_list']):
            r_idx = 1 + k_idx
            rekap_table.cell(r_idx, 0).text = str(k_idx + 1)
            rekap_table.cell(r_idx, 0).paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER

            rekap_table.cell(r_idx, 1).text = k_item['kecamatan']
            rekap_table.cell(r_idx, 1).paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.LEFT

            for p_idx, tot_val in enumerate(k_item['totals']):
                c_val = rekap_table.cell(r_idx, 2 + p_idx)
                c_val.text = str(tot_val)
                c_val.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER

        r_gt = len(ctx['kecamatan_data_list']) + 1
        rekap_table.cell(r_gt, 0).text = "-"
        rekap_table.cell(r_gt, 0).paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
        rekap_table.cell(r_gt, 0).paragraphs[0].runs[0].bold = True

        rekap_table.cell(r_gt, 1).text = "TOTAL KESELURUHAN"
        rekap_table.cell(r_gt, 1).paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
        rekap_table.cell(r_gt, 1).paragraphs[0].runs[0].bold = True

        for p_idx, gtot_val in enumerate(ctx['grand_totals']):
            c_gtot = rekap_table.cell(r_gt, 2 + p_idx)
            c_gtot.text = str(gtot_val)
            c_gtot.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
            c_gtot.paragraphs[0].runs[0].bold = True

    doc.save(output_path)
    return output_path


# ==========================================
# 2. GENERATOR ADDENDUM PDF (REPORTLAB)
# ==========================================
def generate_pdf(addendum_id: int, output_path: str):
    ctx = get_addendum_context(addendum_id)

    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        leftMargin=54,
        rightMargin=54,
        topMargin=45,
        bottomMargin=45
    )

    styles = getSampleStyleSheet()

    style_center_bold = ParagraphStyle("CenterBold", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=11, leading=14, alignment=TA_CENTER)
    style_center = ParagraphStyle("CenterRegular", parent=styles["Normal"], fontName="Helvetica", fontSize=11, leading=14, alignment=TA_CENTER)
    style_body = ParagraphStyle("JustifyBody", parent=styles["Normal"], fontName="Helvetica", fontSize=10.5, leading=14.5, alignment=TA_JUSTIFY)
    style_table_desc = ParagraphStyle("TableDesc", parent=styles["Normal"], fontName="Helvetica", fontSize=10, leading=13.5, alignment=TA_JUSTIFY)
    style_table_name = ParagraphStyle("TableName", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=10, leading=13.5, alignment=TA_LEFT)

    story = []

    # --- HALAMAN 1 ---
    story.append(Paragraph(f"ADDENDUM {ctx['addendum'].addendum_ke}", style_center_bold))
    story.append(Paragraph("SURAT PERJANJIAN", style_center_bold))
    story.append(Paragraph("antara", style_center))
    story.append(Paragraph(ctx['dist'].nama_perusahaan, style_center_bold))
    story.append(Paragraph("dengan", style_center))
    story.append(Paragraph(ctx['kios'].nama_kios, style_center_bold))
    story.append(Paragraph("tentang", style_center))
    story.append(Paragraph("JUAL BELI PUPUK BERSUBSIDI", style_center_bold))
    story.append(Spacer(1, 4))
    story.append(HRFlowable(width="100%", thickness=2, color=colors.black, spaceBefore=4, spaceAfter=8))

    story.append(Paragraph(f"NOMOR : {ctx['addendum'].nomor_addendum}", style_center_bold))
    story.append(Spacer(1, 8))

    intro_p = (
        f"Addendum– {ctx['addendum'].addendum_ke} atas Surat Perjanjian antara <b>{ctx['dist'].nama_perusahaan}</b> dengan "
        f"<b>{ctx['kios'].nama_kios}</b> Nomor: <b>{ctx['addendum'].nomor_addendum}</b> tentang Jual Beli Pupuk Bersubsidi "
        f"( selanjutnya disebut <b>“Addendum- {ctx['addendum'].addendum_ke}”</b> ) dibuat dan ditandatangani di {ctx['addendum'].kota_ttd}, "
        f"pada hari ini {ctx['t_ttd']['hari']} tanggal {ctx['t_ttd']['tanggal_terbilang']} bulan {ctx['t_ttd']['bulan_terbilang']} "
        f"tahun {ctx['t_ttd']['tahun_terbilang']} ( {ctx['t_ttd']['tanggal_format_angka']} ), oleh dan antara yang bertanda tangan di bawah ini :"
    )
    story.append(Paragraph(intro_p, style_body))
    story.append(Spacer(1, 8))

    p1_desc = (
        f"Selaku {ctx['dist'].jabatan.title()}, dengan demikian bertindak untuk dan atas nama <b>{ctx['dist'].nama_perusahaan}</b>, "
        f"suatu perusahaan yang didirikan dan dijalankan berdasarkan hukum Negara Republik Indonesia, berkedudukan di {ctx['dist'].alamat} {ctx['dist'].provinsi}.<br/>"
        f"Selanjutnya disebut <b>“PIHAK PERTAMA”</b>."
    )
    p2_desc = (
        f"Selaku {ctx['kios'].jabatan.title()}, dengan demikian bertindak untuk dan atas nama <b>{ctx['kios'].nama_kios}</b> "
        f"berkedudukan di {ctx['kios'].alamat}.<br/>"
        f"Selanjutnya disebut <b>“PIHAK KEDUA”</b>."
    )

    table_data_pihak = [
        [
            Paragraph(ctx['dist'].nama_pimpinan, style_table_name),
            Paragraph(":", style_table_name),
            Paragraph(p1_desc, style_table_desc)
        ],
        [
            Paragraph(ctx['kios'].nama_pemilik, style_table_name),
            Paragraph(":", style_table_name),
            Paragraph(p2_desc, style_table_desc)
        ]
    ]

    t_pihak = Table(table_data_pihak, colWidths=[140, 15, 335])
    t_pihak.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('LEFTPADDING', (0,0), (-1,-1), 0),
        ('RIGHTPADDING', (0,0), (-1,-1), 0),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('TOPPADDING', (0,0), (-1,-1), 2),
    ]))
    story.append(t_pihak)
    story.append(Spacer(1, 6))

    story.append(Paragraph(
        "<b>PIHAK PERTAMA</b> dan <b>PIHAK KEDUA</b> ( selanjutnya secara bersama- sama disebut <b>“PARA PIHAK”</b>), "
        "terlebih dahulu menerangkan hal-hal sebagai berikut :", style_body
    ))
    story.append(Spacer(1, 6))

    konsiderans = [
        ("A.", f"Bahwa Para Pihak telah membuat, menandatangani dan melaksanakan Surat Perjanjian tentang Jual Beli Pupuk Bersubsidi Nomor : <b>{ctx['nomor_spjb']}</b> yang berlaku efektif sampai dengan tanggal {ctx['t_pi_exp']['tanggal_lengkap']} ( selanjutnya disebut sebagai <b>“ Perjanjian Induk “</b>)."),
        ("B.", f"Surat Keputusan {ctx['sk_kab'].nama_pejabat_dinas} Nomor : {ctx['sk_kab'].nomor_sk} Tanggal {ctx['t_sk_kab']['tanggal_lengkap']} Tentang {ctx['sk_kab'].realokasi_ke} Kebutuhan Pupuk Bersubsidi Untuk Sektor Pertanian {ctx['sk_kab'].nama_daerah} Tahun Anggaran {ctx['sk_kab'].tahun_anggaran}"),
        ("C.", f"Bahwa berdasarkan hal tersebut di atas, PARA PIHAK sepakat melakukan perubahan terhadap kebutuhan Pupuk Bersubsidi untuk sektor pertanian di tingkat Kabupaten/Kota Tahun Anggaran {ctx['addendum'].tahun_anggaran}.")
    ]

    for huruf, isi in konsiderans:
        t_k = Table([[Paragraph(f"<b>{huruf}</b>", style_table_name), Paragraph(isi, style_body)]], colWidths=[20, 470])
        t_k.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('LEFTPADDING', (0,0), (-1,-1), 0),
            ('RIGHTPADDING', (0,0), (-1,-1), 0),
            ('BOTTOMPADDING', (0,0), (-1,-1), 5),
            ('TOPPADDING', (0,0), (-1,-1), 0),
        ]))
        story.append(t_k)

    # --- HALAMAN 2: PASAL KESEPAKATAN & TANDA TANGAN ---
    story.append(PageBreak())

    story.append(Paragraph(
        f"Berdasarkan hal tersebut diatas, PARA PIHAK sepakat membuat dan menandatangani <b>ADDENDUM- {ctx['addendum'].addendum_ke}</b> "
        "dengan ketentuan dan syarat – syarat sebagai berikut :", style_body
    ))
    story.append(Spacer(1, 8))

    pasal = [
        ("1.", f"Melakukan perubahan terhadap Lampiran 2 perjanjian induk Sebagaimana terlampir dalam <b>ADDENDUM- {ctx['addendum'].addendum_ke}</b> ini, dan mulai berlaku sejak tanggal {ctx['t_berlaku']['tanggal_lengkap']}."),
        ("2.", f"Ketentuan dan persyaratan lainnya dari perjanjian induk sepanjang tidak diubah atau diatur lain dalam <b>ADDENDUM- {ctx['addendum'].addendum_ke}</b> ini tetap berlaku."),
        ("3.", f"<b>ADDENDUM- {ctx['addendum'].addendum_ke}</b> ini merupakan satu kesatuan dan bagian yang tidak dapat terpisahkan dengan perjanjian induk.")
    ]

    for no, isi in pasal:
        t_p = Table([[Paragraph(f"<b>{no}</b>", style_table_name), Paragraph(isi, style_body)]], colWidths=[20, 470])
        t_p.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('LEFTPADDING', (0,0), (-1,-1), 0),
            ('RIGHTPADDING', (0,0), (-1,-1), 0),
            ('BOTTOMPADDING', (0,0), (-1,-1), 6),
            ('TOPPADDING', (0,0), (-1,-1), 0),
        ]))
        story.append(t_p)

    story.append(Spacer(1, 8))
    story.append(Paragraph(
        f"Demikian <b>ADDENDUM- {ctx['addendum'].addendum_ke}</b> ini dibuat dan ditandatangani oleh <b>PARA PIHAK</b> pada hari dan tanggal "
        "tersebut diatas dalam rangkap 2 ( dua ) asli, dan mempunyai kekuatan hukum yang sama.", style_body
    ))
    story.append(Spacer(1, 28))

    ttd_kios = [
        Paragraph(f"<b>PIHAK KEDUA<br/>{ctx['kios'].nama_kios}</b>", style_center_bold),
        Spacer(1, 60),
        Paragraph(f"<u><b>{ctx['kios'].nama_pemilik}</b></u>", style_center_bold),
        Paragraph(f"<b>{ctx['kios'].jabatan.upper()}</b>", style_center_bold)
    ]
    ttd_dist = [
        Paragraph(f"<b>PIHAK PERTAMA<br/>{ctx['dist'].nama_perusahaan}</b>", style_center_bold),
        Spacer(1, 60),
        Paragraph(f"<u><b>{ctx['dist'].nama_pimpinan}</b></u>", style_center_bold),
        Paragraph(f"<b>{ctx['dist'].jabatan.upper()}</b>", style_center_bold)
    ]

    t_ttd = Table([[ttd_kios, ttd_dist]], colWidths=[245, 245])
    t_ttd.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('LEFTPADDING', (0,0), (-1,-1), 0),
        ('RIGHTPADDING', (0,0), (-1,-1), 0),
    ]))
    story.append(t_ttd)

    # --- HALAMAN LAMPIRAN 2 ---
    num_pupuk = len(ctx['jenis_pupuk_list'])
    style_satuan = ParagraphStyle("Satuan", parent=styles["Normal"], fontName="Helvetica", fontSize=9.5, alignment=TA_RIGHT)
    style_tbl_cell = ParagraphStyle("CellCenter", parent=styles["Normal"], fontName="Helvetica", fontSize=9, alignment=TA_CENTER)
    style_tbl_bulan = ParagraphStyle("CellBulan", parent=styles["Normal"], fontName="Helvetica", fontSize=9, alignment=TA_LEFT)
    style_tbl_bold = ParagraphStyle("CellBold", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=9, alignment=TA_CENTER)

    for k_data in ctx['kecamatan_data_list']:
        story.append(PageBreak())

        lamp_meta = [
            [Paragraph("Lampiran 2", style_table_desc), Paragraph(":", style_table_desc), Paragraph("Perjanjian Jual Beli Pupuk Bersubsidi", style_table_desc)],
            [Paragraph("Nomor", style_table_desc), Paragraph(":", style_table_desc), Paragraph(ctx['addendum'].nomor_lampiran_2, style_table_desc)],
            [Paragraph("Tanggal", style_table_desc), Paragraph(":", style_table_desc), Paragraph(ctx['t_berlaku']['tanggal_lengkap'], style_table_desc)],
        ]
        t_lamp_meta = Table(lamp_meta, colWidths=[70, 10, 410])
        t_lamp_meta.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('LEFTPADDING', (0,0), (-1,-1), 0),
            ('BOTTOMPADDING', (0,0), (-1,-1), 1),
            ('TOPPADDING', (0,0), (-1,-1), 1),
        ]))
        story.append(t_lamp_meta)
        story.append(Spacer(1, 10))

        judul_lamp = (
            "<b>JENIS, JUMLAH DAN JADWAL PENJUALAN PUPUK BERSUBSIDI<br/>"
            f"DARI PIHAK PERTAMA KEPADA PIHAK KEDUA<br/>"
            f"KECAMATAN : {k_data['kecamatan']}<br/>"
            f"TAHUN {ctx['addendum'].tahun_anggaran}</b>"
        )
        story.append(Paragraph(judul_lamp, style_center_bold))
        story.append(Spacer(1, 6))
        story.append(Paragraph(f"Satuan : {ctx['satuan']}", style_satuan))
        story.append(Spacer(1, 4))

        row0 = [
            Paragraph("<b>NO</b>", style_center_bold),
            Paragraph("<b>BULAN</b>", style_center_bold),
            Paragraph("<b>JENIS PUPUK</b>", style_center_bold)
        ] + [""] * (num_pupuk - 1)

        row1 = ["", ""] + [Paragraph(f"<b>{p.kode}</b>", style_center_bold) for p in ctx['jenis_pupuk_list']]
        matrix_rows = [row0, row1]

        for r in k_data['rows_data']:
            row_vals = [
                Paragraph(str(r['no']), style_tbl_cell),
                Paragraph(r['bulan'], style_tbl_bulan),
            ] + [Paragraph(str(v), style_tbl_cell) for v in r['values']]
            matrix_rows.append(row_vals)

        row_tot = [
            Paragraph("-", style_tbl_bold),
            Paragraph("<b>JUMLAH</b>", style_tbl_bold),
        ] + [Paragraph(str(tot), style_tbl_bold) for tot in k_data['totals']]
        matrix_rows.append(row_tot)

        col_widths_matrix = [35, 145] + [310 / num_pupuk] * num_pupuk
        t_matrix = Table(matrix_rows, colWidths=col_widths_matrix, repeatRows=2)
        t_matrix.setStyle(TableStyle([
            ('SPAN', (0, 0), (0, 1)),
            ('SPAN', (1, 0), (1, 1)),
            ('SPAN', (2, 0), (1 + num_pupuk, 0)),
            ('GRID', (0, 0), (-1, -1), 0.75, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('LEFTPADDING', (1, 2), (1, -1), 8),
        ]))
        story.append(t_matrix)

    if ctx['has_multiple_kecamatan']:
        story.append(PageBreak())
        story.append(Paragraph("<b>Lampiran 2 : Rekapitulasi Alokasi Seluruh Kecamatan</b>", style_body))
        story.append(Spacer(1, 10))
        story.append(Paragraph(
            "<b>REKAPITULASI TOTAL ALOKASI PUPUK BERSUBSIDI<br/>"
            f"DARI PIHAK PERTAMA KEPADA PIHAK KEDUA ({ctx['kios'].nama_kios})<br/>"
            f"TAHUN {ctx['addendum'].tahun_anggaran}</b>", style_center_bold
        ))
        story.append(Spacer(1, 8))
        story.append(Paragraph(f"Satuan : {ctx['satuan']}", style_satuan))
        story.append(Spacer(1, 4))

        rekap_header = [
            Paragraph("<b>NO</b>", style_center_bold),
            Paragraph("<b>KECAMATAN</b>", style_center_bold),
        ] + [Paragraph(f"<b>{p.kode}</b>", style_center_bold) for p in ctx['jenis_pupuk_list']]
        rekap_rows = [rekap_header]

        for k_idx, k_item in enumerate(ctx['kecamatan_data_list']):
            row_k = [
                Paragraph(str(k_idx + 1), style_tbl_cell),
                Paragraph(k_item['kecamatan'], style_tbl_bulan),
            ] + [Paragraph(str(tot), style_tbl_cell) for tot in k_item['totals']]
            rekap_rows.append(row_k)

        rekap_gt = [
            Paragraph("-", style_tbl_bold),
            Paragraph("<b>TOTAL KESELURUHAN</b>", style_tbl_bold),
        ] + [Paragraph(str(gt), style_tbl_bold) for gt in ctx['grand_totals']]
        rekap_rows.append(rekap_gt)

        t_rekap = Table(rekap_rows, colWidths=col_widths_matrix)
        t_rekap.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 0.75, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('LEFTPADDING', (1, 1), (1, -1), 8),
        ]))
        story.append(t_rekap)

    doc.build(story)
    return output_path


# ==========================================================================
# 3. GENERATOR SURAT PERJANJIAN JUAL BELI (SPJB INDUK - TANPA PASAL PANJANG)
# ==========================================================================
def get_spjb_context(kios_id: int):
    session = SessionLocal()
    kios = session.query(Kios).filter(Kios.id == kios_id).first()
    if not kios:
        session.close()
        raise ValueError(f"Kios ID {kios_id} tidak ditemukan")

    dist = session.query(Distributor).first()
    pi = session.query(PerjanjianInduk).filter(PerjanjianInduk.kios_id == kios.id).first()
    nomor_spjb = kios.nomor_spjb or (pi.nomor_surat if pi else "01/SP/CV.ST/I/2022")
    tanggal_spjb = pi.tanggal_surat if pi else date(2022, 1, 3)
    tanggal_exp = pi.tanggal_berlaku_sampai if pi else date(2022, 12, 31)

    t_spjb = format_tanggal_addendum(tanggal_spjb)
    t_exp = format_tanggal_addendum(tanggal_exp)

    ctx = {
        "kios": kios,
        "dist": dist,
        "nomor_spjb": nomor_spjb,
        "t_spjb": t_spjb,
        "t_exp": t_exp,
        "tahun": tanggal_spjb.year
    }
    session.close()
    return ctx


def generate_spjb_docx(kios_id: int, output_path: str):
    """Menghasilkan file DOCX Surat Perjanjian Jual Beli Pokok (SPJB) tanpa pasal-pasal panjang"""
    ctx = get_spjb_context(kios_id)
    doc = Document()

    for section in doc.sections:
        section.top_margin = Inches(0.8)
        section.bottom_margin = Inches(0.8)
        section.left_margin = Inches(1.0)
        section.right_margin = Inches(1.0)

    def add_p(text="", align=WD_ALIGN_PARAGRAPH.JUSTIFY, bold=False, space_after=4, space_before=0, font_size=11):
        p = doc.add_paragraph()
        p.alignment = align
        p.paragraph_format.space_after = Pt(space_after)
        p.paragraph_format.space_before = Pt(space_before)
        p.paragraph_format.line_spacing = 1.15
        if text:
            run = p.add_run(text)
            run.bold = bold
            run.font.name = "Arial"
            run.font.size = Pt(font_size)
            run.font.color.rgb = RGBColor(0, 0, 0)
        return p

    # Header Dokumen
    add_p("SURAT PERJANJIAN", align=WD_ALIGN_PARAGRAPH.CENTER, bold=True, font_size=11, space_after=1)
    add_p("antara", align=WD_ALIGN_PARAGRAPH.CENTER, bold=False, font_size=11, space_after=1)
    add_p(ctx['dist'].nama_perusahaan, align=WD_ALIGN_PARAGRAPH.CENTER, bold=True, font_size=11, space_after=1)
    add_p("dengan", align=WD_ALIGN_PARAGRAPH.CENTER, bold=False, font_size=11, space_after=1)
    add_p(ctx['kios'].nama_kios, align=WD_ALIGN_PARAGRAPH.CENTER, bold=True, font_size=11, space_after=1)
    add_p("tentang", align=WD_ALIGN_PARAGRAPH.CENTER, bold=False, font_size=11, space_after=1)
    add_p(f"JUAL BELI PUPUK BERSUBSIDI TAHUN {ctx['tahun']}", align=WD_ALIGN_PARAGRAPH.CENTER, bold=True, font_size=11, space_after=6)

    p_line = doc.add_paragraph()
    p_line.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_line.paragraph_format.space_after = Pt(4)
    run_line = p_line.add_run("―" * 46)
    run_line.bold = True

    add_p(f"NOMOR : {ctx['nomor_spjb']}", align=WD_ALIGN_PARAGRAPH.CENTER, bold=True, font_size=11, space_after=12)

    # Pembukaan
    p_intro = add_p()
    p_intro.paragraph_format.line_spacing = 1.2
    p_intro.paragraph_format.space_after = Pt(10)
    p_intro.add_run(
        f"Pada hari ini {ctx['t_spjb']['hari']} tanggal {ctx['t_spjb']['tanggal_terbilang']} "
        f"bulan {ctx['t_spjb']['bulan_nama']} tahun {ctx['t_spjb']['tahun_terbilang']} ( {ctx['t_spjb']['tanggal_format_angka']} ), "
        f"dibuat dan ditandatangani Surat Perjanjian Jual Beli Pupuk Bersubsidi di {ctx['dist'].kabupaten}, "
        "oleh dan antara yang bertanda tangan di bawah ini :"
    )

    # Identitas Para Pihak
    table_pihak = doc.add_table(rows=2, cols=3)
    table_pihak.alignment = WD_TABLE_ALIGNMENT.CENTER
    col_widths = [Inches(2.2), Inches(0.2), Inches(4.2)]
    for row in table_pihak.rows:
        for idx, width in enumerate(col_widths):
            row.cells[idx].width = width

    # Distributor
    c1 = table_pihak.cell(0, 0).paragraphs[0]
    r = c1.add_run(ctx['dist'].nama_pimpinan)
    r.bold = True
    table_pihak.cell(0, 1).paragraphs[0].add_run(":")
    c3 = table_pihak.cell(0, 2).paragraphs[0]
    c3.paragraph_format.line_spacing = 1.15
    c3.add_run(
        f"Selaku {ctx['dist'].jabatan.title()}, dengan demikian bertindak untuk dan atas nama {ctx['dist'].nama_perusahaan}, "
        f"berkedudukan di {ctx['dist'].alamat} {ctx['dist'].provinsi}.\n"
        f"Selanjutnya disebut “PIHAK PERTAMA”."
    )

    # Kios
    c1_k = table_pihak.cell(1, 0).paragraphs[0]
    r = c1_k.add_run(ctx['kios'].nama_pemilik)
    r.bold = True
    table_pihak.cell(1, 1).paragraphs[0].add_run(":")
    c3_k = table_pihak.cell(1, 2).paragraphs[0]
    c3_k.paragraph_format.line_spacing = 1.15
    c3_k.add_run(
        f"Selaku {ctx['kios'].jabatan.title()}, dengan demikian bertindak untuk dan atas nama {ctx['kios'].nama_kios}, "
        f"berkedudukan di {ctx['kios'].alamat}, Kec. {ctx['kios'].kecamatan}.\n"
        f"Selanjutnya disebut “PIHAK KEDUA”."
    )

    # Kesepakatan (Tanpa Pasal-Pasal Panjang)
    add_p(
        "PIHAK PERTAMA dan PIHAK KEDUA ( selanjutnya secara bersama-sama disebut “PARA PIHAK”), "
        "dengan ini sepakat mengikatkan diri dalam Surat Perjanjian Jual Beli Pupuk Bersubsidi dengan ketentuan sebagai berikut :",
        space_before=10, space_after=8
    )

    ketentuan = [
        ("1.", f"PIHAK PERTAMA menunjuk PIHAK KEDUA sebagai Kios Pengecer Resmi untuk menyalurkan pupuk bersubsidi di wilayah kerja Kecamatan {ctx['kios'].kecamatan}."),
        ("2.", f"PIHAK KEDUA setuju untuk membeli dan menyalurkan pupuk bersubsidi dari PIHAK PERTAMA sesuai ketentuan peruntukan kelompok tani / petani terdaftar."),
        ("3.", f"Jadwal dan kuota alokasi awal pupuk bersubsidi adalah sebagaimana tercantum dalam Lampiran Perjanjian ini."),
        ("4.", f"Perjanjian ini berlaku efektif terhitung sejak tanggal ditandatangani sampai dengan tanggal {ctx['t_exp']['tanggal_lengkap']}."),
        ("5.", f"Segala perubahan kuota pupuk yang timbul akibat Surat Keputusan Realokasi dari Dinas Pertanian akan diatur dan dituangkan dalam Addendum Surat Perjanjian yang merupakan satu kesatuan dengan Perjanjian ini.")
    ]

    for no, isi in ketentuan:
        p_k = doc.add_paragraph()
        p_k.paragraph_format.left_indent = Inches(0.3)
        p_k.paragraph_format.first_line_indent = Inches(-0.3)
        p_k.paragraph_format.space_after = Pt(5)
        p_k.paragraph_format.line_spacing = 1.15
        r_no = p_k.add_run(f"{no} ")
        r_no.bold = True
        p_k.add_run(isi)

    add_p(
        f"Demikian Surat Perjanjian Jual Beli ini dibuat dan ditandatangani oleh PARA PIHAK pada hari dan tanggal tersebut diatas "
        "dalam rangkap 2 ( dua ) asli bermaterai cukup dan mempunyai kekuatan hukum yang sama.",
        space_before=12, space_after=24
    )

    # Blok Tanda Tangan
    table_ttd = doc.add_table(rows=3, cols=2)
    table_ttd.alignment = WD_TABLE_ALIGNMENT.CENTER
    for row in table_ttd.rows:
        row.cells[0].width = Inches(3.3)
        row.cells[1].width = Inches(3.3)

    p_kios_hdr = table_ttd.cell(0, 0).paragraphs[0]
    r = p_kios_hdr.add_run(f"PIHAK KEDUA\n{ctx['kios'].nama_kios}")
    r.bold = True

    p_dist_hdr = table_ttd.cell(0, 1).paragraphs[0]
    r = p_dist_hdr.add_run(f"PIHAK PERTAMA\n{ctx['dist'].nama_perusahaan}")
    r.bold = True

    table_ttd.cell(1, 0).paragraphs[0].add_run("\n\n\n\n")
    table_ttd.cell(1, 1).paragraphs[0].add_run("\n\n\n\n")

    p_kios_fn = table_ttd.cell(2, 0).paragraphs[0]
    r = p_kios_fn.add_run(f"{ctx['kios'].nama_pemilik}\n")
    r.bold = True; r.underline = True
    r_j = p_kios_fn.add_run(ctx['kios'].jabatan.upper())
    r_j.bold = True

    p_dist_fn = table_ttd.cell(2, 1).paragraphs[0]
    r = p_dist_fn.add_run(f"{ctx['dist'].nama_pimpinan}\n")
    r.bold = True; r.underline = True
    r_jd = p_dist_fn.add_run(ctx['dist'].jabatan.upper())
    r_jd.bold = True

    doc.save(output_path)
    return output_path


def generate_spjb_pdf(kios_id: int, output_path: str):
    """Menghasilkan file PDF Surat Perjanjian Jual Beli Pokok (SPJB) tanpa pasal-pasal panjang"""
    ctx = get_spjb_context(kios_id)

    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        leftMargin=54,
        rightMargin=54,
        topMargin=45,
        bottomMargin=45
    )

    styles = getSampleStyleSheet()

    style_center_bold = ParagraphStyle("CenterBold", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=11, leading=14, alignment=TA_CENTER)
    style_center = ParagraphStyle("CenterRegular", parent=styles["Normal"], fontName="Helvetica", fontSize=11, leading=14, alignment=TA_CENTER)
    style_body = ParagraphStyle("JustifyBody", parent=styles["Normal"], fontName="Helvetica", fontSize=10.5, leading=14.5, alignment=TA_JUSTIFY)
    style_table_desc = ParagraphStyle("TableDesc", parent=styles["Normal"], fontName="Helvetica", fontSize=10, leading=13.5, alignment=TA_JUSTIFY)
    style_table_name = ParagraphStyle("TableName", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=10, leading=13.5, alignment=TA_LEFT)

    story = []

    # Header
    story.append(Paragraph("SURAT PERJANJIAN", style_center_bold))
    story.append(Paragraph("antara", style_center))
    story.append(Paragraph(ctx['dist'].nama_perusahaan, style_center_bold))
    story.append(Paragraph("dengan", style_center))
    story.append(Paragraph(ctx['kios'].nama_kios, style_center_bold))
    story.append(Paragraph("tentang", style_center))
    story.append(Paragraph(f"JUAL BELI PUPUK BERSUBSIDI TAHUN {ctx['tahun']}", style_center_bold))
    story.append(Spacer(1, 4))
    story.append(HRFlowable(width="100%", thickness=2, color=colors.black, spaceBefore=4, spaceAfter=8))

    story.append(Paragraph(f"NOMOR : {ctx['nomor_spjb']}", style_center_bold))
    story.append(Spacer(1, 10))

    intro_p = (
        f"Pada hari ini {ctx['t_spjb']['hari']} tanggal {ctx['t_spjb']['tanggal_terbilang']} "
        f"bulan {ctx['t_spjb']['bulan_nama']} tahun {ctx['t_spjb']['tahun_terbilang']} ( {ctx['t_spjb']['tanggal_format_angka']} ), "
        f"dibuat dan ditandatangani Surat Perjanjian Jual Beli Pupuk Bersubsidi di {ctx['dist'].kabupaten}, "
        "oleh dan antara yang bertanda tangan di bawah ini :"
    )
    story.append(Paragraph(intro_p, style_body))
    story.append(Spacer(1, 8))

    p1_desc = (
        f"Selaku {ctx['dist'].jabatan.title()}, dengan demikian bertindak untuk dan atas nama <b>{ctx['dist'].nama_perusahaan}</b>, "
        f"suatu perusahaan yang didirikan dan dijalankan berdasarkan hukum Negara Republik Indonesia, berkedudukan di {ctx['dist'].alamat} {ctx['dist'].provinsi}.<br/>"
        f"Selanjutnya disebut <b>“PIHAK PERTAMA”</b>."
    )
    p2_desc = (
        f"Selaku {ctx['kios'].jabatan.title()}, dengan demikian bertindak untuk dan atas nama <b>{ctx['kios'].nama_kios}</b>, "
        f"berkedudukan di {ctx['kios'].alamat}, Kec. {ctx['kios'].kecamatan}.<br/>"
        f"Selanjutnya disebut <b>“PIHAK KEDUA”</b>."
    )

    table_data_pihak = [
        [
            Paragraph(ctx['dist'].nama_pimpinan, style_table_name),
            Paragraph(":", style_table_name),
            Paragraph(p1_desc, style_table_desc)
        ],
        [
            Paragraph(ctx['kios'].nama_pemilik, style_table_name),
            Paragraph(":", style_table_name),
            Paragraph(p2_desc, style_table_desc)
        ]
    ]

    t_pihak = Table(table_data_pihak, colWidths=[140, 15, 335])
    t_pihak.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('LEFTPADDING', (0,0), (-1,-1), 0),
        ('RIGHTPADDING', (0,0), (-1,-1), 0),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('TOPPADDING', (0,0), (-1,-1), 2),
    ]))
    story.append(t_pihak)
    story.append(Spacer(1, 8))

    story.append(Paragraph(
        "<b>PIHAK PERTAMA</b> dan <b>PIHAK KEDUA</b> ( selanjutnya secara bersama-sama disebut <b>“PARA PIHAK”</b>), "
        "dengan ini sepakat mengikatkan diri dalam Surat Perjanjian Jual Beli Pupuk Bersubsidi dengan ketentuan sebagai berikut :", style_body
    ))
    story.append(Spacer(1, 6))

    ketentuan = [
        ("1.", f"PIHAK PERTAMA menunjuk PIHAK KEDUA sebagai Kios Pengecer Resmi untuk menyalurkan pupuk bersubsidi di wilayah kerja Kecamatan {ctx['kios'].kecamatan}."),
        ("2.", f"PIHAK KEDUA setuju untuk membeli dan menyalurkan pupuk bersubsidi dari PIHAK PERTAMA sesuai ketentuan peruntukan petani dan kelompok tani terdaftar."),
        ("3.", f"Jadwal dan kuota alokasi pupuk bersubsidi adalah sebagaimana tercantum dalam Lampiran Perjanjian ini."),
        ("4.", f"Perjanjian ini berlaku efektif terhitung sejak tanggal ditandatangani sampai dengan tanggal {ctx['t_exp']['tanggal_lengkap']}."),
        ("5.", f"Segala perubahan kuota alokasi pupuk yang timbul akibat Keputusan Realokasi dari Dinas Pertanian akan dituangkan dalam Addendum Surat Perjanjian yang merupakan satu kesatuan dengan Perjanjian ini.")
    ]

    for no, isi in ketentuan:
        t_k = Table([[Paragraph(f"<b>{no}</b>", style_table_name), Paragraph(isi, style_body)]], colWidths=[20, 470])
        t_k.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('LEFTPADDING', (0,0), (-1,-1), 0),
            ('RIGHTPADDING', (0,0), (-1,-1), 0),
            ('BOTTOMPADDING', (0,0), (-1,-1), 5),
            ('TOPPADDING', (0,0), (-1,-1), 0),
        ]))
        story.append(t_k)

    story.append(Spacer(1, 8))
    story.append(Paragraph(
        "Demikian Surat Perjanjian Jual Beli ini dibuat dan ditandatangani oleh <b>PARA PIHAK</b> pada hari dan tanggal tersebut diatas "
        "dalam rangkap 2 ( dua ) asli bermaterai cukup dan mempunyai kekuatan hukum yang sama.", style_body
    ))
    story.append(Spacer(1, 28))

    ttd_kios = [
        Paragraph(f"<b>PIHAK KEDUA<br/>{ctx['kios'].nama_kios}</b>", style_center_bold),
        Spacer(1, 60),
        Paragraph(f"<u><b>{ctx['kios'].nama_pemilik}</b></u>", style_center_bold),
        Paragraph(f"<b>{ctx['kios'].jabatan.upper()}</b>", style_center_bold)
    ]
    ttd_dist = [
        Paragraph(f"<b>PIHAK PERTAMA<br/>{ctx['dist'].nama_perusahaan}</b>", style_center_bold),
        Spacer(1, 60),
        Paragraph(f"<u><b>{ctx['dist'].nama_pimpinan}</b></u>", style_center_bold),
        Paragraph(f"<b>{ctx['dist'].jabatan.upper()}</b>", style_center_bold)
    ]

    t_ttd = Table([[ttd_kios, ttd_dist]], colWidths=[245, 245])
    t_ttd.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('LEFTPADDING', (0,0), (-1,-1), 0),
        ('RIGHTPADDING', (0,0), (-1,-1), 0),
    ]))
    story.append(t_ttd)

    doc.build(story)
    return output_path
