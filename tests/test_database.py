import pytest
import sqlite3
from contextlib import closing

import database


@pytest.fixture
def db(tmp_path, monkeypatch):
    """
    Membuat database sementara untuk setiap test.
    Database utama poorcone_lab.db tidak akan disentuh.
    """
    test_db_path = tmp_path / "test_poorcone_lab.db"

    monkeypatch.setattr(
        database,
        "DB_PATH",
        test_db_path,
    )

    database.initialize_database()

    return database


def test_add_and_get_note(db):
    """Catatan baru berhasil disimpan dan dibaca."""

    db.add_note(
        "Python Basics",
        "Python",
        "Belajar dasar Python.",
    )

    notes = db.get_all_notes()

    assert len(notes) == 1
    assert notes[0][1:] == (
        "Python Basics",
        "Python",
        "Belajar dasar Python.",
    )


def test_update_existing_note(db):
    """Catatan yang ada berhasil diperbarui."""

    db.add_note(
        "Python Basics",
        "Python",
        "Belajar dasar Python.",
    )

    note_id = db.get_all_notes()[0][0]

    updated = db.update_note(
        note_id,
        "Advanced Python",
        "Programming",
        "Belajar Python lebih mendalam.",
    )

    assert updated is True

    notes = db.get_all_notes()

    assert len(notes) == 1
    assert notes[0] == (
        note_id,
        "Advanced Python",
        "Programming",
        "Belajar Python lebih mendalam.",
    )


def test_update_note_does_not_change_other_notes(db):
    """Update satu catatan tidak mengubah catatan lainnya."""

    db.add_note("Note A", "Python", "Konten A.")
    db.add_note("Note B", "AI", "Konten B.")

    notes_before = db.get_all_notes()

    note_id = notes_before[0][0]

    db.update_note(
        note_id,
        "Updated Note B",
        "Machine Learning",
        "Konten baru B.",
    )

    notes_after = db.get_all_notes()

    assert notes_after[0] == (
        note_id,
        "Updated Note B",
        "Machine Learning",
        "Konten baru B.",
    )

    assert notes_after[1] == notes_before[1]


def test_update_nonexistent_note(db):
    """Update ID yang tidak tersedia mengembalikan False."""

    db.add_note("Python Basics", "Python", "Konten.")

    notes_before = db.get_all_notes()

    updated = db.update_note(
        99999,
        "Judul Baru",
        "AI",
        "Konten baru.",
    )

    assert updated is False
    assert db.get_all_notes() == notes_before


def test_delete_note(db):
    """Catatan berhasil dihapus."""

    db.add_note("Python Basics", "Python", "Konten.")

    note_id = db.get_all_notes()[0][0]

    db.delete_note(note_id)

    assert db.get_all_notes() == []


def test_migration_creates_documents_table(db):
    """Migration membuat tabel documents dan mengatur versi skema."""

    with closing(db.get_connection()) as connection:
        version = connection.execute("PRAGMA user_version").fetchone()[0]

        documents_table = connection.execute("""
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
            AND name = 'documents'
        """).fetchone()

    assert version == 1
    assert documents_table is not None


def test_migration_preserves_existing_notes(tmp_path, monkeypatch):
    """Migration tidak menghapus catatan dari database lama."""

    test_db_path = tmp_path / "legacy.db"

    monkeypatch.setattr(
        database,
        "DB_PATH",
        test_db_path,
    )

    # Simulasikan database lama sebelum migration.
    with sqlite3.connect(test_db_path) as connection:
        connection.execute("""
            CREATE TABLE notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                category TEXT NOT NULL,
                content TEXT NOT NULL
            )
        """)

        connection.executemany(
            """
            INSERT INTO notes (title, category, content)
            VALUES (?, ?, ?)
            """,
            [
                ("Python Basics", "Python", "Konten Python."),
                ("Machine Learning", "AI", "Konten ML."),
            ],
        )

        connection.execute("PRAGMA user_version = 0")

    # Jalankan migration.
    database.initialize_database()

    notes = database.get_all_notes()

    assert len(notes) == 2

    assert notes[0][1:] == (
        "Machine Learning",
        "AI",
        "Konten ML.",
    )

    assert notes[1][1:] == (
        "Python Basics",
        "Python",
        "Konten Python.",
    )


def test_initialize_database_is_idempotent(db):
    """Migration tidak mengulang perubahan yang sudah diterapkan."""

    db.add_note(
        "Python Basics",
        "Python",
        "Konten Python.",
    )

    db.initialize_database()
    db.initialize_database()

    notes = db.get_all_notes()

    assert len(notes) == 1


def test_initialize_database_rejects_newer_schema(
    tmp_path,
    monkeypatch,
):
    """Database dengan versi lebih baru harus ditolak."""

    test_db_path = tmp_path / "future.db"

    monkeypatch.setattr(
        database,
        "DB_PATH",
        test_db_path,
    )

    with sqlite3.connect(test_db_path) as connection:
        connection.execute("PRAGMA user_version = 99")

    with pytest.raises(RuntimeError, match="newer than supported"):
        database.initialize_database()
