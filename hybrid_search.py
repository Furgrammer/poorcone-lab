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
    k=60,
):
    """
    Weighted Reciprocal Rank Fusion.

    WRRF(d) = sum(weight_i / (k + rank_i(d)))

    Parameter:
    - result_lists: daftar hasil dari setiap metode.
    - weights: bobot masing-masing metode.
    - limit: jumlah hasil maksimal.
    - k: konstanta untuk mengontrol pengaruh ranking.
    """

    if limit <= 0:
        return []

    if k <= 0:
        raise ValueError("Nilai k harus lebih besar dari 0.")

    if len(result_lists) != len(weights):
        raise ValueError("Jumlah result_lists dan weights harus sama.")

    if any(weight < 0 for weight in weights):
        raise ValueError("Bobot tidak boleh negatif.")

    fused_scores = {}
    note_lookup = {}

    for results, weight in zip(result_lists, weights):
        for rank, (note, _) in enumerate(results, start=1):
            note_id = note[0]

            note_lookup[note_id] = note

            contribution = weight / (k + rank)

            fused_scores[note_id] = fused_scores.get(note_id, 0.0) + contribution

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
    char_min_score=0.18,
    rrf_k=60,
    partial_char_min_score=0.12,
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
            min_score=partial_char_min_score,
        )

    # ========================================================
    # 1. CHARACTER TF-IDF
    # ========================================================

    char_results = rank_notes_char(
        notes,
        query,
        limit=len(notes),
        min_score=char_min_score,
    )

    # ========================================================
    # 2. SEMANTIC SEARCH
    # ========================================================

    semantic_results = rank_notes_semantic(
        notes,
        query,
        limit=len(notes),
        min_score=semantic_min_score,
    )

    # ========================================================
    # 3. CANDIDATE INTERSECTION
    # ========================================================

    char_ids = {note[0] for note, _ in char_results}

    semantic_ids = {note[0] for note, _ in semantic_results}

    # Hanya dokumen yang ditemukan kedua metode.
    candidate_ids = char_ids & semantic_ids

    # Tidak ada kandidat yang didukung kedua metode.
    if not candidate_ids:
        return []

    filtered_char_results = [
        result for result in char_results if result[0][0] in candidate_ids
    ]

    filtered_semantic_results = [
        result for result in semantic_results if result[0][0] in candidate_ids
    ]

    # ========================================================
    # 4. WEIGHTED RECIPROCAL RANK FUSION
    # ========================================================

    fused_results = weighted_reciprocal_rank_fusion(
        [
            filtered_char_results,
            filtered_semantic_results,
        ],
        weights=[0.4, 0.6],
        limit=len(notes),
        k=rrf_k,
    )

    # ========================================================
    # 5. SEMANTIC SCORE AS TIE-BREAKER
    # ========================================================

    semantic_scores = {note[0]: score for note, score in filtered_semantic_results}

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
