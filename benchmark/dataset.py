"""
Centralized benchmark dataset for Poorcone Lab.

Dataset Version: 2

Digunakan oleh seluruh metode pencarian untuk mengukur:
- Keyword retrieval
- Indonesian semantic retrieval
- English semantic retrieval
- Partial query retrieval
- Negative query rejection
"""


# ============================================================
# HELPER
# ============================================================


def _case(query, relevant_ids, kind):
    """Membuat satu kasus benchmark dengan ground truth."""
    return {
        "query": query,
        "relevant_ids": set(relevant_ids),
        "kind": kind,
    }


# ============================================================
# 1. SAMPLE NOTES
# ============================================================
# Format:
# (id, title, category, content)

SAMPLE_NOTES = [
    (
        1,
        "Supervised Learning",
        "Machine Learning",
        (
            "Supervised learning adalah metode machine learning "
            "yang menggunakan labeled data (data berlabel) untuk "
            "mempelajari hubungan antara input dan output, lalu "
            "memprediksi target atau label untuk data baru."
        ),
    ),
    (
        2,
        "Unsupervised Learning",
        "Machine Learning",
        (
            "Unsupervised learning adalah metode machine learning "
            "yang menganalisis unlabeled data (data tanpa label) "
            "untuk menemukan pola, struktur, atau kelompok "
            "tersembunyi, misalnya dengan clustering."
        ),
    ),
    (
        3,
        "Player Movement",
        "Game Development",
        (
            "Player movement adalah mekanisme pergerakan karakter "
            "dalam game. Pada Pygame, input keyboard seperti tombol "
            "panah atau WASD dibaca untuk mengubah posisi player "
            "pada layar."
        ),
    ),
    (
        4,
        "TF-IDF Search",
        "Information Retrieval",
        (
            "TF-IDF (Term Frequency-Inverse Document Frequency) "
            "adalah metode pembobotan kata dalam information "
            "retrieval untuk memperkirakan kepentingan suatu "
            "istilah pada dokumen relatif terhadap kumpulan "
            "dokumen dan membantu pencarian relevansi."
        ),
    ),
    (
        5,
        "Python Lists",
        "Python",
        (
            "Python list adalah struktur data mutable yang "
            "menyimpan ordered collection (kumpulan elemen "
            "berurutan). Elemen dapat diakses melalui indeks, "
            "ditambahkan, dihapus, atau diperbarui."
        ),
    ),
    (
        6,
        "Linear Regression",
        "Machine Learning",
        (
            "Linear regression adalah algoritma supervised "
            "learning yang memodelkan hubungan linear antara "
            "variabel input dan target numerik untuk memprediksi "
            "nilai kontinu."
        ),
    ),
    (
        7,
        "Classification Metrics",
        "Machine Learning",
        (
            "Classification metrics digunakan untuk mengevaluasi "
            "model klasifikasi. Metrik umum meliputi accuracy, "
            "precision, recall, F1-score, confusion matrix, "
            "false positive, dan false negative."
        ),
    ),
    (
        8,
        "K-Means Clustering",
        "Machine Learning",
        (
            "K-Means adalah algoritma unsupervised learning "
            "untuk membagi data menjadi K cluster berdasarkan "
            "kedekatan data terhadap centroid atau titik pusat "
            "masing-masing kelompok."
        ),
    ),
    (
        9,
        "Neural Networks",
        "Artificial Intelligence",
        (
            "Neural network merupakan model artificial "
            "intelligence yang tersusun dari lapisan neuron "
            "saling terhubung. Model mempelajari pola melalui "
            "weights, biases, dan activation functions."
        ),
    ),
    (
        10,
        "Data Preprocessing",
        "Data Science",
        (
            "Data preprocessing adalah proses mempersiapkan "
            "dataset sebelum analisis atau pelatihan model. "
            "Prosesnya mencakup data cleaning, menangani missing "
            "values, encoding, dan feature scaling."
        ),
    ),
    (
        11,
        "Pandas DataFrames",
        "Python",
        (
            "Pandas DataFrame adalah struktur data tabular dalam "
            "Python yang menyimpan data berbentuk baris dan kolom. "
            "Data dapat difilter, diperbarui, dianalisis, dan "
            "dimanipulasi menggunakan library pandas."
        ),
    ),
    (
        12,
        "Python Dictionaries",
        "Python",
        (
            "Python dictionary adalah struktur data yang "
            "menyimpan pasangan key-value. Setiap value diakses "
            "menggunakan key sehingga cocok untuk pemetaan data."
        ),
    ),
    (
        13,
        "Python Functions",
        "Python",
        (
            "Python functions adalah blok kode yang dapat "
            "digunakan kembali. Function dapat menerima parameters, "
            "menjalankan operasi, dan mengembalikan nilai "
            "menggunakan return."
        ),
    ),
    (
        14,
        "Object-Oriented Programming",
        "Software Engineering",
        (
            "Object-oriented programming atau OOP adalah "
            "paradigma pemrograman yang menggunakan class dan "
            "object. Konsepnya mencakup attributes, methods, "
            "encapsulation, inheritance, dan polymorphism."
        ),
    ),
    (
        15,
        "Pygame Collision Detection",
        "Game Development",
        (
            "Collision detection digunakan untuk mendeteksi "
            "tabrakan atau overlap antara objek dalam game. "
            "Pada Pygame, collision dapat diperiksa menggunakan "
            "hitbox, rectangle, dan metode colliderect."
        ),
    ),
    (
        16,
        "Game Loop",
        "Game Development",
        (
            "Game loop adalah siklus utama yang terus berjalan "
            "selama game aktif. Siklus ini menangani input, "
            "memperbarui game state, melakukan rendering frame, "
            "dan mengatur frame rate."
        ),
    ),
    (
        17,
        "Dynamic Difficulty Adjustment",
        "Game AI",
        (
            "Dynamic Difficulty Adjustment atau DDA adalah "
            "mekanisme untuk menyesuaikan tingkat kesulitan game "
            "berdasarkan performa pemain. Penyesuaian dapat "
            "menggunakan survival time, kills, damage taken, "
            "enemy speed, dan spawn rate."
        ),
    ),
    (
        18,
        "REST API",
        "Software Engineering",
        (
            "REST API merupakan pendekatan arsitektur untuk "
            "komunikasi antar aplikasi melalui HTTP. REST "
            "menggunakan resources, endpoints, dan HTTP methods "
            "seperti GET, POST, PUT, dan DELETE."
        ),
    ),
    (
        19,
        "FastAPI Routing",
        "Software Engineering",
        (
            "FastAPI adalah framework Python untuk membangun "
            "web API. Routing menggunakan path operation "
            "decorators seperti @app.get dan @app.post untuk "
            "menghubungkan HTTP requests dengan fungsi endpoint."
        ),
    ),
    (
        20,
        "SQLite Database",
        "Database",
        (
            "SQLite adalah embedded relational database yang "
            "menyimpan data dalam file lokal. SQLite mendukung "
            "SQL, tables, queries, transactions, dan cocok untuk "
            "aplikasi yang membutuhkan database ringan."
        ),
    ),
    (
        21,
        "Unit Testing with Pytest",
        "Software Testing",
        (
            "Pytest adalah framework untuk menjalankan automated "
            "tests pada kode Python. Pengujian dapat menggunakan "
            "assertions, fixtures, parametrization, dan test "
            "functions untuk memverifikasi perilaku program."
        ),
    ),
    (
        22,
        "Git Version Control",
        "Software Engineering",
        (
            "Git adalah distributed version control system "
            "untuk melacak perubahan source code. Git mendukung "
            "commits, branches, merging, dan kolaborasi dalam "
            "pengembangan perangkat lunak."
        ),
    ),
]


