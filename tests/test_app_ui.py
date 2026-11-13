from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

import database
import ingestion


APP_PATH = Path(__file__).resolve().parents[1] / "app.py"


@pytest.fixture
def app_environment(tmp_path, monkeypatch):
    database_path = tmp_path / "ui-test.db"
    storage_path = tmp_path / "data" / "documents"

    monkeypatch.setattr(database, "DB_PATH", database_path)
    monkeypatch.setattr(ingestion, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(ingestion, "DOCUMENT_STORAGE_DIR", storage_path)

    database.initialize_database()

    def run_app():
        return AppTest.from_file(str(APP_PATH), default_timeout=20).run()

    return run_app


def _caption_values(app):
    return [element.value for element in app.caption]


def test_note_tag_controls_create_attach_and_detach_tags(app_environment):
    database.add_note("Tagged note", "Python", "Synthetic note content.")
    note_id = database.get_all_notes()[0][0]
    tag_id = database.create_tag("Study")
    app = app_environment()

    assert not app.exception
    assert any("Belum ada tag." in value for value in _caption_values(app))

    app.get_by_key(f"add_note_tag_submit_{note_id}").click().run()
    assert not app.exception
    assert [tag[0] for tag in database.get_note_tags(note_id)] == [tag_id]
    assert any("Tags: Study" in value for value in _caption_values(app))

    app.get_by_key(f"remove_note_tag_{note_id}_{tag_id}").click().run()
    assert not app.exception
    assert database.get_note_tags(note_id) == []

    app.text_input(key="create_tag_name_notes").set_value("Created in Notes")
    app.get_by_key("create_tag_submit_notes").click().run()
    assert not app.exception
    assert any(tag[1] == "Created in Notes" for tag in database.get_all_tags())


def test_notes_can_be_filtered_by_category_and_tag(app_environment):
    database.add_note("Python note", "Python", "First synthetic note.")
    database.add_note("AI note", "AI", "Second synthetic note.")
    database.add_note("Other Python note", "Python", "Third synthetic note.")
    notes_by_title = {note[1]: note[0] for note in database.get_all_notes()}
    tag_id = database.create_tag("Career")
    database.add_note_tag(notes_by_title["Python note"], tag_id)
    database.add_note_tag(notes_by_title["AI note"], tag_id)

    app = app_environment()
    app.selectbox(key="notes_category_filter").select("Python")
    app.selectbox(key="notes_tag_filter").select(tag_id).run()

    assert not app.exception
    assert any("Menampilkan 1 dari 3 catatan." in value for value in _caption_values(app))
    note_expanders = [item.label for item in app.get("expander")]
    assert any("Python note — Python" in label for label in note_expanders)
    assert not any("AI note — AI" in label for label in note_expanders)


def test_note_creation_workflow_remains_available(app_environment):
    app = app_environment()
    app.text_input(key="new_note_title").set_value("New UI note")
    app.text_area(key="new_note_content").set_value("Synthetic UI-created content.")
    app.get_by_key("save_new_note").click().run()

    assert not app.exception
    assert any(note[1] == "New UI note" for note in database.get_all_notes())


def test_documents_show_metadata_tags_and_title_can_be_edited(app_environment):
    result = ingestion.ingest_document("original-name.txt", b"Synthetic document body.")
    tag_id = database.create_tag("Research")
    database.add_document_tag(result.document_id, tag_id)

    app = app_environment()

    assert not app.exception
    assert any("Original filename: original-name.txt" in item.value for item in app.caption)
    assert any("File type: TXT" in item.value for item in app.caption)
    assert any("Tags: Research" in item.value for item in app.caption)
    assert not any(
        element.key == f"document_preview_{result.document_id}"
        for element in app.text_area
    )

    app.text_input(key=f"document_title_input_{result.document_id}").set_value(
        "Edited title"
    )
    app.get_by_key(f"save_document_title_{result.document_id}").click().run()

    assert not app.exception
    assert database.get_document_by_id(result.document_id)[1] == "Edited title"
    assert any("Judul dokumen berhasil diperbarui." in item.value for item in app.success)


def test_document_tags_can_be_attached_and_detached(app_environment):
    result = ingestion.ingest_document("tag-document.txt", b"Synthetic tag content.")
    tag_id = database.create_tag("Document tag")
    app = app_environment()

    app.get_by_key(f"add_document_tag_submit_{result.document_id}").click().run()
    assert not app.exception
    assert [tag[0] for tag in database.get_document_tags(result.document_id)] == [
        tag_id
    ]

    app.get_by_key(f"remove_document_tag_{result.document_id}_{tag_id}").click().run()
    assert not app.exception
    assert database.get_document_tags(result.document_id) == []


def test_document_delete_requires_confirmation_and_refreshes_listing(app_environment):
    result = ingestion.ingest_document("delete-me.txt", b"Synthetic deletion content.")
    document = database.get_document_by_id(result.document_id)
    stored_file = Path(ingestion.PROJECT_ROOT) / document[4]
    app = app_environment()

    delete_button = app.get_by_key(f"delete_document_{result.document_id}")
    assert delete_button.disabled
    assert database.get_document_by_id(result.document_id) is not None

    app.get_by_key(f"confirm_delete_document_{result.document_id}").check().run()
    app.get_by_key(f"delete_document_{result.document_id}").click().run()

    assert not app.exception
    assert database.get_document_by_id(result.document_id) is None
    assert not stored_file.exists()
    assert any("berhasil dihapus" in item.value for item in app.success)


def test_cleanup_pending_is_reported_as_warning_not_complete_deletion(
    app_environment,
    monkeypatch,
    tmp_path,
):
    result = ingestion.ingest_document("cleanup-pending.txt", b"Synthetic content.")
    staging_path = tmp_path / "data" / "documents" / ".deletion-staging" / "pending"

    monkeypatch.setattr(
        ingestion,
        "delete_document",
        lambda document_id: ingestion.DocumentDeletionResult(
            document_id=document_id,
            cleanup_pending=True,
            staging_path=staging_path,
        ),
    )
    app = app_environment()

    app.get_by_key(f"confirm_delete_document_{result.document_id}").check().run()
    app.get_by_key(f"delete_document_{result.document_id}").click().run()

    assert not app.exception
    assert any("pembersihan file masih tertunda" in item.value for item in app.warning)
    assert any(str(staging_path) in item.value for item in app.warning)
    assert not any("berhasil dihapus" in item.value for item in app.success)


@pytest.mark.parametrize(
    ("service_result", "service_error", "alert_type", "expected_text"),
    [
        (
            ingestion.DocumentDeletionResult(document_id=1, file_missing=True),
            None,
            "warning",
            "file fisik sebelumnya sudah tidak ditemukan",
        ),
        (
            None,
            ingestion.DocumentNotFoundError("missing"),
            "error",
            "Dokumen tidak ditemukan",
        ),
        (
            None,
            ingestion.DocumentDeletionRecoveryError("restore failed", "/tmp/recovery"),
            "error",
            "/tmp/recovery",
        ),
    ],
)
def test_document_deletion_errors_and_missing_file_are_reported(
    app_environment,
    monkeypatch,
    service_result,
    service_error,
    alert_type,
    expected_text,
):
    result = ingestion.ingest_document("status.txt", b"Synthetic deletion status.")

    def fake_delete(document_id):
        if service_error is not None:
            raise service_error
        return service_result

    monkeypatch.setattr(ingestion, "delete_document", fake_delete)
    app = app_environment()
    app.get_by_key(f"confirm_delete_document_{result.document_id}").check().run()
    app.get_by_key(f"delete_document_{result.document_id}").click().run()

    assert not app.exception
    alerts = getattr(app, alert_type)
    assert any(expected_text in item.value for item in alerts)
    assert not any("berhasil dihapus" in item.value for item in app.success)


def test_global_tag_creation_validation_rename_and_delete(app_environment):
    app = app_environment()

    app.text_input(key="create_tag_name_global").set_value("   ")
    app.get_by_key("create_tag_submit_global").click().run()
    assert not app.exception
    assert any("Nama tag tidak boleh kosong" in item.value for item in app.error)

    app.text_input(key="create_tag_name_global").set_value("Python")
    app.get_by_key("create_tag_submit_global").click().run()
    tag_id = database.get_all_tags()[0][0]
    assert not app.exception
    assert database.get_tag(tag_id)[1] == "Python"

    app.text_input(key="create_tag_name_global").set_value("PYTHON")
    app.get_by_key("create_tag_submit_global").click().run()
    assert not app.exception
    assert len(database.get_all_tags()) == 1
    assert any("sudah tersedia" in item.value for item in app.info)

    app.text_input(key=f"rename_tag_name_{tag_id}").set_value("Programming")
    app.get_by_key(f"rename_tag_submit_{tag_id}").click().run()
    assert not app.exception
    assert database.get_tag(tag_id)[1] == "Programming"

    app.get_by_key(f"confirm_delete_tag_{tag_id}").check().run()
    app.get_by_key(f"delete_tag_{tag_id}").click().run()
    assert not app.exception
    assert database.get_tag(tag_id) is None
