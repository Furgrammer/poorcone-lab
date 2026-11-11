"""
Evaluation metrics for Poorcone Lab Search.

Metrics:
- Precision@K
- Recall@K
- Reciprocal Rank@K
- Mean Reciprocal Rank@K (MRR@K)
- False Positive Rate
- No-result Accuracy
"""

from collections.abc import Sequence, Set as AbstractSet
from typing import TypeAlias


# ============================================================
# TYPE DEFINITIONS
# ============================================================

Note: TypeAlias = tuple[int, str, str, str]
SearchResult: TypeAlias = tuple[Note, float]
SearchResults: TypeAlias = Sequence[SearchResult]


# ============================================================
# INTERNAL HELPERS
# ============================================================


def _validate_k(k: int) -> None:
    """Pastikan nilai K merupakan bilangan positif."""
    if k <= 0:
        raise ValueError("K harus lebih besar dari 0.")


def _get_retrieved_ids(
    results: SearchResults,
    k: int,
) -> list[int]:
    """Ambil ID dokumen dari K hasil pencarian teratas."""
    return [note[0] for note, _ in results[:k]]


# ============================================================
# 1. PRECISION@K
# ============================================================


def precision_at_k(
    results: SearchResults,
    relevant_ids: AbstractSet[int],
    k: int,
) -> float:
    """
    Mengukur proporsi hasil relevan pada K posisi teratas.

    Jumlah pembagi tetap K, termasuk ketika hasil yang
    dikembalikan sistem kurang dari K.
    """
    _validate_k(k)

    retrieved_ids = _get_retrieved_ids(results, k)

    relevant_count = sum(note_id in relevant_ids for note_id in retrieved_ids)

    return relevant_count / k


# ============================================================
# 2. RECALL@K
# ============================================================


def recall_at_k(
    results: SearchResults,
    relevant_ids: AbstractSet[int],
    k: int,
) -> float:
    """
    Mengukur proporsi dokumen relevan yang ditemukan
    dalam K posisi teratas.
    """
    _validate_k(k)

    if not relevant_ids:
        return 0.0

    retrieved_ids = _get_retrieved_ids(results, k)

    relevant_count = sum(note_id in relevant_ids for note_id in retrieved_ids)

    return relevant_count / len(relevant_ids)


# ============================================================
# 3. RECIPROCAL RANK@K
# ============================================================


def reciprocal_rank_at_k(
    results: SearchResults,
    relevant_ids: AbstractSet[int],
    k: int,
) -> float:
    """
    Mengukur posisi hasil relevan pertama.

    Contoh:
    Rank 1 -> 1.00
    Rank 2 -> 0.50
    Rank 3 -> 0.33
    Tidak ditemukan -> 0.00
    """
    _validate_k(k)

    retrieved_ids = _get_retrieved_ids(results, k)

    for rank, note_id in enumerate(retrieved_ids, start=1):
        if note_id in relevant_ids:
            return 1.0 / rank

    return 0.0


# ============================================================
# 4. MEAN RECIPROCAL RANK@K
# ============================================================


def mean_reciprocal_rank_at_k(
    result_sets: Sequence[SearchResults],
    relevant_id_sets: Sequence[AbstractSet[int]],
    k: int,
) -> float:
    """
    Menghitung rata-rata Reciprocal Rank dari beberapa query.
    """
    _validate_k(k)

    if not result_sets:
        raise ValueError("Dataset evaluasi tidak boleh kosong.")

    if len(result_sets) != len(relevant_id_sets):
        raise ValueError("Jumlah hasil dan ground truth harus sama.")

    reciprocal_ranks = [
        reciprocal_rank_at_k(results, relevant_ids, k)
        for results, relevant_ids in zip(result_sets, relevant_id_sets)
    ]

    return sum(reciprocal_ranks) / len(reciprocal_ranks)


# ============================================================
# 5. FALSE POSITIVE RATE
# ============================================================


def false_positive_rate(
    negative_result_sets: Sequence[SearchResults],
) -> float:
    """
    Mengukur proporsi query negatif yang mengembalikan hasil.

    Jika query negatif menghasilkan minimal satu dokumen,
    query tersebut dihitung sebagai false positive.
    """
    if not negative_result_sets:
        raise ValueError("Query negatif tidak boleh kosong.")

    false_positives = sum(bool(results) for results in negative_result_sets)

    return false_positives / len(negative_result_sets)


# ============================================================
# 6. NO-RESULT ACCURACY
# ============================================================


def no_result_accuracy(
    negative_result_sets: Sequence[SearchResults],
) -> float:
    """
    Mengukur proporsi query negatif yang tidak menghasilkan
    dokumen apa pun.
    """
    if not negative_result_sets:
        raise ValueError("Query negatif tidak boleh kosong.")

    correct_no_results = sum(not results for results in negative_result_sets)

    return correct_no_results / len(negative_result_sets)