# ============================================================
# 2. POSITIVE QUERY CASES
# ============================================================

POSITIVE_CASES = [
    # --------------------------------------------------------
    # A. Exact keyword queries
    # --------------------------------------------------------
    _case("supervised learning", {1}, "keyword"),
    _case("unlabeled data", {2}, "keyword"),
    _case("pygame keyboard", {3}, "keyword"),
    _case("inverse document frequency", {4}, "keyword"),
    _case("python lists", {5}, "keyword"),
    _case("linear regression", {6}, "keyword"),
    _case("classification metrics", {7}, "keyword"),
    _case("k-means clustering", {8}, "keyword"),
    _case("neural networks", {9}, "keyword"),
    _case("data preprocessing", {10}, "keyword"),
    _case("pandas dataframe", {11}, "keyword"),
    _case("python dictionaries", {12}, "keyword"),
    _case("python functions", {13}, "keyword"),
    _case("object oriented programming", {14}, "keyword"),
    _case("pygame collision detection", {15}, "keyword"),
    _case("game loop", {16}, "keyword"),
    _case("dynamic difficulty adjustment", {17}, "keyword"),
    _case("REST API", {18}, "keyword"),
    _case("FastAPI routing", {19}, "keyword"),
    _case("SQLite database", {20}, "keyword"),
    _case("pytest unit testing", {21}, "keyword"),
    _case("Git version control", {22}, "keyword"),
    # --------------------------------------------------------
    # B. Indonesian semantic queries
    # --------------------------------------------------------
    _case(
        "belajar dari contoh yang sudah mempunyai label untuk memprediksi keluaran",
        {1},
        "semantic_id",
    ),
    _case(
        "menemukan pola dan kelompok dalam data tanpa label",
        {2},
        "semantic_id",
    ),
    _case(
        "memperkirakan nilai angka berdasarkan hubungan "
        "antara variabel input dan target",
        {6},
        "semantic_id",
    ),
    _case(
        "menilai kinerja model klasifikasi dengan accuracy "
        "precision recall dan f1 score",
        {7},
        "semantic_id",
    ),
    _case(
        "membagi data menjadi beberapa kelompok berdasarkan titik pusat atau centroid",
        {8},
        "semantic_id",
    ),
    _case(
        "membersihkan dataset menangani nilai yang hilang "
        "dan melakukan penskalaan fitur",
        {10},
        "semantic_id",
    ),
    _case(
        "mengolah data berbentuk tabel dengan baris dan kolom menggunakan pandas",
        {11},
        "semantic_id",
    ),
    _case(
        "menyusun program menggunakan class object atribut dan method",
        {14},
        "semantic_id",
    ),
    _case(
        "menyesuaikan tingkat kesulitan permainan berdasarkan performa pemain",
        {17},
        "semantic_id",
    ),
    _case(
        "mendefinisikan endpoint HTTP menggunakan decorator pada framework FastAPI",
        {19},
        "semantic_id",
    ),
    _case(
        "menulis pengujian otomatis untuk memeriksa perilaku "
        "program menggunakan pytest",
        {21},
        "semantic_id",
    ),
    # --------------------------------------------------------
    # C. English semantic queries
    # --------------------------------------------------------
    _case(
        "read keyboard input to change a game character position in Pygame",
        {3},
        "semantic_en",
    ),
    _case(
        "weight terms based on frequency and inverse document "
        "frequency to rank documents",
        {4},
        "semantic_en",
    ),
    _case(
        "a mutable ordered collection that stores items at indexed positions in Python",
        {5},
        "semantic_en",
    ),
    _case(
        "learn representations through connected layers "
        "of neurons weights and activation functions",
        {9},
        "semantic_en",
    ),
    _case(
        "store key value pairs and retrieve values using their keys in Python",
        {12},
        "semantic_en",
    ),
    _case(
        "define reusable blocks of code that accept parameters and return values",
        {13},
        "semantic_en",
    ),
    _case(
        "detect when two game objects overlap using hitboxes or rectangles",
        {15},
        "semantic_en",
    ),
    _case(
        "repeat input handling state updates and rendering for every game frame",
        {16},
        "semantic_en",
    ),
    _case(
        "expose application resources through stateless HTTP methods and endpoints",
        {18},
        "semantic_en",
    ),
    _case(
        "use an embedded relational database stored in a local file",
        {20},
        "semantic_en",
    ),
    _case(
        "track source code changes using commits branches and merges",
        {22},
        "semantic_en",
    ),
]


