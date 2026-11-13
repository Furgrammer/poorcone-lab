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

    assert version == 2
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


def test_migration_from_v1_preserves_notes_and_documents(tmp_path, monkeypatch):
    """Migration v2 mempertahankan seluruh record v1 tanpa perubahan."""

    test_db_path = tmp_path / "version_1.db"
    monkeypatch.setattr(database, "DB_PATH", test_db_path)

    with sqlite3.connect(test_db_path) as connection:
        database._migrate_to_v1(connection)
        connection.execute(
            """
            INSERT INTO notes (title, category, content)
            VALUES (?, ?, ?)
            """,
            ("Existing note", "Python", "Existing note content."),
        )
        connection.execute(
            """
            INSERT INTO documents (
                title, original_filename, file_type, storage_path,
                file_size_bytes, content_hash, extracted_text,
                processing_status, processing_error, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "Existing document",
                "source.txt",
                "txt",
                "data/documents/source.txt",
                12,
                "existing-hash",
                "Existing extracted text.",
                "completed",
                None,
                "2025-01-02 03:04:05",
                "2025-01-03 04:05:06",
            ),
        )
        connection.execute("PRAGMA user_version = 1")

    database.initialize_database()

    with closing(database.get_connection()) as connection:
        version = connection.execute("PRAGMA user_version").fetchone()[0]
        note = connection.execute("SELECT * FROM notes").fetchone()
        document = connection.execute("SELECT * FROM documents").fetchone()

    assert version == 2
    assert note == (1, "Existing note", "Python", "Existing note content.")
    assert document == (
        1,
        "Existing document",
        "source.txt",
        "txt",
        "data/documents/source.txt",
        12,
        "existing-hash",
        "Existing extracted text.",
        "completed",
        None,
        "2025-01-02 03:04:05",
        "2025-01-03 04:05:06",
    )


def test_migration_v2_is_idempotent(db):
    db.add_note("Preserved", "Python", "Content.")
    tag_id = db.create_tag("Python")
    note_id = db.get_all_notes()[0][0]
    db.add_note_tag(note_id, tag_id)

    db.initialize_database()
    db.initialize_database()

    assert db.get_all_notes()[0][1] == "Preserved"
    assert [tag[0] for tag in db.get_note_tags(note_id)] == [tag_id]


def test_failed_migration_rolls_back_schema_changes(tmp_path, monkeypatch):
    test_db_path = tmp_path / "migration_rollback.db"
    monkeypatch.setattr(database, "DB_PATH", test_db_path)

    with sqlite3.connect(test_db_path) as connection:
        database._migrate_to_v1(connection)
        connection.execute("PRAGMA user_version = 1")

    def failing_migration(connection):
        connection.execute("CREATE TABLE migration_probe (id INTEGER)")
        raise RuntimeError("Simulated migration failure")

    monkeypatch.setitem(database.MIGRATIONS, 2, failing_migration)

    with pytest.raises(RuntimeError, match="Simulated migration failure"):
        database.initialize_database()

    with closing(database.get_connection()) as connection:
        version = connection.execute("PRAGMA user_version").fetchone()[0]
        probe = connection.execute(
            """
            SELECT name FROM sqlite_master
            WHERE type = 'table' AND name = 'migration_probe'
            """
        ).fetchone()

    assert version == 1
    assert probe is None


def test_normalize_tag_name_uses_nfc_and_casefold():
    composed = "  Caf\u00e9  "
    decomposed = "CAFE\u0301"

    assert database.normalize_tag_name(composed) == "caf\u00e9"
    assert database.normalize_tag_name(decomposed) == "caf\u00e9"
    assert database.normalize_tag_name("Stra\u00dfe") == "strasse"


@pytest.mark.parametrize(
    "invalid_name",
    [
        "",
        "   ",
        "\t\n",
        None,
        42,
        "x" * 51,
    ],
)
def test_normalize_tag_name_rejects_invalid_names(invalid_name):
    with pytest.raises(ValueError):
        database.normalize_tag_name(invalid_name)


def test_tag_crud_and_duplicate_creation(db):
    tag_id = db.create_tag("  Machine Learning  ")

    assert db.create_tag("machine learning") == tag_id
    assert db.get_tag(tag_id)[1:3] == ("Machine Learning", "machine learning")
    assert [tag[0] for tag in db.get_all_tags()] == [tag_id]
    assert db.get_tag(99999) is None

    unicode_tag_id = db.create_tag("Caf\u00e9")
    assert db.create_tag("CAFE\u0301") == unicode_tag_id
    assert db.get_tag(unicode_tag_id)[1] == "Caf\u00e9"
    assert db.create_tag("x" * 50) != unicode_tag_id


def test_rename_tag_preserves_display_case_and_rejects_conflicts(db):
    first_tag_id = db.create_tag("Python")
    second_tag_id = db.create_tag("Machine Learning")

    assert db.rename_tag(first_tag_id, "  PYTHON  ") is True
    assert db.get_tag(first_tag_id)[1:3] == ("PYTHON", "python")

    with pytest.raises(ValueError, match="sudah digunakan"):
        db.rename_tag(first_tag_id, "machine learning")

    assert db.rename_tag(99999, "Unknown") is False
    assert db.get_tag(second_tag_id)[1] == "Machine Learning"


def test_delete_tag_cascades_note_and_document_relationships(db):
    db.add_note("Note", "Python", "Content.")
    note_id = db.get_all_notes()[0][0]
    document_id = db.add_document(
        "Document",
        "document.txt",
        "txt",
        "data/documents/document.txt",
        7,
        "document-hash",
        "Extracted text.",
    )
    tag_id = db.create_tag("Shared")

    db.add_note_tag(note_id, tag_id)
    db.add_document_tag(document_id, tag_id)

    assert db.delete_tag(tag_id) is True
    assert db.get_note_tags(note_id) == []
    assert db.get_document_tags(document_id) == []
    assert db.delete_tag(tag_id) is False


def test_deleting_entities_cascades_association_rows(db):
    db.add_note("Note", "Python", "Content.")
    note_id = db.get_all_notes()[0][0]
    document_id = db.add_document(
        "Document",
        "document.txt",
        "txt",
        "data/documents/document.txt",
        7,
        "document-hash",
        "Extracted text.",
    )
    tag_id = db.create_tag("Shared")
    db.add_note_tag(note_id, tag_id)
    db.add_document_tag(document_id, tag_id)

    db.delete_note(note_id)

    with closing(db.get_connection()) as connection, connection:
        connection.execute("DELETE FROM documents WHERE id = ?", (document_id,))

    with closing(db.get_connection()) as connection:
        note_relationships = connection.execute(
            "SELECT COUNT(*) FROM note_tags WHERE note_id = ?",
            (note_id,),
        ).fetchone()[0]
        document_relationships = connection.execute(
            "SELECT COUNT(*) FROM document_tags WHERE document_id = ?",
            (document_id,),
        ).fetchone()[0]

    assert note_relationships == 0
    assert document_relationships == 0


def test_note_tag_relationships_are_idempotent_and_removable(db):
    db.add_note("Note", "Python", "Content.")
    note_id = db.get_all_notes()[0][0]
    tag_id = db.create_tag("Python")

    assert db.add_note_tag(note_id, tag_id) is True
    assert db.add_note_tag(note_id, tag_id) is False
    assert [tag[0] for tag in db.get_note_tags(note_id)] == [tag_id]
    assert db.remove_note_tag(note_id, tag_id) is True
    assert db.remove_note_tag(note_id, tag_id) is False
    assert db.get_note_tags(note_id) == []


def test_document_tag_relationships_are_idempotent_and_removable(db):
    document_id = db.add_document(
        "Document",
        "document.txt",
        "txt",
        "data/documents/document.txt",
        7,
        "document-hash",
        "Extracted text.",
    )
    tag_id = db.create_tag("Reference")

    assert db.add_document_tag(document_id, tag_id) is True
    assert db.add_document_tag(document_id, tag_id) is False
    assert [tag[0] for tag in db.get_document_tags(document_id)] == [tag_id]
    assert db.remove_document_tag(document_id, tag_id) is True
    assert db.remove_document_tag(document_id, tag_id) is False
    assert db.get_document_tags(document_id) == []


@pytest.mark.parametrize(
    ("operation", "missing_id"),
    [
        ("add_note", 99999),
        ("remove_note", 99999),
        ("get_note", 99999),
        ("add_document", 99999),
        ("remove_document", 99999),
        ("get_document", 99999),
    ],
)
def test_tag_relationships_report_missing_entities_and_tags(
    db,
    operation,
    missing_id,
):
    tag_id = db.create_tag("Valid")
    db.add_note("Note", "Python", "Content.")
    note_id = db.get_all_notes()[0][0]
    document_id = db.add_document(
        "Document",
        "document.txt",
        "txt",
        "data/documents/document.txt",
        7,
        "document-hash",
        "Extracted text.",
    )

    if operation == "add_note":
        with pytest.raises(ValueError, match="Note dengan ID"):
            db.add_note_tag(missing_id, tag_id)
    elif operation == "remove_note":
        with pytest.raises(ValueError, match="Note dengan ID"):
            db.remove_note_tag(missing_id, tag_id)
    elif operation == "get_note":
        with pytest.raises(ValueError, match="Note dengan ID"):
            db.get_note_tags(missing_id)
    elif operation == "add_document":
        with pytest.raises(ValueError, match="Document dengan ID"):
            db.add_document_tag(missing_id, tag_id)
    elif operation == "remove_document":
        with pytest.raises(ValueError, match="Document dengan ID"):
            db.remove_document_tag(missing_id, tag_id)
    else:
        with pytest.raises(ValueError, match="Document dengan ID"):
            db.get_document_tags(missing_id)

    with pytest.raises(ValueError, match="Tag dengan ID"):
        db.add_note_tag(note_id, 99999)
    with pytest.raises(ValueError, match="Tag dengan ID"):
        db.add_document_tag(document_id, 99999)
    with pytest.raises(ValueError, match="Tag dengan ID"):
        db.remove_note_tag(note_id, 99999)
    with pytest.raises(ValueError, match="Tag dengan ID"):
        db.remove_document_tag(document_id, 99999)


def test_note_and_document_tag_relationships_are_isolated(db):
    db.add_note("Note", "Python", "Content.")
    note_id = db.get_all_notes()[0][0]
    document_id = db.add_document(
        "Document",
        "document.txt",
        "txt",
        "data/documents/document.txt",
        7,
        "document-hash",
        "Extracted text.",
    )
    tag_id = db.create_tag("Shared")

    db.add_note_tag(note_id, tag_id)

    assert [tag[0] for tag in db.get_note_tags(note_id)] == [tag_id]
    assert db.get_document_tags(document_id) == []

    db.add_document_tag(document_id, tag_id)
    assert [tag[0] for tag in db.get_document_tags(document_id)] == [tag_id]


def test_foreign_keys_are_enabled_and_enforced_for_every_connection(db):
    tag_id = db.create_tag("Valid")

    with closing(db.get_connection()) as connection:
        assert connection.execute("PRAGMA foreign_keys").fetchone()[0] == 1

        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                "INSERT INTO note_tags (note_id, tag_id) VALUES (?, ?)",
                (99999, tag_id),
            )

        connection.rollback()


def test_get_document_by_id_and_update_title_preserve_other_fields(db):
    document_id = db.add_document(
        "Original title",
        "original.txt",
        "txt",
        "data/documents/original.txt",
        15,
        "original-hash",
        "Original extracted text.",
    )

    with closing(db.get_connection()) as connection, connection:
        connection.execute(
            "UPDATE documents SET updated_at = ? WHERE id = ?",
            ("2000-01-01 00:00:00", document_id),
        )

    before = db.get_document_by_id(document_id)
    assert before == db.get_all_documents()[0]

    assert db.update_document_title(document_id, "  New title  ") is True

    after = db.get_document_by_id(document_id)
    assert after[1] == "New title"
    assert after[2:11] == before[2:11]
    assert after[11] != "2000-01-01 00:00:00"


@pytest.mark.parametrize("title", ["", "   ", "\t\n", None, 42])
def test_update_document_title_rejects_invalid_titles(db, title):
    document_id = db.add_document(
        "Original title",
        "original.txt",
        "txt",
        "data/documents/original.txt",
        15,
        "original-hash",
        "Original extracted text.",
    )
    before = db.get_document_by_id(document_id)

    with pytest.raises(ValueError, match="Judul dokumen"):
        db.update_document_title(document_id, title)

    assert db.get_document_by_id(document_id) == before


def test_document_database_operations_report_missing_ids(db):
    assert db.get_document_by_id(99999) is None
    assert db.update_document_title(99999, "New title") is False
    assert db.delete_document(99999) is False


def test_delete_document_cascades_document_tags_only(db):
    db.add_note("Preserved note", "Python", "Note content.")
    note_id = db.get_all_notes()[0][0]
    document_id = db.add_document(
        "Document",
        "document.txt",
        "txt",
        "data/documents/document.txt",
        7,
        "document-hash",
        "Extracted text.",
    )
    tag_id = db.create_tag("Shared")
    db.add_note_tag(note_id, tag_id)
    db.add_document_tag(document_id, tag_id)

    assert db.delete_document(document_id) is True
    assert db.get_document_by_id(document_id) is None
    assert db.get_all_notes()[0][1] == "Preserved note"
    assert [tag[0] for tag in db.get_note_tags(note_id)] == [tag_id]
    assert db.get_tag(tag_id) is not None

    with closing(db.get_connection()) as connection:
        document_tag_count = connection.execute(
            "SELECT COUNT(*) FROM document_tags WHERE document_id = ?",
            (document_id,),
        ).fetchone()[0]

    assert document_tag_count == 0
