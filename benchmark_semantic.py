from search import rank_notes, rank_notes_char
from semantic_search import rank_notes_semantic
from hybrid_search import rank_notes_hybrid


SAMPLE_NOTES = [
    (
        1,
        "Supervised Learning",
        "Machine Learning",
        "Pembelajaran menggunakan kumpulan data yang "
        "sudah diberi label untuk memprediksi keluaran.",
    ),
    (
        2,
        "Unsupervised Learning",
        "Machine Learning",
        "Algoritma mencari kelompok atau struktur tersembunyi "
        "dari data yang belum memiliki label.",
    ),
    (
        3,
        "Player Movement",
        "Game Development",
        "Pergerakan karakter dalam game dikendalikan "
        "melalui tombol keyboard menggunakan Pygame.",
    ),
    (
        4,
        "TF-IDF Search",
        "Information Retrieval",
        "Pembobotan kata untuk menilai pentingnya sebuah "
        "istilah dalam dokumen dibandingkan dokumen lainnya.",
    ),
    (
        5,
        "Python Lists",
        "Python",
        "Struktur data untuk menyimpan beberapa item "
        "secara berurutan dan dapat diperbarui.",
    ),
]


# Ground truth: ID catatan yang dianggap relevan.
BENCHMARK_CASES = [
    {
        "query": "metode belajar mesin dengan contoh yang memiliki jawaban",
        "relevant_ids": {1},
    },
    {
        "query": "cara mengelompokkan data tanpa mengetahui kelasnya",
        "relevant_ids": {2},
    },
    {
        "query": "menggerakkan avatar menggunakan tombol komputer",
        "relevant_ids": {3},
    },
    {
        "query": "menentukan relevansi dokumen berdasarkan frekuensi istilah",
        "relevant_ids": {4},
    },
    {
        "query": "wadah untuk menyimpan banyak elemen yang bisa diubah",
        "relevant_ids": {5},
    },
    {
        "query": "supervis",
        "relevant_ids": {1},
    },
]

PARTIAL_QUERY_CASES = [
    {
        "query": "super",
        "relevant_ids": {1},
    },
    {
        "query": "superv",
        "relevant_ids": {1},
    },
    {
        "query": "supervis",
        "relevant_ids": {1},
    },
    {
        "query": "vised",
        "relevant_ids": {1},
    },
]


NEGATIVE_QUERIES = [
    "astronomi dan galaksi",
    "resep masakan nasi goreng",
]


def precision_at_k(results, relevant_ids, k):
    if k <= 0:
        return 0.0

    retrieved_ids = [note[0] for note, _ in results[:k]]

    relevant_count = sum(note_id in relevant_ids for note_id in retrieved_ids)

    return relevant_count / k


def recall_at_k(results, relevant_ids, k):
    if k <= 0 or not relevant_ids:
        return 0.0

    retrieved_ids = [note[0] for note, _ in results[:k]]

    relevant_count = sum(note_id in relevant_ids for note_id in retrieved_ids)

    return relevant_count / len(relevant_ids)


def evaluate_method(name, search_function):
    p1_scores = []
    r3_scores = []

    print(f"\n=== {name} ===")

    for case in BENCHMARK_CASES:
        query = case["query"]
        relevant_ids = case["relevant_ids"]

        results = search_function(
            SAMPLE_NOTES,
            query,
            limit=3,
        )

        p1 = precision_at_k(results, relevant_ids, 1)
        r3 = recall_at_k(results, relevant_ids, 3)

        p1_scores.append(p1)
        r3_scores.append(r3)

        if results:
            top_note = results[0][0]
            top_title = top_note[1]
            top_score = results[0][1]
        else:
            top_title = "(tidak ada hasil)"
            top_score = 0.0

        print(
            f"Query: {query[:42]:42} "
            f"| Top: {top_title:24} "
            f"| Score: {top_score:.6f} "
            f"| P@1: {p1:.2f} "
            f"| R@3: {r3:.2f}"
        )

    total = len(BENCHMARK_CASES)

    print("\nRingkasan:")
    print(f"Precision@1: {sum(p1_scores) / total:.3f}")
    print(f"Recall@3   : {sum(r3_scores) / total:.3f}")


def inspect_negative_queries(name, search_function):
    print(f"\n=== Query negatif: {name} ===")

    for query in NEGATIVE_QUERIES:
        results = search_function(
            SAMPLE_NOTES,
            query,
            limit=3,
        )

        print(f"\nQuery: {query!r}")

        if not results:
            print("Tidak ada hasil.")
            continue

        for note, score in results:
            print(f"- {note[1]:24} | Skor: {score:.3f}")


def evaluate_partial_queries(name, search_function):
    print(f"\n=== Partial Query: {name} ===")

    for case in PARTIAL_QUERY_CASES:
        query = case["query"]
        relevant_ids = case["relevant_ids"]

        results = search_function(
            SAMPLE_NOTES,
            query,
            limit=3,
        )

        p1 = precision_at_k(results, relevant_ids, 1)
        r3 = recall_at_k(results, relevant_ids, 3)

        if results:
            top_title = results[0][0][1]
            score = results[0][1]
        else:
            top_title = "(tidak ada hasil)"
            score = 0.0

        print(
            f"Query: {query:10} "
            f"| Top: {top_title:24} "
            f"| Score: {score:.6f} "
            f"| P@1: {p1:.2f} "
            f"| R@3: {r3:.2f}"
        )


if __name__ == "__main__":
    methods = [
        ("Word TF-IDF", rank_notes),
        ("Character TF-IDF", rank_notes_char),
        ("Semantic Search", rank_notes_semantic),
        ("Hybrid Search", rank_notes_hybrid),
    ]

    for name, search_function in methods:
        evaluate_method(name, search_function)
        inspect_negative_queries(name, search_function)
        evaluate_partial_queries(name, search_function)
