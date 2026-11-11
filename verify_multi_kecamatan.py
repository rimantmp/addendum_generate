from app import app
from db import SessionLocal
from models import DetailAlokasi, Addendum
from generator import generate_docx, generate_pdf

client = app.test_client()

def test_multi_kecamatan():
    print("1. Menambahkan Kecamatan MASANDA ke Addendum 1...")
    res = client.post("/addendum/1/add-kecamatan", data={
        "nama_kecamatan": "MASANDA"
    }, follow_redirects=True)
    assert res.status_code == 200
    assert b"KECAMATAN MASANDA" in res.data
    assert b"KECAMATAN BITTUANG" in res.data
    print("Kecamatan MASANDA berhasil ditambahkan!")

    print("2. Mengisi kuota untuk Kecamatan MASANDA (misal 5 ton NPK di Januari)...")
    res = client.post("/addendum/1/update-allocation", data={
        "kecamatan_list": ["BITTUANG", "MASANDA"],
        "kuota_MASANDA_1_1": "5", # Jan NPK = 5 ton
        "kuota_MASANDA_2_1": "10", # Feb NPK = 10 ton
        "kuota_BITTUANG_1_1": "10" # Jan NPK = 10 ton
    }, follow_redirects=True)
    assert res.status_code == 200
    assert b"berhasil disimpan" in res.data
    print("Update kuota multi-kecamatan berhasil!")

    print("3. Menguji Generate PDF untuk Dokumen Multi-Kecamatan...")
    pdf_path = "hasil_multi_kecamatan.pdf"
    generate_pdf(1, pdf_path)
    print(f"PDF Multi-Kecamatan berhasil digenerate: {pdf_path}")

    print("4. Menguji Generate DOCX untuk Dokumen Multi-Kecamatan...")
    docx_path = "hasil_multi_kecamatan.docx"
    generate_docx(1, docx_path)
    print(f"DOCX Multi-Kecamatan berhasil digenerate: {docx_path}")

    print("5. Menguji unduh via endpoint /addendum/1/pdf ...")
    res = client.get("/addendum/1/pdf")
    assert res.status_code == 200
    assert res.headers["Content-Type"] == "application/pdf"
    assert len(res.data) > 2000
    print("Download PDF endpoint OK!")

    print("SEMUA PENGUJIAN FITUR MULTI-KECAMATAN BERHASIL 100%!")

if __name__ == "__main__":
    test_multi_kecamatan()

