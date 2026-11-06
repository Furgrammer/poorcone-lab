from database import get_all_notes
from search import rank_notes, rank_notes_char
from semantic_search import rank_notes_semantic
from hybrid_search import (
    rank_notes_hybrid,
    is_partial_query,
)


QUERY = "metode belajar mesin dengan contoh yang memiliki jawaban"


def display_results(name, results):
    print(f"\n=== {name} ===")
    print(f"Jumlah hasil: {len(results)}")

    if not results:
        print("Tidak ada hasil.")
        return

    for rank, (note, score) in enumerate(results, start=1):
        note_id, title, category, content = note

        print(f"{rank:2}. ID: {note_id} | {title} — {category} | Score: {score:.6f}")


def main():
    all_notes = get_all_notes()

    print(f"Jumlah catatan dalam database: {len(all_notes)}")
    print(f"Query: {QUERY}")
    print(f"Partial query: {is_partial_query(all_notes, QUERY)}")

    # 1. Word TF-IDF
    word_results = rank_notes(
        all_notes,
        QUERY,
        limit=10,
    )

    display_results("Word TF-IDF", word_results)

    # 2. Character TF-IDF
    char_results = rank_notes_char(
        all_notes,
        QUERY,
        limit=10,
        min_score=0.12,
    )

    display_results("Character TF-IDF", char_results)

    # 3. Semantic Search
    semantic_results = rank_notes_semantic(
        all_notes,
        QUERY,
        limit=10,
        min_score=0.20,
    )

    display_results("Semantic Search", semantic_results)

    # 4. Adaptive Hybrid Search
    hybrid_results = rank_notes_hybrid(
        all_notes,
        QUERY,
        limit=10,
    )

    display_results("Adaptive Hybrid Search", hybrid_results)


if __name__ == "__main__":
    main()
