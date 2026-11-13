from contextlib import closing
from pathlib import Path
import sqlite3
import unicodedata

DB_PATH = Path(__file__).resolve().parent / "poorcone_lab.db"

CURRENT_SCHEMA_VERSION = 2


def get_connection():
    connection = sqlite3.connect(DB_PATH)
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def _migrate_to_v1(connection):
    """
    Migration v1:
    - Memastikan tabel notes tersedia.
    - Membuat tabel documents.
    - Membuat index untuk pencarian metadata.
    """

    # Existing table: tidak mengubah data maupun struktur.
    connection.execute("""
        CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            category TEXT NOT NULL,
            content TEXT NOT NULL
        )
    """)

    # New table: documents.
    connection.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            title TEXT NOT NULL,
            original_filename TEXT NOT NULL,
            file_type TEXT NOT NULL,

            storage_path TEXT NOT NULL UNIQUE,
            file_size_bytes INTEGER NOT NULL
                CHECK (file_size_bytes >= 0),

            content_hash TEXT NOT NULL,
            extracted_text TEXT NOT NULL DEFAULT '',

            processing_status TEXT NOT NULL DEFAULT 'pending'
                CHECK (
                    processing_status IN (
                        'pending',
                        'processing',
                        'completed',
                        'failed'
                    )
                ),

            processing_error TEXT,

            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Index untuk mempercepat pencarian berdasarkan metadata.
    connection.execute("""
        CREATE INDEX IF NOT EXISTS idx_documents_content_hash
        ON documents(content_hash)
    """)

    connection.execute("""
        CREATE INDEX IF NOT EXISTS idx_documents_processing_status
        ON documents(processing_status)
    """)


def _migrate_to_v2(connection):
    """Migration v2: menambahkan tag dan relasi ke Notes serta Documents."""

    connection.execute("""
        CREATE TABLE IF NOT EXISTS tags (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            normalized_name TEXT NOT NULL UNIQUE,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """)

    connection.execute("""
        CREATE TABLE IF NOT EXISTS note_tags (
            note_id INTEGER NOT NULL,
            tag_id INTEGER NOT NULL,
            PRIMARY KEY (note_id, tag_id),
            FOREIGN KEY (note_id) REFERENCES notes(id) ON DELETE CASCADE,
            FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE
        )
    """)

    connection.execute("""
        CREATE TABLE IF NOT EXISTS document_tags (
            document_id INTEGER NOT NULL,
            tag_id INTEGER NOT NULL,
            PRIMARY KEY (document_id, tag_id),
            FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE,
            FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE
        )
    """)

    connection.execute("""
        CREATE INDEX IF NOT EXISTS idx_note_tags_tag_id
        ON note_tags(tag_id)
    """)

    connection.execute("""
        CREATE INDEX IF NOT EXISTS idx_document_tags_tag_id
        ON document_tags(tag_id)
    """)


# Setiap versi baru didaftarkan di sini.
MIGRATIONS = {
    1: _migrate_to_v1,
    2: _migrate_to_v2,
}


def initialize_database():
    """
    Menginisialisasi database dan menjalankan migration
    yang belum diterapkan.
    """

    with closing(get_connection()) as connection:
        try:
            # Mencegah dua proses menjalankan migration bersamaan.
            connection.execute("BEGIN IMMEDIATE")

            current_version = connection.execute("PRAGMA user_version").fetchone()[0]

            # Mencegah aplikasi lama membuka database dengan
            # skema yang lebih baru.
            if current_version > CURRENT_SCHEMA_VERSION:
                raise RuntimeError(
                    f"Database schema version {current_version} "
                    f"is newer than supported version "
                    f"{CURRENT_SCHEMA_VERSION}."
                )

            # Jalankan migration secara berurutan.
            while current_version < CURRENT_SCHEMA_VERSION:
                next_version = current_version + 1

                migration = MIGRATIONS.get(next_version)

                if migration is None:
                    raise RuntimeError(f"Migration v{next_version} is not defined.")

                migration(connection)

                connection.execute(f"PRAGMA user_version = {next_version}")

                current_version = next_version

            connection.commit()

        except Exception:
            connection.rollback()
            raise


def add_note(title, category, content):
    with closing(get_connection()) as connection, connection:
        connection.execute(
            """
            INSERT INTO notes (title, category, content)
            VALUES (?, ?, ?)
            """,
            (title, category, content),
        )


def update_note(note_id, title, category, content):
    """Memperbarui catatan berdasarkan ID."""

    with closing(get_connection()) as connection, connection:
        cursor = connection.execute(
            """
            UPDATE notes
            SET title = ?, category = ?, content = ?
            WHERE id = ?
            """,
            (title, category, content, note_id),
        )

        return cursor.rowcount > 0


def get_all_notes():
    with closing(get_connection()) as connection:
        cursor = connection.execute("""
            SELECT id, title, category, content
            FROM notes
            ORDER BY id DESC
        """)

        return cursor.fetchall()


