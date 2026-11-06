import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from search import rank_notes, rank_notes_char


SAMPLE_NOTES = [
    (
        1,
        "Supervised Learning",
        "Machine Learning",
        "Belajar dari data berlabel untuk memprediksi target.",
    ),
    (
        2,
        "Unsupervised Learning",
        "Machine Learning",
        "Menemukan pola pada data tanpa label.",
    ),
    (
        3,
        "Player Movement",
        "Game Development",
        "Menggerakkan player menggunakan Pygame dan keyboard.",
    ),
]


def test_relevant_note_ranks_first():
    results = rank_notes(
        SAMPLE_NOTES,
        "supervised learning data berlabel",
    )

    assert results
    assert results[0][0][0] == 1
    assert results[0][1] > 0


def test_unrelated_query_returns_no_results():
    results = rank_notes(
        SAMPLE_NOTES,
        "astronomi galaksi",
    )

    assert results == []


def test_empty_query_returns_no_results():
    results = rank_notes(SAMPLE_NOTES, "   ")

    assert results == []


def test_limit_controls_number_of_results():
    results = rank_notes(
        SAMPLE_NOTES,
        "machine learning",
        limit=1,
    )

    assert len(results) <= 1


def test_character_search_finds_partial_word():
    results = rank_notes_char(SAMPLE_NOTES, "supervis")

    assert results
    assert results[0][0][0] == 1


def test_character_search_filters_unrelated_query():
    results = rank_notes_char(SAMPLE_NOTES, "astronomi galaksi")

    assert results == []
