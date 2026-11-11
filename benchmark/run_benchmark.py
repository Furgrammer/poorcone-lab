"""
Unified benchmark runner for Poorcone Lab.

Menjalankan seluruh metode pencarian menggunakan
dataset dan evaluation engine yang sama.
"""

from collections.abc import Callable, Mapping, Sequence
from typing import Any

from benchmark.dataset import (
    SAMPLE_NOTES,
    POSITIVE_CASES,
    PARTIAL_QUERY_CASES,
    NEGATIVE_CASES,
)
from benchmark.evaluator import evaluate_search_method


SearchFunction = Callable[..., Sequence]


# ============================================================
# 1. SEARCH METHOD REGISTRY
# ============================================================


def get_search_methods() -> dict[str, SearchFunction]:
    """
    Mengambil seluruh metode pencarian yang akan dievaluasi.

    Import dilakukan di dalam fungsi agar metode yang tidak
    digunakan tidak perlu dimuat saat modul benchmark di-import.
    """

    from search import rank_notes, rank_notes_char
    from semantic_search import rank_notes_semantic
    from hybrid_search import rank_notes_hybrid

    return {
        "Word TF-IDF": rank_notes,
        "Character TF-IDF": rank_notes_char,
        "Semantic Search": rank_notes_semantic,
        "Hybrid Search": rank_notes_hybrid,
    }


# ============================================================
# 2. RUN BENCHMARK
# ============================================================


def run_benchmark(
    k: int = 3,
    methods: Mapping[str, SearchFunction] | None = None,
) -> dict[str, dict[str, Any]]:
    """
    Menjalankan evaluasi seluruh metode pencarian.

    Parameter:
    - k: jumlah hasil teratas yang dievaluasi.
    - methods: metode pencarian yang digunakan.
      Jika None, gunakan seluruh metode default.

    Return:
    - Dictionary berisi hasil evaluasi setiap metode.
    """

    if k <= 0:
        raise ValueError("K harus lebih besar dari 0.")

    selected_methods = get_search_methods() if methods is None else dict(methods)

    if not selected_methods:
        raise ValueError("Minimal satu metode pencarian diperlukan.")

    reports = {}

    print("Starting Poorcone Lab Search Benchmark...")
    print(f"Sample notes : {len(SAMPLE_NOTES)}")
    print(f"Positive     : {len(POSITIVE_CASES)}")
    print(f"Partial      : {len(PARTIAL_QUERY_CASES)}")
    print(f"Negative     : {len(NEGATIVE_CASES)}")
    print(f"K            : {k}")

    for name, search_function in selected_methods.items():
        print(f"\nEvaluating: {name}")

        reports[name] = evaluate_search_method(
            search_function=search_function,
            notes=SAMPLE_NOTES,
            positive_cases=POSITIVE_CASES,
            partial_cases=PARTIAL_QUERY_CASES,
            negative_cases=NEGATIVE_CASES,
            k=k,
        )

    return reports


# ============================================================
# 3. PRINT SUMMARY REPORT
# ============================================================


def print_report(
    reports: Mapping[str, dict[str, Any]],
    k: int = 3,
) -> None:
    """Menampilkan ringkasan hasil benchmark."""

    if not reports:
        raise ValueError("Tidak ada hasil benchmark untuk ditampilkan.")

    print("\n" + "=" * 105)
    print("POORCONE LAB - SEARCH BENCHMARK REPORT")
    print("=" * 105)

    print(
        f"{'Method':<22}"
        f"{'P@1':>8}"
        f"{f'P@{k}':>8}"
        f"{f'R@{k}':>8}"
        f"{f'MRR@{k}':>9}"
        f"{'Part P@1':>11}"
        f"{'Part R@K':>11}"
        f"{'FPR':>8}"
        f"{'No-result':>11}"
    )

    print("-" * 105)

    for name, report in reports.items():
        positive = report["positive"]
        partial = report["partial"]
        negative = report["negative"]

        print(
            f"{name:<22}"
            f"{positive['precision_at_1']:>8.3f}"
            f"{positive['precision_at_k']:>8.3f}"
            f"{positive['recall_at_k']:>8.3f}"
            f"{positive['mrr_at_k']:>9.3f}"
            f"{partial['precision_at_1']:>11.3f}"
            f"{partial['recall_at_k']:>11.3f}"
            f"{negative['false_positive_rate']:>8.3f}"
            f"{negative['no_result_accuracy']:>11.3f}"
        )

    print("-" * 105)

    # --------------------------------------------------------
    # Positive query breakdown
    # --------------------------------------------------------

    print("\nPOSITIVE QUERY BREAKDOWN")

    for name, report in reports.items():
        print(f"\n{name}")

        for kind, metrics in report["positive_by_kind"].items():
            print(
                f"  {kind:<14}"
                f"P@1: {metrics['precision_at_1']:.3f} | "
                f"P@{k}: {metrics['precision_at_k']:.3f} | "
                f"R@{k}: {metrics['recall_at_k']:.3f} | "
                f"MRR@{k}: {metrics['mrr_at_k']:.3f}"
            )

    print("\nBenchmark completed.")


# ============================================================
# 4. MAIN ENTRY POINT
# ============================================================


def main() -> None:
    """Entry point untuk menjalankan benchmark."""

    k = 3

    reports = run_benchmark(k=k)

    print_report(
        reports=reports,
        k=k,
    )


if __name__ == "__main__":
    main()