def delete_note(note_id):
    with closing(get_connection()) as connection, connection:
        connection.execute(
            "DELETE FROM notes WHERE id = ?",
            (note_id,),
        )


def add_document(
    title,
    original_filename,
    file_type,
    storage_path,
    file_size_bytes,
    content_hash,
    extracted_text,
):
    """Menyimpan metadata dan teks hasil ekstraksi dokumen."""

    with closing(get_connection()) as connection, connection:
        cursor = connection.execute(
            """
            INSERT INTO documents (
                title,
                original_filename,
                file_type,
                storage_path,
                file_size_bytes,
                content_hash,
                extracted_text,
                processing_status
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, 'completed')
            """,
            (
                title,
                original_filename,
                file_type,
                storage_path,
                file_size_bytes,
                content_hash,
                extracted_text,
            ),
        )

        return cursor.lastrowid


def get_document_by_hash(content_hash):
    """Mencari dokumen berdasarkan SHA-256."""

    with closing(get_connection()) as connection:
        return connection.execute(
            """
            SELECT
                id,
                title,
                original_filename,
                file_type,
                storage_path,
                file_size_bytes,
                content_hash,
                extracted_text,
                processing_status
            FROM documents
            WHERE content_hash = ?
            ORDER BY id ASC
            LIMIT 1
            """,
            (content_hash,),
        ).fetchone()


def get_document_by_id(document_id):
    """Mengambil metadata dokumen berdasarkan ID, atau None jika tidak ada."""

    with closing(get_connection()) as connection:
        return connection.execute(
            """
            SELECT
                id,
                title,
                original_filename,
                file_type,
                storage_path,
                file_size_bytes,
                content_hash,
                extracted_text,
                processing_status,
                processing_error,
                created_at,
                updated_at
            FROM documents
            WHERE id = ?
            """,
            (document_id,),
        ).fetchone()


