import sqlite3
from contextlib import closing
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "poorcone_lab.db"

CURRENT_SCHEMA_VERSION = 1


def get_connection():
    return sqlite3.connect(DB_PATH)


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


# Setiap versi baru didaftarkan di sini.
MIGRATIONS = {
    1: _migrate_to_v1,
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
