import sqlite3
from pathlib import Path

from io import BytesIO

from docx import Document
from pypdf import PdfWriter

import pytest

import ingestion


@pytest.fixture
def isolated_environment(tmp_path, monkeypatch):
    """Menyiapkan database dan storage terpisah untuk pengujian."""

    test_db_path = tmp_path / "test.db"
    test_storage_path = tmp_path / "data" / "documents"

    monkeypatch.setattr(
        ingestion.database,
        "DB_PATH",
        test_db_path,
    )

    monkeypatch.setattr(
        ingestion,
        "PROJECT_ROOT",
        tmp_path,
    )

    monkeypatch.setattr(
        ingestion,
        "DOCUMENT_STORAGE_DIR",
        test_storage_path,
    )

    ingestion.database.initialize_database()

    return tmp_path


def test_ingest_txt_success(isolated_environment):
    """File TXT berhasil diekstrak dan disimpan."""

    content = b"Belajar Python dan Machine Learning."

    result = ingestion.ingest_document(
        "python_basics.txt",
        content,
    )

    assert result.title == "python_basics"
    assert result.file_type == "txt"
    assert result.is_duplicate is False

    stored_file = isolated_environment / result_file_path(result)

    assert stored_file.exists()
    assert stored_file.read_bytes() == content

    document = ingestion.database.get_document_by_hash(result.content_hash)

    assert document is not None
    assert document[1] == "python_basics"
    assert document[7] == "Belajar Python dan Machine Learning."
    assert document[8] == "completed"


def result_file_path(result):
    document = ingestion.database.get_all_documents()[0]
    return document[4]


def test_ingest_markdown_success(isolated_environment):
    """File Markdown berhasil diekstrak."""

    content = b"# Python Basics\n\nBelajar Python."

    result = ingestion.ingest_document(
        "python_basics.md",
        content,
    )

    document = ingestion.database.get_document_by_hash(result.content_hash)

    assert document[7] == "# Python Basics\n\nBelajar Python."
    assert document[3] == "md"


def test_duplicate_content_is_not_stored_twice(isolated_environment):
    """Konten identik tidak menghasilkan dokumen duplikat."""

    content = b"Konten yang sama."

    first = ingestion.ingest_document(
        "first.txt",
        content,
    )

    second = ingestion.ingest_document(
        "second.txt",
        content,
    )

    assert first.is_duplicate is False
    assert second.is_duplicate is True
    assert second.document_id == first.document_id

    assert len(ingestion.database.get_all_documents()) == 1


def test_unsupported_file_extension(isolated_environment):
    """Ekstensi yang tidak didukung ditolak."""

    with pytest.raises(ValueError, match="Format tidak didukung"):
        ingestion.ingest_document(
            "script.py",
            b"print('Hello')",
        )


def test_empty_file_is_rejected(isolated_environment):
    """File kosong ditolak."""

    with pytest.raises(ValueError, match="File kosong"):
        ingestion.ingest_document(
            "empty.txt",
            b"",
        )


def test_invalid_utf8_is_rejected(isolated_environment):
    """File dengan encoding yang tidak valid ditolak."""

    with pytest.raises(ValueError, match="UTF-8"):
        ingestion.ingest_document(
            "invalid.txt",
            b"\xff\xfe\xfa",
        )


def test_filename_path_is_sanitized(isolated_environment):
    """Path dari nama file tidak digunakan sebagai storage path."""

    result = ingestion.ingest_document(
        "../../secret.txt",
        b"Safe content.",
    )

    document = ingestion.database.get_document_by_hash(result.content_hash)

    assert document[2] == "secret.txt"
    assert document[4].startswith("data/documents/")
    assert ".." not in document[4]


def test_failed_database_insert_removes_stored_file(
    isolated_environment,
    monkeypatch,
):
    """File fisik dibersihkan jika penyimpanan database gagal."""

    def simulate_database_error(**kwargs):
        raise sqlite3.OperationalError("Simulated error")

    monkeypatch.setattr(
        ingestion.database,
        "add_document",
        simulate_database_error,
    )

    with pytest.raises(sqlite3.OperationalError):
        ingestion.ingest_document(
            "python.txt",
            b"Belajar Python.",
        )

    stored_files = list(ingestion.DOCUMENT_STORAGE_DIR.glob("*"))

    assert stored_files == []


