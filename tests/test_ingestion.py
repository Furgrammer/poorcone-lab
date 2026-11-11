import sqlite3
from pathlib import Path

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
