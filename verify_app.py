from app import app

client = app.test_client()

def test_endpoints():
    print("Testing GET / ...")
    res = client.get("/")
    assert res.status_code == 200
    assert b"Sistem Generator Addendum" in res.data
    assert b"UD UNGGUL TANI" in res.data
    print("Dashboard OK!")

    print("Testing GET /addendum/1 ...")
    res = client.get("/addendum/1")
    assert res.status_code == 200
    assert b"01/SP/CV/ST/XII/2022" in res.data
    print("Detail Addendum OK!")

    print("Testing GET /addendum/1/pdf ...")
    res = client.get("/addendum/1/pdf")
    assert res.status_code == 200
    assert res.headers["Content-Type"] == "application/pdf"
    assert len(res.data) > 1000
    print(f"Generate & Download PDF OK! (Ukuran: {len(res.data)} bytes)")

    print("Testing GET /addendum/1/docx ...")
    res = client.get("/addendum/1/docx")
    assert res.status_code == 200
    assert "wordprocessingml" in res.headers["Content-Type"]
    assert len(res.data) > 1000
    print(f"Generate & Download DOCX OK! (Ukuran: {len(res.data)} bytes)")

    print("Testing GET /batch/zip ...")
    res = client.get("/batch/zip")
    assert res.status_code == 200
    assert res.headers["Content-Type"] == "application/zip"
    assert len(res.data) > 1000
    print(f"Batch Download ZIP OK! (Ukuran: {len(res.data)} bytes)")

    print("Testing GET /kios ...")
    res = client.get("/kios")
    assert res.status_code == 200
    assert b"NOMOR SPJB" in res.data
    assert b"SPJB (PDF)" in res.data
    print("Master Kios with SPJB OK!")

    print("Testing GET /kios/2/spjb/pdf ...")
    res = client.get("/kios/2/spjb/pdf")
    assert res.status_code == 200
    assert res.headers["Content-Type"] == "application/pdf"
    assert len(res.data) > 1000
    print(f"Generate & Download SPJB PDF OK! (Ukuran: {len(res.data)} bytes)")

    print("Testing GET /kios/2/spjb/docx ...")
    res = client.get("/kios/2/spjb/docx")
    assert res.status_code == 200
    assert "wordprocessingml" in res.headers["Content-Type"]
    assert len(res.data) > 1000
    print(f"Generate & Download SPJB DOCX OK! (Ukuran: {len(res.data)} bytes)")

    print("Testing GET /backup ...")
    res = client.get("/backup")
    assert res.status_code == 200
    assert b"Cadangan & Pemulihan Database" in res.data
    print("Halaman Backup View OK!")

    print("Testing GET /backup/download ...")
    res = client.get("/backup/download")
    assert res.status_code == 200
    assert len(res.data) > 10000
    print(f"Download Backup (.db) OK! (Ukuran: {len(res.data)} bytes)")

    print("Testing GET /backup/sql ...")
    res = client.get("/backup/sql")
    assert res.status_code == 200
    assert b"CREATE TABLE" in res.data
    print(f"Download SQL Dump (.sql) OK! (Ukuran: {len(res.data)} bytes)")

    print("SEMUA PENGUJIAN ENDPOINT BERHASIL 100%!")

if __name__ == "__main__":
    test_endpoints()

