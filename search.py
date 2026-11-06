from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


def _rank_with_vectorizer(
    notes,
    query,
    limit,
    vectorizer,
    min_score=0.0,
):
    """Mengurutkan catatan dan menyaring skor di bawah ambang."""
    if not query.strip() or not notes or limit <= 0:
        return []

    documents = [
        f"{title} {category} {content}" for _, title, category, content in notes
    ]

    try:
        document_vectors = vectorizer.fit_transform(documents)
        query_vector = vectorizer.transform([query])
    except ValueError:
        return []

    scores = cosine_similarity(query_vector, document_vectors).flatten()

    results = [
        (note, float(score))
        for note, score in zip(notes, scores)
        if score > 0 and score >= min_score
    ]

    results.sort(key=lambda item: item[1], reverse=True)
    return results[:limit]


def rank_notes(notes, query, limit=10):
    """Baseline: TF-IDF berbasis kata."""
    vectorizer = TfidfVectorizer(ngram_range=(1, 2))

    return _rank_with_vectorizer(notes, query, limit, vectorizer)


def rank_notes_char(notes, query, limit=10, min_score=0.12):
    """Eksperimen: TF-IDF karakter dengan ambang skor."""
    vectorizer = TfidfVectorizer(
        analyzer="char_wb",
        ngram_range=(3, 5),
    )

    return _rank_with_vectorizer(
        notes,
        query,
        limit,
        vectorizer,
        min_score=min_score,
    )
