import hashlib
import os
import stat
import uuid
from dataclasses import dataclass
from pathlib import Path, PureWindowsPath

from io import BytesIO

from docx import Document
from docx.table import Table
from docx.text.paragraph import Paragraph

from pypdf import PdfReader

import database


# ============================================================
# CONFIGURATION
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent

DOCUMENT_STORAGE_DIR = PROJECT_ROOT / "data" / "documents"

ALLOWED_EXTENSIONS = {
    ".txt",
    ".md",
    ".pdf",
    ".docx",
}

MAX_PDF_PAGES = 200

MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB


# ============================================================
# RESULT MODEL
# ============================================================


@dataclass(frozen=True)
class IngestionResult:
    document_id: int
    title: str
    original_filename: str
    file_type: str
    content_hash: str
    file_size_bytes: int
    is_duplicate: bool


@dataclass(frozen=True)
class DocumentDeletionResult:
    document_id: int
    file_missing: bool = False
    cleanup_pending: bool = False
    staging_path: Path | None = None


class DocumentNotFoundError(LookupError):
    """Raised when a requested document does not exist in SQLite."""


class DocumentDeletionRecoveryError(RuntimeError):
    """Raised when a staged file cannot be restored after database failure."""

    def __init__(self, message, recovery_path):
        super().__init__(f"{message} File recovery location: {recovery_path}")
        self.recovery_path = Path(recovery_path)


# ============================================================
# VALIDATION
# ============================================================


def validate_filename(filename):
    """Memvalidasi nama dan ekstensi file."""

    if not isinstance(filename, str):
        raise ValueError("Nama file harus berupa string.")

    # Ambil nama file saja, bukan direktori asalnya.
    safe_filename = filename.replace("\\", "/").split("/")[-1].strip()

    if safe_filename in {"", ".", ".."}:
        raise ValueError("Nama file tidak valid.")

    extension = Path(safe_filename).suffix.lower()

    if extension not in ALLOWED_EXTENSIONS:
        raise ValueError("Format tidak didukung. Gunakan file TXT atau Markdown.")

    return safe_filename, extension


def extract_text(content):
    """Mengubah bytes menjadi teks UTF-8."""

    if not isinstance(content, (bytes, bytearray, memoryview)):
        raise ValueError("Konten file harus berupa bytes.")

    raw_content = bytes(content)

    if not raw_content:
        raise ValueError("File kosong.")

    if len(raw_content) > MAX_FILE_SIZE_BYTES:
        raise ValueError("Ukuran file melebihi batas 10 MB.")

    try:
        text = raw_content.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise ValueError("File harus menggunakan encoding UTF-8.") from error

    if "\x00" in text:
        raise ValueError("File terdeteksi mengandung data biner.")

    if not text.strip():
        raise ValueError("Dokumen tidak memiliki konten teks.")

    # Normalisasi line endings.
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    return text


def extract_pdf_text(content):
    """Mengekstrak teks dari setiap halaman PDF."""

    try:
        reader = PdfReader(
            BytesIO(content),
            strict=False,
        )

        if reader.is_encrypted:
            raise ValueError("PDF dilindungi password. PDF terenkripsi belum didukung.")

        page_count = len(reader.pages)

        if page_count == 0:
            raise ValueError("PDF tidak memiliki halaman.")

        if page_count > MAX_PDF_PAGES:
            raise ValueError(
                f"PDF memiliki {page_count} halaman. "
                f"Batas maksimum adalah {MAX_PDF_PAGES} halaman."
            )

        extracted_pages = []

        for page_number, page in enumerate(
            reader.pages,
            start=1,
        ):
            page_text = page.extract_text() or ""

            if page_text.strip():
                extracted_pages.append(f"[Page {page_number}]\n{page_text.strip()}")

    except ValueError:
        raise

    except Exception as error:
        raise ValueError("PDF tidak valid, rusak, atau gagal dibaca.") from error

    if not extracted_pages:
        raise ValueError(
            "PDF tidak memiliki teks yang dapat diekstrak. "
            "PDF hasil scan mungkin memerlukan OCR, "
            "yang belum didukung."
        )

    return "\n\n".join(extracted_pages)


def _extract_docx_blocks(container):
    """
    Mengekstrak paragraf dan tabel sesuai urutan dokumen.
    Mendukung tabel bersarang.
    """

    extracted_parts = []

    for block in container.iter_inner_content():
        if isinstance(block, Paragraph):
            paragraph_text = block.text.strip()

            if paragraph_text:
                extracted_parts.append(paragraph_text)

        elif isinstance(block, Table):
            table_rows = []

            for row in block.rows:
                cell_texts = []
                seen_cells = set()

                for cell in row.cells:
                    # Hindari membaca sel merged lebih dari sekali.
                    cell_identity = id(cell._tc)

                    if cell_identity in seen_cells:
                        continue

                    seen_cells.add(cell_identity)

                    cell_parts = _extract_docx_blocks(cell)

                    cell_text = " ".join(
                        part.strip() for part in cell_parts if part.strip()
                    )

                    if cell_text:
                        cell_texts.append(cell_text)

                if cell_texts:
                    table_rows.append(" | ".join(cell_texts))

            if table_rows:
                extracted_parts.append("\n".join(table_rows))

    return extracted_parts


