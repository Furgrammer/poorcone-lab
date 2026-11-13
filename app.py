import streamlit as st

from database import (
    add_note,
    update_note,
    delete_note,
    get_all_notes,
    get_all_documents,
    get_all_tags,
    normalize_tag_name,
    get_note_tags,
    get_document_tags,
    create_tag,
    rename_tag,
    delete_tag,
    add_note_tag,
    remove_note_tag,
    add_document_tag,
    remove_document_tag,
    update_document_title,
    initialize_database,
)

from ingestion import (
    DocumentDeletionRecoveryError,
    DocumentNotFoundError,
    delete_document as delete_document_service,
    ingest_document,
)

from search import rank_notes, rank_notes_char
from semantic_search import rank_notes_semantic
from hybrid_search import rank_notes_hybrid


# ============================================================
# 1. APPLICATION CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="Poorcone Lab",
    page_icon="🧪",
    layout="wide",
    initial_sidebar_state="collapsed",
)

initialize_database()


# ============================================================
# 2. CUSTOM STYLING
# ============================================================

st.markdown(
    """
    <style>
        .block-container {
            max-width: 1180px;
            padding-top: 2.5rem;
            padding-bottom: 3rem;
        }

        [data-testid="stMetric"] {
            background: rgba(128, 128, 128, 0.07);
            border: 1px solid rgba(128, 128, 128, 0.18);
            border-radius: 12px;
            padding: 16px;
        }

        div[data-testid="stForm"] {
            border: 1px solid rgba(128, 128, 128, 0.22);
            border-radius: 12px;
            padding: 20px;
        }

        .stTabs [data-baseweb="tab-list"] {
            gap: 12px;
        }

        [data-testid="stExpander"] {
            border-radius: 10px;
        }
    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# 3. HELPER FUNCTIONS
# ============================================================

NOTE_CATEGORIES = [
    "Python",
    "Machine Learning",
    "AI",
    "Game Development",
    "Software Engineering",
    "Data Science",
    "Project",
    "Lainnya",
]


def render_create_tag_form(form_key):
    with st.form(f"create_tag_form_{form_key}", clear_on_submit=True):
        tag_name = st.text_input(
            "Nama tag",
            key=f"create_tag_name_{form_key}",
        )
        submitted = st.form_submit_button(
            "Buat tag",
            key=f"create_tag_submit_{form_key}",
        )

    if submitted:
        try:
            existing_tags = get_all_tags()
            normalized_name = normalize_tag_name(tag_name)
            already_exists = any(tag[2] == normalized_name for tag in existing_tags)
            create_tag(tag_name)

            if already_exists:
                st.session_state["ui_notice"] = (
                    "info",
                    f"Tag '{tag_name.strip()}' sudah tersedia.",
                )
            else:
                st.session_state["ui_notice"] = (
                    "success",
                    f"Tag '{tag_name.strip()}' berhasil dibuat.",
                )
            st.rerun()
        except ValueError as error:
            st.error(str(error))
        except Exception:
            st.error("Tag gagal dibuat karena terjadi kesalahan database.")


def render_tag_assignments(entity_type, entity_id, associated_tags):
    if associated_tags:
        st.caption("Tags: " + ", ".join(tag[1] for tag in associated_tags))
    else:
        st.caption("Belum ada tag.")

    if entity_type == "note":
        add_relationship = add_note_tag
        remove_relationship = remove_note_tag
        entity_label = "catatan"
    else:
        add_relationship = add_document_tag
        remove_relationship = remove_document_tag
        entity_label = "dokumen"

    all_tags = get_all_tags()
    attached_tag_ids = {tag[0] for tag in associated_tags}
    available_tags = [tag for tag in all_tags if tag[0] not in attached_tag_ids]

    if available_tags:
        with st.form(f"add_{entity_type}_tag_{entity_id}"):
            selected_tag_id = st.selectbox(
                f"Tambahkan tag ke {entity_label}",
                [tag[0] for tag in available_tags],
                format_func=lambda tag_id: next(
                    tag[1] for tag in available_tags if tag[0] == tag_id
                ),
                key=f"add_{entity_type}_tag_select_{entity_id}",
            )
            submitted = st.form_submit_button(
                "Tambahkan tag",
                key=f"add_{entity_type}_tag_submit_{entity_id}",
            )

        if submitted:
            try:
                add_relationship(entity_id, selected_tag_id)
                st.rerun()
            except Exception as error:
                st.error(str(error))
    else:
        st.caption("Tidak ada tag lain untuk ditambahkan.")

    for tag_id, tag_name, *_ in associated_tags:
        if st.button(
            f"Lepas tag: {tag_name}",
            key=f"remove_{entity_type}_tag_{entity_id}_{tag_id}",
        ):
            try:
                remove_relationship(entity_id, tag_id)
                st.rerun()
            except Exception as error:
                st.error(str(error))


def render_note_list(notes, note_tags_by_id):
    """Menampilkan catatan dengan opsi edit dan hapus."""

    for index, note in enumerate(notes, start=1):
        note_id, title, category, content = note

        is_editing = st.session_state.get("editing_note_id") == note_id

        with st.expander(
            f"{index}. {title} — {category}",
            expanded=is_editing,
        ):
            # ------------------------------------------------
            # EDIT MODE
            # ------------------------------------------------

            if is_editing:
                st.markdown("#### Edit Catatan")

                # Pertahankan kategori lama jika belum tersedia
                # dalam pilihan kategori terbaru.
                edit_categories = NOTE_CATEGORIES.copy()

                if category not in edit_categories:
                    edit_categories.insert(0, category)

                with st.form(f"edit_note_form_{note_id}"):
                    edited_title = st.text_input(
                        "Judul catatan",
                        value=title,
                        key=f"edit_note_title_{note_id}",
                    )

                    edited_category = st.selectbox(
                        "Kategori",
                        edit_categories,
                        index=edit_categories.index(category),
                        key=f"edit_note_category_{note_id}",
                    )

                    edited_content = st.text_area(
                        "Isi catatan",
                        value=content,
                        height=220,
                        key=f"edit_note_content_{note_id}",
                    )

                    save_col, cancel_col = st.columns(2)

                    with save_col:
                        save_submitted = st.form_submit_button(
                            "💾 Simpan perubahan",
                            type="primary",
                            key=f"save_note_{note_id}",
                        )

                    with cancel_col:
                        cancel_submitted = st.form_submit_button(
                            "Batal",
                            key=f"cancel_edit_note_{note_id}",
                        )

                # Proses penyimpanan
                if save_submitted:
                    if edited_title.strip() and edited_content.strip():
                        updated = update_note(
                            note_id,
                            edited_title.strip(),
                            edited_category,
                            edited_content.strip(),
                        )

                        if updated:
                            st.session_state.pop(
                                "editing_note_id",
                                None,
                            )

                            st.session_state.pop(
                                "last_search",
                                None,
                            )

                            st.session_state["flash_message"] = (
                                f"Catatan '{edited_title.strip()}' berhasil diperbarui."
                            )

                            st.rerun()

                        else:
                            st.error(
                                "Catatan tidak ditemukan atau "
                                "tidak mengalami perubahan."
                            )

                    else:
                        st.warning("Judul dan isi catatan harus diisi.")

                # Batalkan proses edit
                if cancel_submitted:
                    st.session_state.pop(
                        "editing_note_id",
                        None,
                    )

                    st.rerun()

            # ------------------------------------------------
            # VIEW MODE
            # ------------------------------------------------

            else:
                st.write(content)

                edit_col, delete_col = st.columns(2)

                with edit_col:
                    if st.button(
                        "✏️ Edit Catatan",
                        key=f"edit_{note_id}",
                        use_container_width=True,
                    ):
                        st.session_state["editing_note_id"] = note_id

                        st.rerun()

                with delete_col:
                    if st.button(
                        "🗑️ Hapus Catatan",
                        key=f"delete_{note_id}",
                        use_container_width=True,
                    ):
                        delete_note(note_id)

                        st.session_state.pop(
                            "last_search",
                            None,
                        )

                        st.session_state["flash_message"] = (
                            f"Catatan '{title}' berhasil dihapus."
                        )

                        st.rerun()

            render_tag_assignments(
                "note",
                note_id,
                note_tags_by_id.get(note_id, []),
            )


def render_search_results(results, method):
    """Menampilkan hasil pencarian."""

    if not results:
        st.info("Tidak ditemukan catatan yang cocok.")
        return

    st.caption(f"Ditemukan {len(results)} hasil pencarian.")

    score_labels = {
        "Adaptive Hybrid Search": "Skor WRRF",
        "Semantic Search": "Skor semantic",
        "Character TF-IDF": "Skor Character TF-IDF",
        "Word TF-IDF": "Skor Word TF-IDF",
    }

    for index, (note, score) in enumerate(results, start=1):
        note_id, title, category, content = note

        with st.expander(
            f"#{index} · {title} — {category}",
            expanded=(index == 1),
        ):
            if score is not None:
                st.caption(f"{score_labels[method]}: {score:.4f}")

            st.write(content)


# ============================================================
# 4. LOAD DATA
# ============================================================

all_notes = get_all_notes()
all_documents = get_all_documents()
all_tags = get_all_tags()
note_tags_by_id = {note[0]: get_note_tags(note[0]) for note in all_notes}

total_notes = len(all_notes)
total_documents = len(all_documents)

total_categories = len({note[2] for note in all_notes})


# ============================================================
# 5. HEADER
# ============================================================

flash_message = st.session_state.pop(
    "flash_message",
    None,
)

if flash_message:
    st.success(flash_message)

ui_notice = st.session_state.pop("ui_notice", None)
if ui_notice:
    notice_level, notice_message = ui_notice
    getattr(st, notice_level)(notice_message)

header_left, header_right = st.columns([4, 1])

with header_left:
    st.title("🧪 Poorcone Lab")
    st.caption("Personal AI Research Lab — Knowledge Vault")

with header_right:
    st.caption("LOCAL KNOWLEDGE SYSTEM")


st.divider()


# ============================================================
# 6. DASHBOARD METRICS
# ============================================================

metric1, metric2, metric3, metric4 = st.columns(4)

with metric1:
    st.metric(
        "Total Notes",
        total_notes,
        help="Jumlah seluruh catatan dalam database.",
    )

with metric2:
    st.metric(
        "Categories",
        total_categories,
        help="Jumlah kategori berbeda yang digunakan.",
    )

with metric3:
    st.metric(
        "Documents",
        total_documents,
        help="Jumlah dokumen yang telah diimpor.",
    )

with metric4:
    st.metric(
        "Search Modes",
        4,
        help="Adaptive Hybrid, Semantic, Character, dan Word TF-IDF.",
    )


st.divider()


# ============================================================
# 7. MAIN NAVIGATION
# ============================================================

explore_tab, add_tab, notes_tab, documents_tab, tags_tab = st.tabs(
    [
        "🔎 Explore",
        "✍️ Add Notes",
        "📚 My Notes",
        "📄 Documents",
        "🏷️ Tags",
    ],
    key="main_tabs",
    on_change="rerun",
)


# ============================================================
# 8. EXPLORE TAB
# ============================================================

with explore_tab:
    st.subheader("Explore Your Knowledge")

    st.caption("Temukan pengetahuan menggunakan keyword, semantic, atau hybrid search.")

    # --------------------------------------------------------
    # SEARCH FORM
    # --------------------------------------------------------

    with st.form("search_form"):
        search_method = st.selectbox(
            "Metode pencarian",
            [
                "Adaptive Hybrid Search",
                "Semantic Search",
                "Character TF-IDF",
                "Word TF-IDF",
            ],
        )

        keyword = st.text_input(
            "Masukkan kata kunci atau pertanyaan",
            placeholder=("Contoh: cara kerja supervised learning..."),
        )

        compare_methods = st.checkbox("Bandingkan Word TF-IDF dan Character TF-IDF")

        search_submitted = st.form_submit_button(
            "🔍 Cari pengetahuan",
            type="primary",
            use_container_width=True,
        )

    # --------------------------------------------------------
    # SEARCH EXECUTION
    # --------------------------------------------------------

    method_descriptions = {
        "Adaptive Hybrid Search": (
            "Menggunakan Character TF-IDF untuk partial query "
            "dan Hybrid Search berbasis WRRF untuk query normal."
        ),
        "Semantic Search": (
            "Menggunakan sentence embeddings untuk mencari "
            "catatan berdasarkan kemiripan makna."
        ),
        "Character TF-IDF": (
            "Menggunakan fitur karakter untuk mendukung "
            "pencarian kata dan potongan kata."
        ),
        "Word TF-IDF": (
            "Menggunakan pembobotan kata untuk pencarian berbasis keyword."
        ),
    }

    st.caption(method_descriptions[search_method])

    if search_submitted:
        if not keyword.strip():
            st.warning("Masukkan kata kunci terlebih dahulu.")

        elif not all_notes:
            st.info("Belum ada catatan untuk dicari.")

        else:
            if search_method == "Adaptive Hybrid Search":
                results = rank_notes_hybrid(
                    all_notes,
                    keyword,
                    limit=10,
                )

            elif search_method == "Semantic Search":
                results = rank_notes_semantic(
                    all_notes,
                    keyword,
                    limit=10,
                    min_score=0.20,
                )

            elif search_method == "Character TF-IDF":
                results = rank_notes_char(
                    all_notes,
                    keyword,
                    limit=10,
                )

            else:
                results = rank_notes(
                    all_notes,
                    keyword,
                    limit=10,
                )

            comparison = None

            if compare_methods:
                word_results = rank_notes(
                    all_notes,
                    keyword,
                    limit=3,
                )

                char_results = rank_notes_char(
                    all_notes,
                    keyword,
                    limit=3,
                )

                comparison = {
                    "word": word_results,
                    "char": char_results,
                }

            st.session_state["last_search"] = {
                "query": keyword.strip(),
                "method": search_method,
                "results": results,
                "comparison": comparison,
            }

    # --------------------------------------------------------
    # DISPLAY SEARCH RESULTS
    # --------------------------------------------------------

    search_state = st.session_state.get("last_search")

    if search_state:
        st.divider()

        st.markdown(f"#### Hasil pencarian: `{search_state['query']}`")

        if search_state["comparison"] is not None:
            st.markdown("##### Perbandingan metode")

            word_results = search_state["comparison"]["word"]
            char_results = search_state["comparison"]["char"]

            comparison_rows = []

            row_count = max(
                len(word_results),
                len(char_results),
                1,
            )

            for index in range(row_count):
                word_label = "Tidak ada hasil"
                char_label = "Tidak ada hasil"

                if index < len(word_results):
                    note, score = word_results[index]

                    word_label = f"{note[1]} ({score:.3f})"

                if index < len(char_results):
                    note, score = char_results[index]

                    char_label = f"{note[1]} ({score:.3f})"

                comparison_rows.append(
                    {
                        "Rank": index + 1,
                        "Word TF-IDF": word_label,
                        "Character TF-IDF": char_label,
                    }
                )

            st.table(comparison_rows)

            st.caption(
                "Skor Word dan Character TF-IDF berasal dari "
                "metode berbeda, sehingga tidak dapat dibandingkan "
                "secara langsung."
            )

        st.markdown("##### Search Results")

        render_search_results(
            search_state["results"],
            search_state["method"],
        )

    else:
        st.info(
            "Masukkan kata kunci dan pilih metode pencarian "
            "untuk mulai menjelajahi knowledge base."
        )

        st.markdown(
            """
            **Contoh pencarian:**

            - `supervised learning`
            - `belajar dari data berlabel`
            - `supervis`
            - `pygame collision detection`
            """
        )


# ============================================================
# 9. ADD NOTES TAB
# ============================================================

with add_tab:
    st.subheader("Create New Note")

    st.caption(
        "Simpan pengetahuan, ide, atau dokumentasi ke dalam personal knowledge base."
    )

    with st.form("note_form", clear_on_submit=True):
        title = st.text_input(
            "Judul catatan",
            placeholder="Contoh: Introduction to Machine Learning",
            key="new_note_title",
        )

        category = st.selectbox(
            "Kategori",
            NOTE_CATEGORIES,
            key="new_note_category",
        )

        content = st.text_area(
            "Isi catatan",
            placeholder="Tuliskan pengetahuan atau informasi...",
            height=220,
            key="new_note_content",
        )

        submitted = st.form_submit_button(
            "💾 Simpan catatan",
            type="primary",
            key="save_new_note",
        )

        if submitted:
            if title.strip() and content.strip():
                add_note(
                    title.strip(),
                    category,
                    content.strip(),
                )

                st.session_state.pop("last_search", None)

                st.session_state["flash_message"] = "Catatan berhasil disimpan."

                st.rerun()

            else:
                st.warning("Judul dan isi catatan harus diisi.")


# ============================================================
# 10. MY NOTES TAB
# ============================================================

with notes_tab:
    st.subheader("My Knowledge Vault")

    st.caption("Kelola dan lihat seluruh catatan yang tersimpan.")

    st.markdown("#### Buat tag")
    render_create_tag_form("notes")

    if not all_notes:
        st.info("Belum ada catatan. Mulai dengan menambahkan catatan pertama.")

    else:
        available_categories = sorted({note[2] for note in all_notes})
        available_tag_ids = sorted(
            {tag[0] for tags in note_tags_by_id.values() for tag in tags}
            | {tag[0] for tag in all_tags}
        )

        selected_category = st.selectbox(
            "Filter kategori",
            ["Semua kategori"] + available_categories,
            key="notes_category_filter",
        )

        selected_tag_id = st.selectbox(
            "Filter tag",
            [None] + available_tag_ids,
            format_func=lambda tag_id: (
                "Semua tag"
                if tag_id is None
                else next(tag[1] for tag in all_tags if tag[0] == tag_id)
            ),
            key="notes_tag_filter",
        )

        filtered_notes = [
            note
            for note in all_notes
            if (
                selected_category == "Semua kategori"
                or note[2] == selected_category
            )
            and (
                selected_tag_id is None
                or selected_tag_id
                in {tag[0] for tag in note_tags_by_id.get(note[0], [])}
            )
        ]

        st.caption(f"Menampilkan {len(filtered_notes)} dari {total_notes} catatan.")

        render_note_list(filtered_notes, note_tags_by_id)


# ============================================================
# 11. DOCUMENTS TAB
# ============================================================

with documents_tab:
    st.subheader("Document Library")

    st.caption("Impor dan kelola dokumen sebagai bagian dari personal knowledge base.")

    # --------------------------------------------------------
    # DOCUMENT UPLOAD
    # --------------------------------------------------------

    st.markdown("#### Import Documents")

    st.caption("Format yang didukung: TXT, Markdown, PDF, dan DOCX. ")

    uploaded_files = st.file_uploader(
        "Pilih dokumen",
        type=["txt", "md", "pdf", "docx"],
        accept_multiple_files=True,
        help="Kamu dapat mengunggah beberapa dokumen sekaligus.",
        key="document_uploader",
    )

    if st.button(
        "📥 Import Documents",
        type="primary",
        use_container_width=True,
        disabled=not uploaded_files,
        key="import_documents_button",
    ):
        import_messages = []

        for uploaded_file in uploaded_files:
            try:
                result = ingest_document(
                    filename=uploaded_file.name,
                    content=uploaded_file.getvalue(),
                )

                if result.is_duplicate:
                    import_messages.append(
                        (
                            "warning",
                            f"{uploaded_file.name}: konten sudah "
                            f"tersimpan sebagai dokumen ID "
                            f"{result.document_id}.",
                        )
                    )

                else:
                    import_messages.append(
                        (
                            "success",
                            f"{uploaded_file.name} berhasil diimpor.",
                        )
                    )

            except Exception as error:
                import_messages.append(
                    (
                        "error",
                        f"Gagal mengimpor {uploaded_file.name}: {error}",
                    )
                )

        st.session_state["document_import_messages"] = import_messages

        st.rerun()

    # --------------------------------------------------------
    # IMPORT NOTIFICATIONS
    # --------------------------------------------------------

    document_import_messages = st.session_state.pop(
        "document_import_messages",
        [],
    )

    if document_import_messages:
        success_messages = [
            message for level, message in document_import_messages if level == "success"
        ]

        duplicate_messages = [
            message for level, message in document_import_messages if level == "warning"
        ]

        error_messages = [
            message for level, message in document_import_messages if level == "error"
        ]

        with st.container(border=True):
            st.markdown("#### Import Results")

            result_col1, result_col2, result_col3 = st.columns(3)

            with result_col1:
                st.metric("Imported", len(success_messages))

            with result_col2:
                st.metric("Duplicates", len(duplicate_messages))

            with result_col3:
                st.metric("Failed", len(error_messages))

            # Detail setiap file.
            with st.expander(
                "View import details",
                expanded=bool(error_messages),
            ):
                for level, message in document_import_messages:
                    if level == "success":
                        st.success(message)

                    elif level == "warning":
                        st.warning(message)

                    elif level == "error":
                        st.error(message)

    # --------------------------------------------------------
    # DOCUMENT LIBRARY
    # --------------------------------------------------------

    st.divider()

    st.markdown("#### Your Documents")
    st.markdown("##### Buat tag")
    render_create_tag_form("documents")

    if not all_documents:
        st.info("Belum ada dokumen. Impor file TXT atau Markdown untuk memulai.")

    else:
        st.caption(f"Menampilkan {total_documents} dokumen.")

        for document in all_documents:
            (
                document_id,
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
                updated_at,
            ) = document

            with st.expander(
                f"{title} · {original_filename}",
                expanded=False,
            ):
                st.caption(f"Original filename: {original_filename}")
                col1, col2 = st.columns(2)

                with col1:
                    st.caption(f"Document ID: {document_id}")
                    st.caption(f"File type: {file_type.upper()}")

                with col2:
                    st.caption(f"File size: {file_size_bytes / 1024:.2f} KB")
                    st.caption(f"Status: {processing_status}")

                st.caption(f"Imported: {created_at}")

                st.markdown("##### Edit document title")
                with st.form(f"edit_document_title_{document_id}"):
                    edited_title = st.text_input(
                        "Document title",
                        value=title,
                        key=f"document_title_input_{document_id}",
                    )
                    title_submitted = st.form_submit_button(
                        "Save title",
                        key=f"save_document_title_{document_id}",
                    )

                if title_submitted:
                    try:
                        if update_document_title(document_id, edited_title):
                            st.session_state["ui_notice"] = (
                                "success",
                                "Judul dokumen berhasil diperbarui.",
                            )
                            st.rerun()
                        st.error("Dokumen tidak ditemukan.")
                    except ValueError as error:
                        st.error(str(error))
                    except Exception:
                        st.error("Judul dokumen gagal diperbarui.")

                st.markdown("##### Document tags")
                render_tag_assignments(
                    "document",
                    document_id,
                    get_document_tags(document_id),
                )

                st.markdown("##### Document preview")
                if processing_status == "completed":
                    preview_limit = 5000
                    show_preview = st.checkbox(
                        "Show extracted text",
                        key=f"show_document_preview_{document_id}",
                    )

                    if show_preview:
                        preview_text = extracted_text[:preview_limit]
                        st.text_area(
                            "Extracted text",
                            value=preview_text,
                            height=220,
                            disabled=True,
                            key=f"document_preview_{document_id}",
                        )

                        if len(extracted_text) > preview_limit:
                            st.caption(
                                "Preview dibatasi hingga 5.000 karakter. "
                                "Konten lengkap tetap tersimpan di database."
                            )
                elif processing_status == "failed":
                    st.error(processing_error or "Document processing failed.")

                st.markdown("##### Delete document")
                st.warning(
                    "Penghapusan akan menghapus metadata dan file dokumen. "
                    "Tindakan ini tidak dapat dibatalkan."
                )
                confirmed = st.checkbox(
                    "Saya yakin ingin menghapus dokumen ini",
                    key=f"confirm_delete_document_{document_id}",
                )
                if st.button(
                    "Delete document",
                    key=f"delete_document_{document_id}",
                    type="primary",
                    disabled=not confirmed,
                ):
                    try:
                        deletion = delete_document_service(document_id)
                        if deletion is None:
                            st.session_state["ui_notice"] = (
                                "error",
                                "Dokumen tidak ditemukan atau tidak terhapus.",
                            )
                        elif deletion.cleanup_pending:
                            st.session_state["ui_notice"] = (
                                "warning",
                                "Metadata dokumen terhapus, tetapi pembersihan file "
                                f"masih tertunda. Lokasi staging: {deletion.staging_path}",
                            )
                        elif deletion.file_missing:
                            st.session_state["ui_notice"] = (
                                "warning",
                                "Metadata dokumen terhapus; file fisik sebelumnya "
                                "sudah tidak ditemukan.",
                            )
                        else:
                            st.session_state["ui_notice"] = (
                                "success",
                                "Dokumen dan file fisiknya berhasil dihapus.",
                            )
                        st.rerun()
                    except DocumentNotFoundError:
                        st.session_state["ui_notice"] = (
                            "error",
                            "Dokumen tidak ditemukan.",
                        )
                        st.rerun()
                    except DocumentDeletionRecoveryError as error:
                        st.session_state["ui_notice"] = (
                            "error",
                            "Penghapusan metadata gagal dan file tidak dapat "
                            f"dipulihkan. Lokasi pemulihan: {error.recovery_path}",
                        )
                        st.rerun()
                    except Exception:
                        st.error("Dokumen gagal dihapus. Data belum dapat dipastikan.")


# ============================================================
# 12. GLOBAL TAG MANAGEMENT
# ============================================================

with tags_tab:
    st.subheader("Tag management")
    st.caption("Tag yang sama dapat digunakan oleh Notes dan Documents.")
    st.warning(
        "Menghapus tag akan melepas relasinya dari Notes dan Documents, "
        "tetapi tidak menghapus Notes atau Documents tersebut."
    )

    st.markdown("#### Buat tag")
    render_create_tag_form("global")

    st.divider()
    st.markdown("#### Existing tags")

    current_tags = get_all_tags()
    if not current_tags:
        st.info("Belum ada tag.")
    else:
        for tag_id, tag_name, *_ in current_tags:
            with st.expander(tag_name, key=f"global_tag_{tag_id}"):
                with st.form(f"rename_tag_form_{tag_id}"):
                    new_tag_name = st.text_input(
                        "Nama tag baru",
                        value=tag_name,
                        key=f"rename_tag_name_{tag_id}",
                    )
                    rename_submitted = st.form_submit_button(
                        "Ganti nama tag",
                        key=f"rename_tag_submit_{tag_id}",
                    )

                if rename_submitted:
                    try:
                        if rename_tag(tag_id, new_tag_name):
                            st.session_state["ui_notice"] = (
                                "success",
                                f"Tag '{tag_name}' berhasil diganti namanya.",
                            )
                            st.rerun()
                        st.error("Tag tidak ditemukan.")
                    except ValueError as error:
                        st.error(str(error))
                    except Exception:
                        st.error("Tag gagal diganti namanya.")

                confirmed = st.checkbox(
                    "Saya paham relasi tag ini akan dilepas",
                    key=f"confirm_delete_tag_{tag_id}",
                )
                if st.button(
                    "Hapus tag",
                    key=f"delete_tag_{tag_id}",
                    disabled=not confirmed,
                ):
                    try:
                        if delete_tag(tag_id):
                            st.session_state["ui_notice"] = (
                                "success",
                                f"Tag '{tag_name}' dan relasinya berhasil dihapus.",
                            )
                            st.rerun()
                        st.error("Tag tidak ditemukan.")
                    except Exception:
                        st.error("Tag gagal dihapus.")


# ============================================================
# 13. FOOTER
# ============================================================

st.divider()

st.caption(
    "Poorcone Lab · Personal AI Research Lab · "
    "Powered by Python, SQLite, and Machine Learning."
)
