import pytest

from hybrid_search import (
    is_partial_query,
    rank_notes_hybrid,
    weighted_reciprocal_rank_fusion,
)

SAMPLE_NOTES = [
    (
        1,
        "Supervised Learning",
        "Machine Learning",
        "Pembelajaran menggunakan kumpulan data "
        "yang sudah diberi label untuk memprediksi keluaran.",
    ),
    (
        2,
        "Unsupervised Learning",
        "Machine Learning",
        "Algoritma mencari kelompok atau struktur "
        "tersembunyi dari data yang belum memiliki label.",
    ),
]


@pytest.mark.parametrize(
    "query",
    ["super", "superv", "supervis", "vised"],
)
def test_detects_partial_query(query):
    assert is_partial_query(SAMPLE_NOTES, query)


def test_exact_word_is_not_partial_query():
    assert not is_partial_query(
        SAMPLE_NOTES,
        "supervised",
    )


def test_sentence_is_not_partial_query():
    assert not is_partial_query(
        SAMPLE_NOTES,
        "metode belajar mesin",
    )


def test_short_query_is_not_partial_query():
    assert not is_partial_query(
        SAMPLE_NOTES,
        "su",
    )


@pytest.mark.parametrize(
    "query",
    ["super", "superv", "supervis", "vised"],
)
def test_hybrid_finds_partial_query(query):
    results = rank_notes_hybrid(
        SAMPLE_NOTES,
        query,
        limit=3,
    )

    retrieved_ids = {note[0] for note, score in results}

    assert 1 in retrieved_ids


def test_weighted_rrf_prioritizes_higher_weight():
    note_a = (
        1,
        "Document A",
        "Test",
        "Content A",
    )

    note_b = (
        2,
        "Document B",
        "Test",
        "Content B",
    )

    char_results = [
        (note_a, 0.9),
        (note_b, 0.8),
    ]

    semantic_results = [
        (note_b, 0.9),
        (note_a, 0.8),
    ]

    results = weighted_reciprocal_rank_fusion(
        [char_results, semantic_results],
        weights=[0.4, 0.6],
        limit=2,
    )

    assert results[0][0][0] == 2
    assert results[1][0][0] == 1


def test_hybrid_normal_query_uses_weighted_ranking():
    results = rank_notes_hybrid(
        SAMPLE_NOTES,
        "metode belajar mesin dengan contoh yang memiliki jawaban",
        limit=3,
    )

    assert results
    assert results[0][0][0] == 1
