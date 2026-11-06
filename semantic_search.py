from functools import lru_cache

from sentence_transformers import SentenceTransformer


MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"


@lru_cache(maxsize=1)
def get_model():
    """Memuat model satu kali selama proses Python berjalan."""
    return SentenceTransformer(
        MODEL_NAME,
        device="cpu",
    )


@lru_cache(maxsize=4)
def encode_documents(documents: tuple[str, ...]):
    """Mengubah seluruh dokumen menjadi embeddings."""
    model = get_model()

    embeddings = model.encode(
        list(documents),
        convert_to_numpy=True,
        normalize_embeddings=True,
        show_progress_bar=False,
    )

    return embeddings


def rank_notes_semantic(
    notes,
    query,
    limit=10,
    min_score=0.20,
):
    """
    Mengurutkan catatan berdasarkan kemiripan makna.

    notes:
        Daftar tuple (id, title, category, content)

    query:
        Pertanyaan atau kata kunci pengguna.

    limit:
        Jumlah maksimum hasil.
    """
    if not query.strip() or not notes or limit <= 0:
        return []

    documents = tuple(
        f"{title}. {category}. {content}" for _, title, category, content in notes
    )

    model = get_model()

    # Embedding dokumen di-cache agar tidak dihitung ulang
    # setiap kali pengguna melakukan pencarian.
    document_embeddings = encode_documents(documents)

    # Query diubah menjadi embedding.
    query_embedding = model.encode(
        query,
        convert_to_numpy=True,
        normalize_embeddings=True,
        show_progress_bar=False,
    )

    # Karena kedua embedding sudah dinormalisasi,
    # dot product sama dengan cosine similarity.
    scores = document_embeddings @ query_embedding

    results = [
        (note, float(score)) for note, score in zip(notes, scores) if score >= min_score
    ]

    results.sort(
        key=lambda item: item[1],
        reverse=True,
    )

    return results[:limit]