def update_document_title(document_id, title):
    """Mengganti judul dokumen tanpa mengubah metadata sumbernya."""

    if not isinstance(title, str):
        raise ValueError("Judul dokumen harus berupa string.")

    normalized_title = title.strip()
    if not normalized_title:
        raise ValueError("Judul dokumen tidak boleh kosong.")

    with closing(get_connection()) as connection, connection:
        cursor = connection.execute(
            """
            UPDATE documents
            SET title = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (normalized_title, document_id),
        )
        return cursor.rowcount > 0


def delete_document(document_id):
    """Menghapus metadata dokumen; document_tags dihapus melalui cascade."""

    with closing(get_connection()) as connection, connection:
        cursor = connection.execute(
            "DELETE FROM documents WHERE id = ?",
            (document_id,),
        )
        return cursor.rowcount > 0


def get_all_documents():
    """Mengambil seluruh dokumen berdasarkan ID terbaru."""

    with closing(get_connection()) as connection:
        return connection.execute(
            """
            SELECT
                id,
                title,
                original_filename,
                file_type,
                storage_path,
                file_size_bytes,
                content_hash,
                extracted_text,
                processing_status,
                processing_error,
                created_at,
                updated_at
            FROM documents
            ORDER BY id DESC
            """
        ).fetchall()


def normalize_tag_name(name):
    """Memvalidasi dan menormalisasi nama tag untuk pencocokan unik."""

    if not isinstance(name, str):
        raise ValueError("Nama tag harus berupa string.")

    display_name = unicodedata.normalize("NFC", name.strip())

    if not display_name:
        raise ValueError("Nama tag tidak boleh kosong.")

    if len(display_name) > 50:
        raise ValueError("Nama tag maksimal 50 karakter.")

    return unicodedata.normalize("NFC", display_name.casefold())


def _prepare_tag_name(name):
    normalized_name = normalize_tag_name(name)
    display_name = unicodedata.normalize("NFC", name.strip())
    return display_name, normalized_name


def create_tag(name):
    """Membuat tag; jika tag ekuivalen sudah ada, ID yang ada dikembalikan."""

    display_name, normalized_name = _prepare_tag_name(name)

    with closing(get_connection()) as connection, connection:
        connection.execute(
            """
            INSERT OR IGNORE INTO tags (name, normalized_name)
            VALUES (?, ?)
            """,
            (display_name, normalized_name),
        )

        row = connection.execute(
            "SELECT id FROM tags WHERE normalized_name = ?",
            (normalized_name,),
        ).fetchone()

        if row is None:
            raise RuntimeError("Tag gagal disimpan.")

        return row[0]


def get_all_tags():
    """Mengambil semua tag berdasarkan nama tampilan."""

    with closing(get_connection()) as connection:
        return connection.execute(
            """
            SELECT id, name, normalized_name, created_at
            FROM tags
            ORDER BY name COLLATE NOCASE, id
            """
        ).fetchall()


def get_tag(tag_id):
    """Mengambil tag berdasarkan ID, atau None jika tidak ditemukan."""

    with closing(get_connection()) as connection:
        return connection.execute(
            """
            SELECT id, name, normalized_name, created_at
            FROM tags
            WHERE id = ?
            """,
            (tag_id,),
        ).fetchone()


def rename_tag(tag_id, name):
    """Mengganti nama tag; konflik nama menghasilkan ValueError."""

    display_name, normalized_name = _prepare_tag_name(name)

    with closing(get_connection()) as connection, connection:
        tag = connection.execute(
            "SELECT id FROM tags WHERE id = ?",
            (tag_id,),
        ).fetchone()

        if tag is None:
            return False

        conflict = connection.execute(
            """
            SELECT id FROM tags
            WHERE normalized_name = ? AND id != ?
            """,
            (normalized_name, tag_id),
        ).fetchone()

        if conflict is not None:
            raise ValueError(f"Nama tag '{display_name}' sudah digunakan.")

        try:
            connection.execute(
                """
                UPDATE tags
                SET name = ?, normalized_name = ?
                WHERE id = ?
                """,
                (display_name, normalized_name, tag_id),
            )
        except sqlite3.IntegrityError as error:
            raise ValueError(f"Nama tag '{display_name}' sudah digunakan.") from error

        return True


def delete_tag(tag_id):
    """Menghapus tag dan semua relasi Notes/Documents-nya."""

    with closing(get_connection()) as connection, connection:
        cursor = connection.execute(
            "DELETE FROM tags WHERE id = ?",
            (tag_id,),
        )
        return cursor.rowcount > 0


def _require_entity(connection, table, entity_id, entity_label):
    row = connection.execute(
        f"SELECT 1 FROM {table} WHERE id = ?",
        (entity_id,),
    ).fetchone()

    if row is None:
        raise ValueError(f"{entity_label} dengan ID {entity_id} tidak ditemukan.")


def _require_tag(connection, tag_id):
    if connection.execute(
        "SELECT 1 FROM tags WHERE id = ?",
        (tag_id,),
    ).fetchone() is None:
        raise ValueError(f"Tag dengan ID {tag_id} tidak ditemukan.")


def _add_entity_tag(
    entity_table,
    relation_table,
    entity_column,
    entity_id,
    tag_id,
    entity_label,
):
    with closing(get_connection()) as connection, connection:
        _require_entity(connection, entity_table, entity_id, entity_label)
        _require_tag(connection, tag_id)

        cursor = connection.execute(
            f"""
            INSERT OR IGNORE INTO {relation_table} ({entity_column}, tag_id)
            VALUES (?, ?)
            """,
            (entity_id, tag_id),
        )
        return cursor.rowcount > 0


def _remove_entity_tag(
    entity_table,
    relation_table,
    entity_column,
    entity_id,
    tag_id,
    entity_label,
):
    with closing(get_connection()) as connection, connection:
        _require_entity(connection, entity_table, entity_id, entity_label)
        _require_tag(connection, tag_id)

        cursor = connection.execute(
            f"""
            DELETE FROM {relation_table}
            WHERE {entity_column} = ? AND tag_id = ?
            """,
            (entity_id, tag_id),
        )
        return cursor.rowcount > 0


def _get_entity_tags(
    entity_table,
    relation_table,
    entity_column,
    entity_id,
    entity_label,
):
    with closing(get_connection()) as connection:
        _require_entity(connection, entity_table, entity_id, entity_label)

        return connection.execute(
            f"""
            SELECT tags.id, tags.name, tags.normalized_name, tags.created_at
            FROM tags
            JOIN {relation_table} ON {relation_table}.tag_id = tags.id
            WHERE {relation_table}.{entity_column} = ?
            ORDER BY tags.name COLLATE NOCASE, tags.id
            """,
            (entity_id,),
        ).fetchall()


def add_note_tag(note_id, tag_id):
    """Menghubungkan tag dengan Note; relasi duplikat tidak dibuat."""

    return _add_entity_tag(
        "notes", "note_tags", "note_id", note_id, tag_id, "Note"
    )


def remove_note_tag(note_id, tag_id):
    """Melepas tag dari Note."""

    return _remove_entity_tag(
        "notes", "note_tags", "note_id", note_id, tag_id, "Note"
    )


def get_note_tags(note_id):
    """Mengambil tag yang terhubung dengan Note."""

    return _get_entity_tags(
        "notes", "note_tags", "note_id", note_id, "Note"
    )


def add_document_tag(document_id, tag_id):
    """Menghubungkan tag dengan Document; relasi duplikat tidak dibuat."""

    return _add_entity_tag(
        "documents",
        "document_tags",
        "document_id",
        document_id,
        tag_id,
        "Document",
    )


def remove_document_tag(document_id, tag_id):
    """Melepas tag dari Document."""

    return _remove_entity_tag(
        "documents",
        "document_tags",
        "document_id",
        document_id,
        tag_id,
        "Document",
    )


def get_document_tags(document_id):
    """Mengambil tag yang terhubung dengan Document."""

    return _get_entity_tags(
        "documents",
        "document_tags",
        "document_id",
        document_id,
        "Document",
    )
