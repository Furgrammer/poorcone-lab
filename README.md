# Poorcone Lab

**An AI-powered personal knowledge management system with intelligent note retrieval.**

Poorcone Lab is a personal AI research and development project. Its current application helps users save, organize, update, delete, and retrieve notes through keyword-based, character-based, semantic, and hybrid search methods.

The project emphasizes practical implementation, measurable search quality, and maintainable Python code.

> **Project status:** Prototype v1. Core note-management workflows, search methods, benchmark evaluation, and automated tests are implemented. Search quality is still being evaluated and improved.

## Features

### Knowledge management

- **Create notes:** Save a note with a title, category, and content.
- **Read notes:** Browse saved notes and filter them by category.
- **Update notes:** Edit a note's title, category, and content.
- **Delete notes:** Remove notes from the local database.
- **Persistent storage:** Store notes in a local SQLite database.

### Intelligent search

Poorcone Lab provides four search methods:

1. **Word TF-IDF** — retrieves notes using word-level TF-IDF features. It is intended for keyword-oriented queries.
2. **Character TF-IDF** — uses character-level features to improve matching for incomplete words and partial queries.
3. **Semantic Search** — represents text with sentence embeddings from a multilingual Sentence Transformers model and retrieves notes based on semantic similarity.
4. **Adaptive Hybrid Search** — routes detected partial queries to Character TF-IDF. For regular queries, it combines Character TF-IDF and Semantic Search candidates, then ranks their intersection using Weighted Reciprocal Rank Fusion (WRRF).

The current Hybrid Search configuration uses:

| Parameter | Value | Purpose |
|---|---:|---|
| Character threshold (regular queries) | `0.18` | Minimum Character TF-IDF score for regular-query candidates |
| Semantic threshold | `0.20` | Minimum semantic score for regular-query candidates |
| Character threshold (partial queries) | `0.12` | Minimum Character TF-IDF score for partial-query retrieval |
| Character / semantic WRRF weights | `0.4 / 0.6` | Relative contribution of each ranking method |
| WRRF `k` | `60` | Ranking constant used by Weighted Reciprocal Rank Fusion |

These are the current experimental defaults, not universal relevance thresholds. Their behavior depends on the contents of the user's notes and the query distribution.

The Explore page also supports comparing Word TF-IDF and Character TF-IDF results for the same query.

## Technology Stack

