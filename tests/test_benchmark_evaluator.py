import pytest

from benchmark.evaluator import (
    evaluate_cases,
    evaluate_negative_cases,
    evaluate_search_method,
)


NOTE_1 = (1, "Supervised Learning", "ML", "Labeled data")
NOTE_2 = (2, "Python Lists", "Python", "Ordered items")


def fake_search(notes, query, limit=3):
    data = {
        "query_one": [
            (NOTE_1, 0.9),
            (NOTE_2, 0.8),
        ],
        "query_two": [
            (NOTE_2, 0.9),
        ],
        "negative_hit": [
            (NOTE_1, 0.9),
        ],
        "negative_empty": [],
    }

    return data.get(query, [])[:limit]


def test_evaluate_cases():
    cases = [
        {
            "query": "query_one",
            "relevant_ids": {1},
            "kind": "keyword",
        },
        {
            "query": "query_two",
            "relevant_ids": {2},
            "kind": "semantic",
        },
    ]

    result = evaluate_cases(
        fake_search,
        [NOTE_1, NOTE_2],
        cases,
        k=3,
    )

    assert result["total_queries"] == 2
    assert result["precision_at_1"] == pytest.approx(1.0)
    assert result["recall_at_k"] == pytest.approx(1.0)
    assert result["mrr_at_k"] == pytest.approx(1.0)


def test_evaluate_negative_cases():
    cases = [
        {"query": "negative_hit", "relevant_ids": set()},
        {"query": "negative_empty", "relevant_ids": set()},
    ]

    result = evaluate_negative_cases(
        fake_search,
        [NOTE_1, NOTE_2],
        cases,
        k=3,
    )

    assert result["total_queries"] == 2
    assert result["false_positive_count"] == 1
    assert result["false_positive_rate"] == pytest.approx(0.5)
    assert result["no_result_accuracy"] == pytest.approx(0.5)


def test_evaluate_search_method():
    positive_cases = [
        {
            "query": "query_one",
            "relevant_ids": {1},
            "kind": "keyword",
        },
    ]

    partial_cases = [
        {
            "query": "query_two",
            "relevant_ids": {2},
            "kind": "partial",
        },
    ]

    negative_cases = [
        {
            "query": "negative_empty",
            "relevant_ids": set(),
            "kind": "out_of_domain",
        },
    ]

    result = evaluate_search_method(
        fake_search,
        [NOTE_1, NOTE_2],
        positive_cases,
        partial_cases,
        negative_cases,
        k=3,
    )

    assert result["positive"]["total_queries"] == 1
    assert result["partial"]["total_queries"] == 1
    assert result["negative"]["total_queries"] == 1
    assert "keyword" in result["positive_by_kind"]


def test_evaluate_cases_rejects_empty_dataset():
    with pytest.raises(ValueError):
        evaluate_cases(fake_search, [NOTE_1], [], k=3)


def test_evaluate_cases_rejects_invalid_k():
    with pytest.raises(ValueError):
        evaluate_cases(
            fake_search,
            [NOTE_1],
            [{"query": "query_one", "relevant_ids": {1}}],
            k=0,
        )
