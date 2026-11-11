import pytest

from benchmark.dataset import (
    POSITIVE_CASES,
    PARTIAL_QUERY_CASES,
    NEGATIVE_CASES,
)

from benchmark.run_benchmark import (
    run_benchmark,
    print_report,
)

NOTE_1 = (1, "Supervised Learning", "ML", "Labeled data")


def fake_search(notes, query, limit=3):
    return [(NOTE_1, 0.9)][:limit]


def test_run_benchmark_with_custom_method():
    reports = run_benchmark(
        k=3,
        methods={
            "Fake Search": fake_search,
        },
    )

    assert "Fake Search" in reports

    report = reports["Fake Search"]

    assert report["positive"]["total_queries"] == len(POSITIVE_CASES)

    assert report["partial"]["total_queries"] == len(PARTIAL_QUERY_CASES)

    assert report["negative"]["total_queries"] == len(NEGATIVE_CASES)


def test_run_benchmark_rejects_invalid_k():
    with pytest.raises(ValueError):
        run_benchmark(
            k=0,
            methods={"Fake Search": fake_search},
        )


def test_run_benchmark_rejects_empty_methods():
    with pytest.raises(ValueError):
        run_benchmark(
            k=3,
            methods={},
        )


def test_print_report():
    reports = run_benchmark(
        k=3,
        methods={
            "Fake Search": fake_search,
        },
    )

    # Memastikan laporan bisa ditampilkan tanpa error.
    print_report(reports, k=3)
