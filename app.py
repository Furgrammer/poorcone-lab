import streamlit as st

from database import (
    add_note,
    delete_note,
    get_all_notes,
    initialize_database,
)

from search import rank_notes, rank_notes_char
from semantic_search import rank_notes_semantic
from hybrid_search import rank_notes_hybrid


initialize_database()

st.set_page_config(
    page_title="Poorcone Lab",
    page_icon="🧪",
    layout="centered",
)

st.title("Poorcone Lab")
st.caption("Personal AI Research Lab — Knowledge Vault")

# Bagian 1: Formulir menambah catatan
with st.form("note_form"):
    title = st.text_input("Judul catatan")

    category = st.selectbox(
        "Kategori",
        [
            "Python",
            "Machine Learning",
            "AI",
            "Project",
            "Lainnya",
        ],
    )

    content = st.text_area("Isi catatan")

    submitted = st.form_submit_button("Simpan catatan")

    if submitted:
        if title.strip() and content.strip():
            add_note(title.strip(), category, content.strip())
            st.success("Catatan berhasil disimpan.")
        else:
            st.warning("Judul dan isi catatan harus diisi.")


st.divider()
st.subheader("Cari pengetahuan")

search_method = st.selectbox(
    "Metode pencarian",
    [
        "Adaptive Hybrid Search",
        "Character TF-IDF",
        "Word TF-IDF",
        "Semantic Search",
    ],
    index=0,
)

st.caption(
    "Adaptive Hybrid: menggunakan Character TF-IDF "
    "untuk partial query dan Hybrid RRF untuk query normal."
)

keyword = st.text_input("Masukkan kata kunci")
all_notes = get_all_notes()


compare_methods = st.checkbox("Bandingkan Word TF-IDF dan Character TF-IDF")

if keyword.strip() and compare_methods:
    word_results = rank_notes(all_notes, keyword, limit=3)
    char_results = rank_notes_char(all_notes, keyword, limit=3)

    st.markdown("#### Perbandingan hasil pencarian")

    comparison_rows = []
    row_count = max(len(word_results), len(char_results), 1)

    for index in range(row_count):
        word_label = "—"
        char_label = "—"

        if index < len(word_results):
            note, score = word_results[index]
            word_label = f"{note[1]} ({score:.3f})"
        elif index == 0:
            word_label = "Tidak ada hasil"

        if index < len(char_results):
            note, score = char_results[index]
            char_label = f"{note[1]} ({score:.3f})"
        elif index == 0:
            char_label = "Tidak ada hasil"

        comparison_rows.append(
            {
                "Peringkat": index + 1,
                "Word TF-IDF": word_label,
                "Character TF-IDF": char_label,
            }
        )

    st.table(comparison_rows)

    st.caption(
        "Maksimal 3 hasil per metode. Skor menunjukkan kemiripan "
        "dalam masing-masing metode; skor kedua metode tidak "
        "dapat dibandingkan secara langsung."
    )


if keyword.strip():
    if search_method == "Adaptive Hybrid Search":
        results = rank_notes_hybrid(
            all_notes,
            keyword,
            limit=10,
        )

    elif search_method == "Character TF-IDF":
        results = rank_notes_char(
            all_notes,
            keyword,
            limit=10,
        )

    elif search_method == "Word TF-IDF":
        results = rank_notes(
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

else:
    results = [(note, None) for note in all_notes]

if keyword.strip() and not results:
    st.info("Tidak ditemukan catatan yang cocok.")
elif not results:
    st.info("Belum ada catatan yang tersimpan.")
else:
    if keyword.strip():
        if search_method == "Character TF-IDF":
            st.caption("Character TF-IDF — ambang skor minimum 0.12.")
        else:
            st.caption("Word TF-IDF — pencarian berdasarkan fitur kata.")

    for note, score in results:
        note_id, title, category, content = note

        with st.expander(f"{title} — {category}"):
            if score is not None:
                st.caption(f"Skor kemiripan: {score:.3f}")

            st.write(content)

            if st.button("Hapus catatan", key=f"delete_{note_id}"):
                delete_note(note_id)
                st.rerun()
