import pytest

from benchmark.metrics import (
    precision_at_k,
    recall_at_k,
    reciprocal_rank_at_k,
    mean_reciprocal_rank_at_k,
    false_positive_rate,
    no_result_accuracy,
)


# Sample notes
NOTE_1 = (1, "Supervised Learning", "ML", "Labeled data")
NOTE_2 = (2, "Python Lists", "Python", "Ordered collection")
NOTE_3 = (3, "TF-IDF Search", "AI", "Document weighting")

# Search results: (note, score)
RESULTS = [
    (NOTE_2, 0.90),
    (NOTE_1, 0.80),
    (NOTE_3, 0.70),
]


def test_precision_at_k():
    result = precision_at_k(
        RESULTS,
        {1},
        3,
    )

    assert result == pytest.approx(1 / 3)


def test_recall_at_k():
    result = recall_at_k(
        RESULTS,
        {1, 3},
        2,
    )

    assert result == pytest.approx(0.5)


def test_recall_with_empty_relevant_ids():
    result = recall_at_k(
        RESULTS,
        set(),
        3,
    )

    assert result == 0.0


def test_reciprocal_rank_at_k():
    result = reciprocal_rank_at_k(
        RESULTS,
        {1},
        3,
    )

    assert result == pytest.approx(0.5)


def test_reciprocal_rank_not_found():
    result = reciprocal_rank_at_k(
        RESULTS,
        {99},
        3,
    )

    assert result == 0.0


def test_mean_reciprocal_rank_at_k():
    result_sets = [
        RESULTS,
        RESULTS[1:],
    ]

    relevant_id_sets = [
        {2},
        {1},
    ]

    result = mean_reciprocal_rank_at_k(
        result_sets,
        relevant_id_sets,
        3,
    )

    # Query pertama: RR = 1.0
    # Query kedua: RR = 1.0
    assert result == pytest.approx(1.0)


def test_false_positive_rate():
    negative_results = [
        [RESULTS[0]],
        [],
        [RESULTS[1]],
        [],
    ]

    result = false_positive_rate(negative_results)

    assert result == pytest.approx(0.5)


def test_no_result_accuracy():
    negative_results = [
        [RESULTS[0]],
        [],
        [RESULTS[1]],
        [],
    ]

    result = no_result_accuracy(negative_results)

    assert result == pytest.approx(0.5)


def test_invalid_k():
    with pytest.raises(ValueError):
        precision_at_k(RESULTS, {1}, 0)


def test_empty_negative_dataset():
    with pytest.raises(ValueError):
        false_positive_rate([])