def extract_docx_text(content):
    """Mengekstrak paragraf dan tabel dari DOCX."""

    try:
        document = Document(BytesIO(content))

        extracted_parts = _extract_docx_blocks(document)

    except Exception as error:
        raise ValueError("DOCX tidak valid atau gagal dibaca.") from error

    extracted_text = "\n\n".join(extracted_parts)

    if not extracted_text.strip():
        raise ValueError("DOCX tidak memiliki teks yang dapat diekstrak.")

    return extracted_text


def extract_document_text(content, extension):
    """Memilih extractor berdasarkan ekstensi dokumen."""

    if extension in {".txt", ".md"}:
        return extract_text(content)

    elif extension == ".pdf":
        return extract_pdf_text(content)

    elif extension == ".docx":
        return extract_docx_text(content)

    raise ValueError(f"Format dokumen tidak didukung: {extension}")


# ============================================================
# HASHING
# ============================================================


def calculate_file_hash(content):
    """Menghitung SHA-256 berdasarkan bytes file asli."""

    return hashlib.sha256(content).hexdigest()


# ============================================================
# DOCUMENT INGESTION
# ============================================================


def ingest_document(filename, content):
    """
    Memvalidasi, mengekstrak, dan menyimpan dokumen TXT/Markdown.

    Jika konten sudah pernah diimpor, dokumen lama dikembalikan
    tanpa membuat duplikat.
    """

    # 1. Validasi filename.
    original_filename, extension = validate_filename(filename)

    # 2. Validasi dan ekstraksi konten.
    raw_content = (
        bytes(content) if isinstance(content, (bytes, bytearray, memoryview)) else None
    )

    if raw_content is None:
        raise ValueError("Konten file harus berupa bytes.")

    extracted_text = extract_document_text(
        raw_content,
        extension,
    )

    # 3. Hitung metadata.
    content_hash = calculate_file_hash(raw_content)
    file_size_bytes = len(raw_content)

    title = Path(original_filename).stem or original_filename
    file_type = extension.lstrip(".")

    # 4. Periksa dokumen duplikat.
    existing = database.get_document_by_hash(content_hash)

    if existing is not None:
        return IngestionResult(
            document_id=existing[0],
            title=existing[1],
            original_filename=existing[2],
            file_type=existing[3],
            content_hash=existing[6],
            file_size_bytes=existing[5],
            is_duplicate=True,
        )

    # 5. Buat nama penyimpanan unik.
    stored_filename = f"{uuid.uuid4().hex}{extension}"

    relative_path = Path("data") / "documents" / stored_filename

    absolute_path = PROJECT_ROOT / relative_path

    # 6. Simpan file asli.
    DOCUMENT_STORAGE_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    absolute_path.write_bytes(raw_content)

    try:
        # 7. Simpan metadata dan extracted text ke SQLite.
        document_id = database.add_document(
            title=title,
            original_filename=original_filename,
            file_type=file_type,
            storage_path=relative_path.as_posix(),
            file_size_bytes=file_size_bytes,
            content_hash=content_hash,
            extracted_text=extracted_text,
        )

    except Exception:
        # Hapus file fisik apabila penyimpanan database gagal.
        absolute_path.unlink(missing_ok=True)
        raise

    return IngestionResult(
        document_id=document_id,
        title=title,
        original_filename=original_filename,
        file_type=file_type,
        content_hash=content_hash,
        file_size_bytes=file_size_bytes,
        is_duplicate=False,
    )