# ============================================================
# 3. PARTIAL QUERY CASES
# ============================================================

PARTIAL_QUERY_CASES = [
    # "super" terdapat pada supervised dan unsupervised.
    _case("super", {1, 2}, "partial"),
    _case("superv", {1, 2}, "partial"),
    _case("supervis", {1, 2}, "partial"),
    _case("vised", {1, 2}, "partial"),
    # "pyth" terdapat dalam judul atau konten empat catatan.
    _case("pyth", {5, 11, 12, 13}, "partial"),
    _case("regress", {6}, "partial"),
    _case("panda", {11}, "partial"),
    _case("dict", {12}, "partial"),
    _case("collis", {15}, "partial"),
    _case("fast", {19}, "partial"),
]


# ============================================================
# 4. NEGATIVE QUERY CASES
# ============================================================

NEGATIVE_CASES = [
    # --------------------------------------------------------
    # A. Out-of-domain queries
    # --------------------------------------------------------
    _case(
        "astronomi dan galaksi",
        set(),
        "out_of_domain",
    ),
    _case(
        "resep masakan nasi goreng",
        set(),
        "out_of_domain",
    ),
    # --------------------------------------------------------
    # B. Nonsense queries
    # --------------------------------------------------------
    _case(
        "zebra teleportasi",
        set(),
        "nonsense",
    ),
    # --------------------------------------------------------
    # C. Hard negative queries
    # --------------------------------------------------------
    _case(
        "membangun aplikasi real-time menggunakan WebSocket",
        set(),
        "hard_negative",
    ),
    _case(
        "melatih YOLOv8 untuk object detection pada gambar",
        set(),
        "hard_negative",
    ),
    _case(
        "membuat agen game reinforcement learning menggunakan Q-learning",
        set(),
        "hard_negative",
    ),
    _case(
        "mengorkestrasi container menggunakan Docker Compose",
        set(),
        "hard_negative",
    ),
    _case(
        "mengoptimalkan query PostgreSQL menggunakan indexing",
        set(),
        "hard_negative",
    ),
    _case(
        "membuat animasi karakter 3D menggunakan Blender dan skeletal rigging",
        set(),
        "hard_negative",
    ),
]
