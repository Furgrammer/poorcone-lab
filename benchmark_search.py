
from search import rank_notes, rank_notes_char


SAMPLE_NOTES = [
    (
        1,
        "Supervised Learning",
        "Machine Learning",
        "Supervised learning uses labeled data to predict outcomes.",
    ),
    (
        2,
        "Unsupervised Learning",
        "Machine Learning",
        "Unsupervised learning finds patterns in unlabeled data.",
    ),
    (
        3,
        "Player Movement",
        "Game Development",
        "Pygame moves a player with keyboard controls.",
    ),
    (
        4,
        "TF-IDF Search",
        "AI",
        "TF-IDF represents text using term frequency and inverse document frequency.",
    ),
    (
        5,
        "Python Lists",
        "Python",
        "Lists store ordered collections of items in Python.",
    ),
]


# Ground truth: ID catatan yang dianggap relevan untuk setiap query.
# Query parsial "supervis" dan "super" relevan dengan catatan 1 dan 2.
POSITIVE_CASES = [
    {"query": "supervised learning", "relevant_ids": {1}},
    {"query": "supervis", "relevant_ids": {1, 2}},
    {"query": "super", "relevant_ids": {1, 2}},
    {"query": "unlabeled data", "relevant_ids": {2}},
    {"query": "pygame keyboard", "relevant_ids": {3}},
    {"query": "inverse document frequency", "relevant_ids": {4}},
    {"query": "python lists", "relevant_ids": {5}},
    {"query": "pyth", "relevant_ids": {5}},
]


# Query ini sengaja dipilih karena tidak memiliki catatan relevan.
NEGATIVE_QUERIES = [
    "astronomi galaksi",
    "zebra teleportasi",
]


def precision_at_k(results, relevant_ids, k):
    """Proporsi hasil relevan dalam k posisi teratas."""
    if k <= 0:
        return 0.0

    retrieved_ids = [note[0] for note, _ in results[:k]]
    relevant_count = sum(
        note_id in relevant_ids for note_id in retrieved_ids
    )

    return relevant_count / k


def recall_at_k(results, relevant_ids, k):
    """Proporsi catatan relevan yang ditemukan dalam k posisi teratas."""
    if k <= 0 or not relevant_ids:
        return 0.0

    retrieved_ids = [note[0] for note, _ in results[:k]]
    relevant_count = sum(
        note_id in relevant_ids for note_id in retrieved_ids
    )

    return relevant_count / len(relevant_ids)


def evaluate_method(name, search_function):
    p1_scores = []
    p3_scores = []
    r3_scores = []

    print(f"\n=== {name} ===")

    for case in POSITIVE_CASES:
        query = case["query"]
        relevant_ids = case["relevant_ids"]

        results = search_function(SAMPLE_NOTES, query, limit=3)

        p1 = precision_at_k(results, relevant_ids, 1)
        p3 = precision_at_k(results, relevant_ids, 3)
        r3 = recall_at_k(results, relevant_ids, 3)

        p1_scores.append(p1)
        p3_scores.append(p3)
        r3_scores.append(r3)

        top_title = results[0][0][1] if results else "(tidak ada hasil)"

        print(
            f"{query!r:32} | "
            f"Top: {top_title:24} | "
            f"P@1: {p1:.2f} | "
            f"P@3: {p3:.2f} | "
            f"R@3: {r3:.2f}"
        )

    total = len(POSITIVE_CASES)

    print("\nRingkasan query positif:")
    print(f"Rata-rata Precision@1: {sum(p1_scores) / total:.3f}")
    print(f"Rata-rata Precision@3: {sum(p3_scores) / total:.3f}")
    print(f"Rata-rata Recall@3   : {sum(r3_scores) / total:.3f}")

    false_positives = 0

    print("\nQuery negatif:")
    for query in NEGATIVE_QUERIES:
        results = search_function(SAMPLE_NOTES, query, limit=3)

        if results:
            false_positives += 1
            titles = ", ".join(note[1] for note, _ in results)
            print(f"{query!r} -> HASIL TIDAK RELEVAN: {titles}")
        else:
            print(f"{query!r} -> Tidak ada hasil")

    false_positive_rate = false_positives / len(NEGATIVE_QUERIES)

    print(
        "False-positive rate: "
        f"{false_positives}/{len(NEGATIVE_QUERIES)} "
        f"= {false_positive_rate:.3f}"
    )


if __name__ == "__main__":
    evaluate_method("Word TF-IDF (baseline)", rank_notes)
    evaluate_method("Character TF-IDF", rank_notes_char)
