"""
Unified evaluation engine for Poorcone Lab.

Menghubungkan benchmark dataset dengan evaluation metrics
agar semua metode pencarian diuji menggunakan prosedur sama.
"""

from collections.abc import Callable, Sequence
from typing import Any

from benchmark.metrics import (
    precision_at_k,
    recall_at_k,
    reciprocal_rank_at_k,
    false_positive_rate,
    no_result_accuracy,
)


SearchFunction = Callable[..., Sequence]


# ============================================================
# 1. EVALUATE POSITIVE / PARTIAL QUERIES
# ============================================================


def evaluate_cases(
    search_function: SearchFunction,
    notes: Sequence,
    cases: Sequence[dict[str, Any]],
    k: int = 3,
) -> dict[str, Any]:
    """
    Mengevaluasi query yang memiliki dokumen relevan.

    Menghasilkan:
    - Precision@1
    - Precision@K
    - Recall@K
    - MRR@K
    - Detail hasil setiap query
    """
    if k <= 0:
        raise ValueError("K harus lebih besar dari 0.")

    if not cases:
        raise ValueError("Dataset evaluasi tidak boleh kosong.")

    p1_scores = []
    pk_scores = []
    recall_scores = []
    reciprocal_ranks = []

    details = []

    for case in cases:
        query = case["query"]
        relevant_ids = case["relevant_ids"]

        results = search_function(
            notes,
            query,
            limit=k,
        )

        p1 = precision_at_k(
            results,
            relevant_ids,
            1,
        )

        pk = precision_at_k(
            results,
            relevant_ids,
            k,
        )

        rk = recall_at_k(
            results,
            relevant_ids,
            k,
        )

        rr = reciprocal_rank_at_k(
            results,
            relevant_ids,
            k,
        )

        p1_scores.append(p1)
        pk_scores.append(pk)
        recall_scores.append(rk)
        reciprocal_ranks.append(rr)

        top_title = results[0][0][1] if results else "(tidak ada hasil)"

        details.append(
            {
                "query": query,
                "top_title": top_title,
                "result_count": len(results),
                "precision_at_1": p1,
                "precision_at_k": pk,
                "recall_at_k": rk,
                "reciprocal_rank_at_k": rr,
            }
        )

    total = len(cases)

    return {
        "total_queries": total,
        "precision_at_1": sum(p1_scores) / total,
        "precision_at_k": sum(pk_scores) / total,
        "recall_at_k": sum(recall_scores) / total,
        "mrr_at_k": sum(reciprocal_ranks) / total,
        "details": details,
    }


# ============================================================
# 2. EVALUATE NEGATIVE QUERIES
# ============================================================


def evaluate_negative_cases(
    search_function: SearchFunction,
    notes: Sequence,
    cases: Sequence[dict[str, Any]],
    k: int = 3,
) -> dict[str, Any]:
    """
    Mengevaluasi query yang tidak memiliki dokumen relevan.

    Menghasilkan:
    - False Positive Rate
    - No-result Accuracy
    - Detail hasil setiap query negatif
    """
    if k <= 0:
        raise ValueError("K harus lebih besar dari 0.")

    if not cases:
        raise ValueError("Dataset negatif tidak boleh kosong.")

    negative_result_sets = []
    details = []

    for case in cases:
        query = case["query"]

        results = search_function(
            notes,
            query,
            limit=k,
        )

        negative_result_sets.append(results)

        details.append(
            {
                "query": query,
                "result_count": len(results),
                "is_false_positive": bool(results),
                "top_title": (results[0][0][1] if results else "(tidak ada hasil)"),
            }
        )

    total = len(cases)

    fpr = false_positive_rate(negative_result_sets)
    no_result = no_result_accuracy(negative_result_sets)

    false_positive_count = sum(detail["is_false_positive"] for detail in details)

    return {
        "total_queries": total,
        "false_positive_count": false_positive_count,
        "no_result_count": total - false_positive_count,
        "false_positive_rate": fpr,
        "no_result_accuracy": no_result,
        "details": details,
    }


# ============================================================
# 3. UNIFIED METHOD EVALUATION
# ============================================================


def evaluate_search_method(
    search_function: SearchFunction,
    notes: Sequence,
    positive_cases: Sequence[dict[str, Any]],
    partial_cases: Sequence[dict[str, Any]],
    negative_cases: Sequence[dict[str, Any]],
    k: int = 3,
) -> dict[str, Any]:
    """
    Mengevaluasi satu metode pencarian menggunakan
    seluruh kelompok benchmark.
    """

    # Evaluasi seluruh positive queries.
    positive = evaluate_cases(
        search_function,
        notes,
        positive_cases,
        k,
    )

    # Evaluasi positive queries berdasarkan kategorinya.
    positive_by_kind = {}

    kinds = sorted({case["kind"] for case in positive_cases})

    for kind in kinds:
        filtered_cases = [case for case in positive_cases if case["kind"] == kind]

        positive_by_kind[kind] = evaluate_cases(
            search_function,
            notes,
            filtered_cases,
            k,
        )

    # Partial queries dievaluasi secara terpisah.
    partial = evaluate_cases(
        search_function,
        notes,
        partial_cases,
        k,
    )

    # Negative queries.
    negative = evaluate_negative_cases(
        search_function,
        notes,
        negative_cases,
        k,
    )

    return {
        "positive": positive,
        "positive_by_kind": positive_by_kind,
        "partial": partial,
        "negative": negative,
    }
