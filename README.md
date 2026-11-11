# Poorcone Lab

**Poorcone Lab** is a personal AI research and development project focused on building practical AI-assisted tools. Its current direction is a personal knowledge management system with intelligent note retrieval.

The project is being developed incrementally, with an emphasis on understanding the underlying methods, evaluating search quality, and keeping the system maintainable as it grows.

> **Project status:** Early development. Core note management and search workflows are being developed and evaluated.

## Current Features

- **Note storage:** Store and manage personal notes using SQLite.
- **Keyword search:** Retrieve notes using TF-IDF-based text representations.
- **Character-level search:** Improve retrieval for partial words and incomplete queries.
- **Semantic search:** Retrieve notes based on textual meaning using sentence embeddings.
- **Hybrid search:** Combine lexical and semantic retrieval through a hybrid ranking approach.
- **Search evaluation:** Run benchmark scripts and automated tests while improving retrieval quality.

## Technology Stack

- **Language:** Python
- **Environment and dependency management:** [uv](https://docs.astral.sh/uv/)
- **Application interface:** Streamlit
- **Database:** SQLite
- **Data processing and machine learning:** scikit-learn, Sentence Transformers, PyTorch
- **Testing:** pytest

## Getting Started

### Prerequisites

- Ubuntu on WSL 2 (or another compatible Linux environment)
- Python version configured in `.python-version`
- [uv](https://docs.astral.sh/uv/getting-started/installation/)

### 1. Open the project directory

```bash
cd ~/projects/poorcone-lab
```

### 2. Install dependencies

```bash
uv sync --locked
```

This creates or updates the project virtual environment and installs the dependencies recorded in `uv.lock`.

### 3. Run the application

```bash
uv run streamlit run app.py
```

Streamlit will print a local URL in the terminal. Open that URL in your browser to use the application.

## Running Tests

Run the test suite from the project root:

```bash
uv run pytest -q
```

## Search Experiments

The repository includes separate modules and scripts for experimenting with retrieval methods. Depending on the current implementation, useful entry points include:

```bash
uv run python benchmark_search.py
uv run python benchmark_semantic.py
uv run python debug_retrieval.py
```

These scripts are intended for inspecting search behavior and comparing retrieval approaches. Run them from the project root.

## Project Structure

```text
poorcone-lab/
├── app.py                  # Streamlit application
├── main.py                 # Main project entry point / utilities
├── database.py             # SQLite database operations
├── search.py               # Lexical search implementation
├── semantic_search.py      # Semantic search implementation
├── hybrid_search.py        # Hybrid retrieval and ranking
├── benchmark_search.py     # Search benchmark script
├── benchmark_semantic.py   # Semantic-search benchmark script
├── debug_retrieval.py      # Retrieval debugging script
├── tests/                  # Automated tests
├── pyproject.toml          # Project metadata and dependencies
├── uv.lock                 # Locked dependency versions
└── .python-version         # Project Python version
```

The exact modules and their responsibilities may evolve as the project develops.

## Local Data

The application uses a local SQLite database currently named `pair_lab.db`. The filename is retained for compatibility with the existing project implementation; it does not change the project's current name, **Poorcone Lab**.

- Back up the database before making structural changes.
- Do not delete the database when reinstalling dependencies.
- Avoid committing personal notes or other private database contents to a public repository.

The database filename can be renamed in a later maintenance step after all code references and backup procedures have been checked.

## Development Principles

- Build a working minimum viable product before expanding its scope.
- Prefer measurable search improvements over adding complexity without evaluation.
- Keep experiments, application code, and tests understandable and maintainable.
- Treat retrieval benchmarks as development tools; results depend on the dataset and evaluation queries.

## Roadmap

Potential next steps include:

- Expand the evaluation dataset with realistic queries and hard negative examples.
- Improve Indonesian and English query handling, including partial and ambiguous queries.
- Refine hybrid ranking and expose useful retrieval diagnostics.
- Improve note organization, metadata, and application usability.
- Evaluate whether retrieval-augmented generation (RAG) is justified by the system's actual needs.

---

Created and maintained as an ongoing personal AI research and development project.