def build_text_pdf(text):
    """Membuat PDF sederhana berisi teks untuk pengujian."""

    escaped_text = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")

    content_stream = (f"BT /F1 12 Tf 40 200 Td ({escaped_text}) Tj ET").encode("ascii")

    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        (
            b"<< /Type /Page /Parent 2 0 R "
            b"/MediaBox [0 0 300 300] "
            b"/Resources << /Font << /F1 4 0 R >> >> "
            b"/Contents 5 0 R >>"
        ),
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        (
            b"<< /Length "
            + str(len(content_stream)).encode()
            + b" >>\nstream\n"
            + content_stream
            + b"\nendstream"
        ),
    ]

    output = bytearray(b"%PDF-1.4\n")
    offsets = [0]

    for index, obj in enumerate(objects, start=1):
        offsets.append(len(output))

        output.extend(f"{index} 0 obj\n".encode())
        output.extend(obj)
        output.extend(b"\nendobj\n")

    xref_offset = len(output)

    output.extend(f"xref\n0 {len(objects) + 1}\n".encode())

    output.extend(b"0000000000 65535 f \n")

    for offset in offsets[1:]:
        output.extend(f"{offset:010d} 00000 n \n".encode())

    output.extend(
        (
            f"trailer\n<< /Size {len(objects) + 1} "
            f"/Root 1 0 R >>\n"
            f"startxref\n{xref_offset}\n%%EOF"
        ).encode()
    )

    return bytes(output)


def build_docx():
    """Membuat DOCX dengan paragraf dan tabel."""

    document = Document()

    document.add_paragraph("Opening paragraph.")

    table = document.add_table(
        rows=2,
        cols=2,
    )

    table.cell(0, 0).text = "Topic"
    table.cell(0, 1).text = "Description"

    table.cell(1, 0).text = "Python"
    table.cell(1, 1).text = "Programming language"

    document.add_paragraph("Closing paragraph.")

    output = BytesIO()
    document.save(output)

    return output.getvalue()


def test_pdf_extraction_success(isolated_environment):
    """PDF berhasil diekstrak dan penanda halaman tersedia."""

    content = build_text_pdf("PDF extraction works.")

    result = ingestion.ingest_document(
        "python_guide.pdf",
        content,
    )

    document = ingestion.database.get_document_by_hash(result.content_hash)

    assert result.file_type == "pdf"
    assert result.is_duplicate is False
    assert "[Page 1]" in document[7]
    assert "PDF extraction works." in document[7]


def test_docx_extraction_includes_paragraphs_and_tables(
    isolated_environment,
):
    """DOCX berhasil diekstrak sesuai urutan paragraf dan tabel."""

    content = build_docx()

    result = ingestion.ingest_document(
        "python_guide.docx",
        content,
    )

    document = ingestion.database.get_document_by_hash(result.content_hash)

    extracted_text = document[7]

    assert result.file_type == "docx"

    assert "Opening paragraph." in extracted_text
    assert "Topic | Description" in extracted_text
    assert "Python | Programming language" in extracted_text
    assert "Closing paragraph." in extracted_text

    assert (
        extracted_text.index("Opening paragraph.")
        < extracted_text.index("Topic")
        < extracted_text.index("Closing paragraph.")
    )


def test_pdf_without_extractable_text_is_rejected(
    isolated_environment,
):
    """PDF tanpa teks yang dapat diekstrak ditolak."""

    content = build_text_pdf("")

    with pytest.raises(ValueError, match="OCR"):
        ingestion.ingest_document(
            "scanned_document.pdf",
            content,
        )


def test_encrypted_pdf_is_rejected(isolated_environment):
    """PDF yang dilindungi password ditolak."""

    writer = PdfWriter()

    writer.add_blank_page(
        width=72,
        height=72,
    )

    writer.encrypt("test-password")

    output = BytesIO()
    writer.write(output)

    with pytest.raises(ValueError, match="password"):
        ingestion.ingest_document(
            "encrypted.pdf",
            output.getvalue(),
        )


def test_invalid_pdf_is_rejected(isolated_environment):
    """File PDF yang rusak atau tidak valid ditolak."""

    with pytest.raises(ValueError, match="PDF"):
        ingestion.ingest_document(
            "invalid.pdf",
            b"Not a valid PDF file.",
        )


def test_invalid_docx_is_rejected(isolated_environment):
    """File DOCX yang rusak atau tidak valid ditolak."""

    with pytest.raises(ValueError, match="DOCX"):
        ingestion.ingest_document(
            "invalid.docx",
            b"Not a valid DOCX file.",
        )