def _validated_document_path(storage_path):
    if not isinstance(storage_path, str) or not storage_path.strip():
        raise ValueError("Storage path dokumen tidak valid.")

    if "\x00" in storage_path:
        raise ValueError("Storage path dokumen tidak valid.")

    relative_path = Path(storage_path)
    windows_path = PureWindowsPath(storage_path)

    if (
        relative_path.is_absolute()
        or windows_path.is_absolute()
        or windows_path.drive
        or ".." in relative_path.parts
        or ".." in windows_path.parts
    ):
        raise ValueError("Storage path dokumen harus berupa path relatif yang aman.")

    project_root = Path(PROJECT_ROOT).resolve()
    storage_root = Path(os.path.abspath(DOCUMENT_STORAGE_DIR))

    try:
        storage_root_relative = storage_root.relative_to(project_root)
    except ValueError as error:
        raise ValueError("Direktori storage dokumen berada di luar project.") from error

    current_path = project_root
    for part in storage_root_relative.parts:
        current_path = current_path / part
        if current_path.is_symlink():
            raise ValueError("Symlink tidak diizinkan dalam direktori storage.")

    candidate_path = Path(os.path.abspath(project_root / relative_path))

    try:
        candidate_relative = candidate_path.relative_to(storage_root)
    except ValueError as error:
        raise ValueError("Storage path berada di luar direktori dokumen.") from error

    if not candidate_relative.parts:
        raise ValueError("Storage path harus menunjuk ke sebuah file.")

    current_path = storage_root
    for part in candidate_relative.parts:
        current_path = current_path / part
        if current_path.is_symlink():
            raise ValueError("Symlink tidak diizinkan pada storage path dokumen.")

    resolved_storage_root = storage_root.resolve()
    resolved_path = candidate_path.resolve()

    try:
        resolved_relative = resolved_path.relative_to(resolved_storage_root)
    except ValueError as error:
        raise ValueError("Resolved storage path berada di luar direktori dokumen.") from error

    if not resolved_relative.parts:
        raise ValueError("Storage path harus menunjuk ke sebuah file.")

    return resolved_storage_root, resolved_path


def _validated_staging_directory(storage_root):
    staging_directory = storage_root / ".deletion-staging"

    if staging_directory.is_symlink():
        raise ValueError("Direktori staging tidak boleh berupa symlink.")

    staging_directory.mkdir(mode=0o700, exist_ok=True)

    if staging_directory.is_symlink() or not staging_directory.is_dir():
        raise ValueError("Direktori staging dokumen tidak aman.")

    if staging_directory.resolve() != storage_root / ".deletion-staging":
        raise ValueError("Direktori staging berada di luar storage dokumen.")

    return staging_directory


def _restore_staged_file(staged_path, original_path, storage_root):
    staging_directory = _validated_staging_directory(storage_root)

    if staged_path.parent != staging_directory or staged_path.is_symlink():
        raise OSError("File staging berubah atau tidak aman.")

    if not staged_path.is_file():
        raise FileNotFoundError(f"File staging tidak ditemukan: {staged_path}")

    if original_path.exists() or original_path.is_symlink():
        raise FileExistsError(f"Lokasi asal sudah digunakan: {original_path}")

    os.replace(staged_path, original_path)


def delete_document(document_id):
    """
    Menghapus metadata dokumen dan file sumber secara terkoordinasi.

    Mengembalikan None jika ID tidak ada. Result menandai file yang
    sebelumnya sudah hilang atau cleanup yang masih tertunda.
    """

    document = database.get_document_by_id(document_id)
    if document is None:
        raise DocumentNotFoundError(f"Dokumen dengan ID {document_id} tidak ditemukan.")

    storage_root, original_path = _validated_document_path(document[4])

    try:
        source_stat = original_path.lstat()
    except FileNotFoundError:
        file_missing = True
        staged_path = None
    else:
        file_missing = False

        if stat.S_ISLNK(source_stat.st_mode):
            raise ValueError("Symlink tidak diizinkan sebagai file dokumen.")

        if not stat.S_ISREG(source_stat.st_mode):
            raise ValueError("Storage path dokumen bukan file biasa.")

        staging_directory = _validated_staging_directory(storage_root)
        staged_path = staging_directory / (
            f"document-{document_id}-{uuid.uuid4().hex}.pending"
        )

        if staged_path.exists() or staged_path.is_symlink():
            raise FileExistsError(f"Lokasi staging sudah digunakan: {staged_path}")

        os.replace(original_path, staged_path)

    try:
        deleted = database.delete_document(document_id)
    except Exception as error:
        if staged_path is not None:
            try:
                _restore_staged_file(staged_path, original_path, storage_root)
            except Exception as restore_error:
                raise DocumentDeletionRecoveryError(
                    f"Penghapusan metadata gagal ({error}) dan file tidak dapat "
                    "dikembalikan.",
                    staged_path,
                ) from restore_error
        raise

    if not deleted:
        if staged_path is not None:
            try:
                _restore_staged_file(staged_path, original_path, storage_root)
            except Exception as restore_error:
                raise DocumentDeletionRecoveryError(
                    "Record dokumen tidak terhapus dan file tidak dapat "
                    "dikembalikan.",
                    staged_path,
                ) from restore_error
        return None

    if staged_path is not None:
        try:
            staging_directory = _validated_staging_directory(storage_root)
            if staged_path.parent != staging_directory or staged_path.is_symlink():
                raise OSError("File staging berubah atau tidak aman.")
            staged_path.unlink()
        except OSError:
            return DocumentDeletionResult(
                document_id=document_id,
                cleanup_pending=True,
                staging_path=staged_path,
            )
        except ValueError:
            return DocumentDeletionResult(
                document_id=document_id,
                cleanup_pending=True,
                staging_path=staged_path,
            )

    return DocumentDeletionResult(
        document_id=document_id,
        file_missing=file_missing,
    )