- **Language:** Python
- **Environment and dependency management:** [uv](https://docs.astral.sh/uv/)
- **Application interface:** [Streamlit](https://streamlit.io/)
- **Local database:** SQLite
- **Keyword and character retrieval:** scikit-learn
- **Semantic retrieval:** Sentence Transformers and PyTorch (CPU)
- **Automated testing:** pytest

## Getting Started

### Prerequisites

- Python version compatible with the project requirement (`>=3.13`); the repository's `.python-version` file specifies the selected development version.
- [uv](https://docs.astral.sh/uv/getting-started/installation/)
- Linux, Ubuntu on WSL 2, or another environment supported by the project dependencies.

### 1. Open the project directory

After cloning the repository, change into its root directory:

```bash
cd poorcone-lab
```

### 2. Install dependencies

```bash
uv sync --locked
```

This creates or updates the project virtual environment and installs the dependency versions recorded in `uv.lock`, including the CPU build of PyTorch configured by the project.

### 3. Run the application

```bash
uv run streamlit run app.py
```

Streamlit prints a local URL in the terminal. Open that URL in a browser to use Poorcone Lab.

The semantic-search model may need to download its pretrained weights the first time it is used. An internet connection may therefore be required on first use; subsequent runs can use the local model cache.

## Using the Application

The application is organized into three main tabs:

- **Explore:** Enter a query, select a search method, and inspect the retrieved notes. Adaptive Hybrid Search is the default method.
- **Add Notes:** Create a note by entering its title, category, and content.
- **My Notes:** Browse notes, filter them by category, edit existing notes, or delete notes.

Example queries to try in Explore:

| Query | What it demonstrates |
|---|---|
| `supervised learning` | Keyword-oriented retrieval |
| `belajar dari contoh yang sudah mempunyai label` | Indonesian semantic retrieval |
| `read keyboard input to change a game character position in Pygame` | English semantic retrieval |
| `supervis` | Partial-word retrieval |

Search results and scores should be interpreted in the context of the selected method. Scores from different retrieval methods are not necessarily directly comparable.

## Running Tests

Run the complete automated test suite from the project root:

```bash
uv run pytest -q
```

The latest recorded test run passed **35 tests**. This includes tests for database operations, search behavior, benchmark metrics, benchmark evaluation, and the benchmark runner.

## Running the Search Benchmark

Run the centralized benchmark using:

```bash
uv run python -m benchmark.run_benchmark
```

The current benchmark dataset contains:

| Dataset component | Count |
|---|---:|
| Sample notes | 22 |
| Positive queries | 44 |
| Partial queries | 10 |
| Negative queries | 9 |
| **Total queries** | **63** |

The evaluator uses `K = 3` and reports retrieval metrics for Word TF-IDF, Character TF-IDF, Semantic Search, and Hybrid Search. The query set includes keyword queries, Indonesian and English semantic queries, partial queries, out-of-domain queries, nonsense queries, and hard negatives.

### Latest recorded benchmark snapshot

The following results are from the latest benchmark run recorded during development:

| Method | P@1 | R@3 | MRR@3 | Partial P@1 | Partial R@3 | FPR | No-result accuracy |
|---|---:|---:|---:|---:|---:|---:|---:|
| Word TF-IDF | 0.977 | 1.000 | 0.989 | 0.000 | 0.000 | 0.778 | 0.222 |
| Character TF-IDF | 0.977 | 1.000 | 0.989 | 1.000 | 0.925 | 0.778 | 0.222 |
| Semantic Search | 0.932 | 0.955 | 0.943 | 0.500 | 0.450 | 0.778 | 0.222 |
| **Hybrid Search** | **0.977** | **1.000** | **0.989** | **1.000** | **0.925** | **0.333** | **0.667** |

Metric notes:

- **P@1:** Precision at rank 1 for positive queries.
- **R@3:** Recall within the top three results for positive queries.
- **MRR@3:** Mean reciprocal rank within the top three results.
- **Partial P@1 / Partial R@3:** Precision at rank 1 and recall within the top three results for partial queries.
- **FPR:** Fraction of negative queries that returned at least one result. Lower is better.
- **No-result accuracy:** Fraction of negative queries correctly returning no results. Higher is better.

In this benchmark snapshot, Hybrid Search returned results for 3 of the 9 negative queries (FPR `0.333`). This means negative-query rejection is improved compared with the other evaluated methods, but it is not perfect.

> **Evaluation limitation:** These metrics are measured on a small, curated benchmark dataset. They are useful for comparing methods during development, but they do not establish performance on every user's notes or on unseen query distributions. Results may change when the dataset, notes, model, or thresholds change.

## Project Structure

```text
poorcone-lab/
├── app.py                         # Streamlit user interface
├── database.py                    # SQLite connection and note CRUD operations
├── search.py                      # Word and Character TF-IDF retrieval
├── semantic_search.py              # Sentence-embedding semantic retrieval
├── hybrid_search.py                # Adaptive Hybrid Search and WRRF ranking
├── benchmark/
│   ├── dataset.py                 # Sample notes and labeled benchmark queries
│   ├── metrics.py                 # Retrieval evaluation metrics
│   ├── evaluator.py               # Evaluation for each search method
│   └── run_benchmark.py           # Unified benchmark entry point
├── tests/
│   ├── test_database.py
│   ├── test_search.py
│   ├── test_hybrid_search.py
│   ├── test_benchmark_metrics.py
│   ├── test_benchmark_evaluator.py
│   └── test_benchmark_runner.py
├── pyproject.toml                 # Project metadata and dependencies
├── uv.lock                        # Locked dependency versions
├── .python-version                # Selected Python version
└── README.md
```

## Local Data and Privacy

The application stores notes in a local SQLite database named `poorcone_lab.db`, located in the project directory. The database is initialized automatically when the application starts if it does not already exist.

- The database contains user-created notes and should be treated as private application data.
- Database files are excluded from Git through `.gitignore`; do not force-add them to a public repository.
- Back up `poorcone_lab.db` before making database schema changes or performing maintenance.
- `uv sync --locked` installs dependencies; it is not a database migration or reset command.

The database filename is retained for compatibility with the existing implementation, even though the project is named Poorcone Lab.

## Current Scope and Limitations

- Poorcone Lab is currently a local, single-user prototype built around Streamlit and SQLite.
- Semantic retrieval uses a pretrained sentence-embedding model; the model is not fine-tuned on the user's personal notes.
- Hybrid Search uses thresholds and candidate intersection to reduce irrelevant results, but the current benchmark still contains false positives.
- Benchmark results are limited by the size and coverage of the curated dataset.
- The current version focuses on note management and retrieval. It does **not** yet provide Retrieval-Augmented Generation (RAG) or generative answers grounded in the notes.

## Roadmap

Potential future improvements include:

- Expand the benchmark with more representative notes, positive queries, and hard negatives.
- Investigate remaining false positives and improve out-of-domain query rejection without harming positive or partial-query recall.
- Improve note organization and search-result explanations.
- Evaluate and implement RAG only after retrieval quality and evaluation coverage are sufficiently mature.

---

Poorcone Lab is an ongoing personal AI research and development project.
