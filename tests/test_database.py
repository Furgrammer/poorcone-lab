import pytest

import database


@pytest.fixture
def db(tmp_path, monkeypatch):
    """
    Membuat database sementara untuk setiap test.
    Database utama pair_lab.db tidak akan disentuh.
    """
    test_db_path = tmp_path / "test_pair_lab.db"

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
