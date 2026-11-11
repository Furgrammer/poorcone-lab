import sqlite3
from contextlib import closing
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "pair_lab.db"


def get_connection():
    return sqlite3.connect(DB_PATH)


def initialize_database():
    with closing(get_connection()) as connection, connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                category TEXT NOT NULL,
                content TEXT NOT NULL
            )
        """)


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
