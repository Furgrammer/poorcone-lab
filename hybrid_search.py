import re

from search import rank_notes_char
from semantic_search import rank_notes_semantic


def reciprocal_rank_fusion(result_lists, limit=10, k=60):
    """
    Menggabungkan hasil pencarian berdasarkan peringkat
    menggunakan Reciprocal Rank Fusion.
    """
    if limit <= 0 or k <= 0:
        return []

    fused_scores = {}
    note_lookup = {}

    for results in result_lists:
        for rank, (note, _) in enumerate(results, start=1):
            note_id = note[0]

            note_lookup[note_id] = note

            fused_scores[note_id] = fused_scores.get(note_id, 0.0) + 1 / (k + rank)

    ranked_ids = sorted(
        fused_scores,
        key=lambda note_id: fused_scores[note_id],
        reverse=True,
    )

    return [
        (note_lookup[note_id], fused_scores[note_id]) for note_id in ranked_ids[:limit]
    ]


def weighted_reciprocal_rank_fusion(
    result_lists,
    weights,
    limit=10,
):
    """
    Menggabungkan hasil pencarian berdasarkan peringkat
    dengan bobot berbeda untuk setiap metode.
    """
    if limit <= 0 or len(result_lists) != len(weights):
        return []

    if any(weight < 0 for weight in weights):
        raise ValueError("Bobot tidak boleh negatif.")

    fused_scores = {}
    note_lookup = {}

    for results, weight in zip(result_lists, weights):
        for rank, (note, _) in enumerate(results, start=1):
            note_id = note[0]

            note_lookup[note_id] = note

            fused_scores[note_id] = fused_scores.get(note_id, 0.0) + weight / rank

    ranked_ids = sorted(
        fused_scores,
        key=lambda note_id: fused_scores[note_id],
        reverse=True,
    )

    return [
        (note_lookup[note_id], fused_scores[note_id]) for note_id in ranked_ids[:limit]
    ]


def is_partial_query(notes, query):
    """
    Mendeteksi apakah query merupakan potongan
    dari sebuah kata di dalam dokumen.
    """
    normalized_query = query.casefold().strip()

    if len(normalized_query) < 3:
        return False

    if len(normalized_query.split()) != 1:
        return False

    all_tokens = []

    for _, title, category, content in notes:
        document = f"{title} {category} {content}".casefold()
        tokens = re.findall(r"\w+", document)

        all_tokens.extend(tokens)

    # Jika query merupakan kata utuh, bukan partial query.
    if normalized_query in all_tokens:
        return False

    # Periksa apakah query merupakan bagian dari token lain.
    return any(normalized_query in token for token in all_tokens)


def rank_notes_hybrid(
    notes,
    query,
    limit=10,
    semantic_min_score=0.20,
    char_min_score=0.12,
    rrf_k=60,
):
    """
    Hybrid Search:
    Character TF-IDF + Semantic Search + RRF.

    Semantic gate memastikan dokumen yang ditampilkan
    memenuhi minimum semantic similarity.
    """
    if not query.strip() or not notes or limit <= 0:
        return []

    # Gunakan Character TF-IDF untuk partial query.
    if is_partial_query(notes, query):
        return rank_notes_char(
            notes,
            query,
            limit=limit,
            min_score=char_min_score,
        )

    char_results = rank_notes_char(
        notes,
        query,
        limit=len(notes),
        min_score=char_min_score,
    )

    semantic_results = rank_notes_semantic(
        notes,
        query,
        limit=len(notes),
        min_score=semantic_min_score,
    )

    # ID dokumen yang lolos semantic threshold.
    semantic_ids = {note[0] for note, _ in semantic_results}

    # Filter hasil Character TF-IDF.
    filtered_char_results = [
        result for result in char_results if result[0][0] in semantic_ids
    ]

    fused_results = weighted_reciprocal_rank_fusion(
        [
            filtered_char_results,
            semantic_results,
        ],
        weights=[0.4, 0.6],
        limit=len(notes),
    )

    # Simpan semantic similarity sebagai tie-breaker.
    semantic_scores = {note[0]: score for note, score in semantic_results}

    # Urutkan berdasarkan Weighted RRF,
    # kemudian semantic similarity jika skor seri.
    fused_results.sort(
        key=lambda item: (
            item[1],
            semantic_scores.get(
                item[0][0],
                float("-inf"),
            ),
        ),
        reverse=True,
    )

    return fused_results[:limit]

    # Simpan semantic similarity setiap dokumen.
    semantic_scores = {note[0]: score for note, score in semantic_results}

    # Gunakan semantic similarity sebagai tie-breaker.
    fused_results.sort(
        key=lambda item: (
            item[1],
            semantic_scores.get(
                item[0][0],
                float("-inf"),
            ),
        ),
        reverse=True,
    )

    return fused_results[:limit]
