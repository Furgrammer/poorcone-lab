import pytest

import hybrid_search


NOTE_1 = (1, "Supervised Learning", "ML", "Labeled data")
NOTE_2 = (2, "Python Lists", "Python", "Ordered items")
NOTE_3 = (3, "TF-IDF Search", "AI", "Document weighting")


def test_weighted_rrf_uses_k():
    result_lists = [
        [
            (NOTE_1, 0.9),
            (NOTE_2, 0.8),
        ],
        [
            (NOTE_2, 0.95),
            (NOTE_1, 0.7),
        ],
    ]

    result = hybrid_search.weighted_reciprocal_rank_fusion(
        result_lists,
        weights=[0.4, 0.6],
        limit=2,
        k=60,
    )

    scores = {note[0]: score for note, score in result}

    expected_note_1 = 0.4 / 61 + 0.6 / 62
    expected_note_2 = 0.4 / 62 + 0.6 / 61

    assert scores[1] == pytest.approx(expected_note_1)
    assert scores[2] == pytest.approx(expected_note_2)

    # NOTE_2 memiliki kontribusi ranking lebih besar.
    assert result[0][0][0] == 2


def test_weighted_rrf_rejects_invalid_k():
    with pytest.raises(ValueError):
        hybrid_search.weighted_reciprocal_rank_fusion(
            [],
            weights=[],
            k=0,
        )


def test_hybrid_returns_only_intersection(monkeypatch):
    monkeypatch.setattr(
        hybrid_search,
        "is_partial_query",
        lambda notes, query: False,
    )

    monkeypatch.setattr(
        hybrid_search,
        "rank_notes_char",
        lambda *args, **kwargs: [
            (NOTE_1, 0.9),
            (NOTE_2, 0.8),
        ],
    )

    monkeypatch.setattr(
        hybrid_search,
        "rank_notes_semantic",
        lambda *args, **kwargs: [
            (NOTE_2, 0.95),
            (NOTE_3, 0.7),
        ],
    )

    result = hybrid_search.rank_notes_hybrid(
        [NOTE_1, NOTE_2, NOTE_3],
        "sample query",
    )

    result_ids = {note[0] for note, score in result}

    assert result_ids == {2}


def test_hybrid_returns_empty_without_intersection(monkeypatch):
    monkeypatch.setattr(
        hybrid_search,
        "is_partial_query",
        lambda notes, query: False,
    )

    monkeypatch.setattr(
        hybrid_search,
        "rank_notes_char",
        lambda *args, **kwargs: [
            (NOTE_1, 0.9),
        ],
    )

    monkeypatch.setattr(
        hybrid_search,
        "rank_notes_semantic",
        lambda *args, **kwargs: [
            (NOTE_2, 0.8),
        ],
    )

    result = hybrid_search.rank_notes_hybrid(
        [NOTE_1, NOTE_2],
        "sample query",
    )

    assert result == []


def test_partial_query_uses_character_search(monkeypatch):
    monkeypatch.setattr(
        hybrid_search,
        "is_partial_query",
        lambda notes, query: True,
    )

    expected_results = [
        (NOTE_1, 0.9),
    ]

    def fake_char_search(notes, query, limit=10, min_score=0.0):
        return expected_results[:limit]

    def unexpected_semantic_search(*args, **kwargs):
        raise AssertionError(
            "Semantic Search tidak boleh dipanggil untuk partial query."
        )

    monkeypatch.setattr(
        hybrid_search,
        "rank_notes_char",
        fake_char_search,
    )

    monkeypatch.setattr(
        hybrid_search,
        "rank_notes_semantic",
        unexpected_semantic_search,
    )

    result = hybrid_search.rank_notes_hybrid(
        [NOTE_1],
        "super",
    )

    assert result == expected_results
