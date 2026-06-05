from __future__ import annotations

import re
import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence

from chromadb.api import ClientAPI
from chromadb.api.models.Collection import Collection

from playscript_agent.rag.embeddings import (
    EmbeddingModel,
    SentenceTransformerEmbeddingModel,
)
from playscript_agent.rag.ingest import (
    DEFAULT_CHROMA_DIR,
    IngestResult,
    create_chroma_client,
)


DEFAULT_RULE_COLLECTION_NAME = "dnd_rule_chunks"
DEFAULT_DOCUMENT_DIR = Path(__file__).resolve().parents[2] / "document"
DEFAULT_MODULE_DIR = DEFAULT_DOCUMENT_DIR / "modules"
SUPPORTED_RULEBOOK_EXTENSIONS = {".md", ".txt", ".pdf"}


@dataclass(frozen=True, slots=True)
class RulePage:
    page_number: int
    text: str


@dataclass(frozen=True, slots=True)
class RuleDocument:
    source_id: str
    title: str
    source_path: Path
    pages: tuple[RulePage, ...]
    ruleset: str = "dnd5e"
    document_type: str = "rules_core"
    visibility: str = "public"


@dataclass(frozen=True, slots=True)
class RuleChunk:
    chunk_id: str
    title: str
    content: str
    source: str
    source_id: str
    section: str
    page_start: int
    page_end: int
    ruleset: str
    document_type: str
    visibility: str

    def chroma_metadata(self) -> dict[str, str | int]:
        return {
            "chunk_id": self.chunk_id,
            "domain": "dnd_rules",
            "type": self.document_type,
            "ruleset": self.ruleset,
            "source_id": self.source_id,
            "source": self.source,
            "title": self.title,
            "section": self.section,
            "visibility": self.visibility,
            "page_start": self.page_start,
            "page_end": self.page_end,
        }


def load_rule_documents(
    paths: str | Path | Sequence[str | Path] = DEFAULT_DOCUMENT_DIR,
    *,
    ruleset: str = "dnd5e",
    document_type: str | None = None,
    visibility: str | None = None,
) -> tuple[RuleDocument, ...]:
    documents: list[RuleDocument] = []
    for path in _iter_rulebook_files(paths):
        effective_document_type, effective_visibility = _infer_document_scope(
            path,
            document_type=document_type,
            visibility=visibility,
        )
        documents.append(
            load_rule_document(
                path,
                ruleset=ruleset,
                document_type=effective_document_type,
                visibility=effective_visibility,
            )
        )
    if not documents:
        raise FileNotFoundError(
            f"no supported rulebook files found under {paths!r}; "
            f"supported extensions: {sorted(SUPPORTED_RULEBOOK_EXTENSIONS)}"
        )
    return tuple(documents)


def load_rule_document(
    path: str | Path,
    *,
    ruleset: str = "dnd5e",
    document_type: str | None = None,
    visibility: str | None = None,
) -> RuleDocument:
    source_path = Path(path)
    if not source_path.exists():
        raise FileNotFoundError(source_path)
    if source_path.suffix.lower() not in SUPPORTED_RULEBOOK_EXTENSIONS:
        raise ValueError(f"unsupported rulebook file type: {source_path.suffix}")

    pages = _read_rulebook_pages(source_path)
    pages = tuple(page for page in pages if page.text.strip())
    if not pages:
        raise ValueError(f"rulebook contains no extractable text: {source_path}")

    effective_document_type, effective_visibility = _infer_document_scope(
        source_path,
        document_type=document_type,
        visibility=visibility,
    )

    return RuleDocument(
        source_id=_slug(source_path.stem),
        title=source_path.stem,
        source_path=source_path,
        pages=pages,
        ruleset=ruleset,
        document_type=effective_document_type,
        visibility=effective_visibility,
    )


def chunk_rule_documents(
    documents: Iterable[RuleDocument],
    *,
    chunk_size: int = 1200,
    chunk_overlap: int = 160,
) -> tuple[RuleChunk, ...]:
    chunks: list[RuleChunk] = []
    for document in documents:
        chunks.extend(
            chunk_rule_document(
                document,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
            )
        )
    return tuple(chunks)


def chunk_rule_document(
    document: RuleDocument,
    *,
    chunk_size: int = 1200,
    chunk_overlap: int = 160,
) -> tuple[RuleChunk, ...]:
    if chunk_size <= 0:
        raise ValueError("chunk_size must be > 0")
    if chunk_overlap < 0:
        raise ValueError("chunk_overlap must be >= 0")
    if chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap must be smaller than chunk_size")

    chunks: list[RuleChunk] = []
    for page in document.pages:
        section = _infer_section_title(page.text, fallback=document.title)
        for page_chunk_index, content in enumerate(
            _split_text(page.text, chunk_size=chunk_size, chunk_overlap=chunk_overlap),
            start=1,
        ):
            title = f"{document.title} p.{page.page_number}"
            if section and section != document.title:
                title = f"{title} - {section}"
            chunks.append(
                RuleChunk(
                    chunk_id=(
                        f"rule:{document.ruleset}:{document.source_id}:"
                        f"p{page.page_number}:c{page_chunk_index}"
                    ),
                    title=title,
                    content=content,
                    source=document.source_path.name,
                    source_id=document.source_id,
                    section=section,
                    page_start=page.page_number,
                    page_end=page.page_number,
                    ruleset=document.ruleset,
                    document_type=document.document_type,
                    visibility=document.visibility,
                )
            )
    return tuple(chunks)


def ingest_rulebooks(
    paths: str | Path | Sequence[str | Path] = DEFAULT_DOCUMENT_DIR,
    *,
    client: ClientAPI | None = None,
    collection_name: str = DEFAULT_RULE_COLLECTION_NAME,
    embedding_model: EmbeddingModel | None = None,
    persist_directory: str | Path | None = DEFAULT_CHROMA_DIR,
    ruleset: str = "dnd5e",
    document_type: str | None = None,
    visibility: str | None = None,
    chunk_size: int = 1200,
    chunk_overlap: int = 160,
) -> tuple[Collection, IngestResult]:
    documents = load_rule_documents(
        paths,
        ruleset=ruleset,
        document_type=document_type,
        visibility=visibility,
    )
    chunks = chunk_rule_documents(
        documents,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )
    chroma_client = client or create_chroma_client(persist_directory=persist_directory)
    collection = chroma_client.get_or_create_collection(
        name=collection_name,
        embedding_function=None,
        metadata={"domain": "dnd_rules", "ruleset": ruleset},
    )
    embedder = embedding_model or SentenceTransformerEmbeddingModel()
    upsert_rule_chunks(collection, chunks, embedder)
    return collection, IngestResult(
        collection_name=collection_name,
        chunk_count=len(chunks),
        persist_directory=str(persist_directory) if persist_directory is not None else None,
    )


def upsert_rule_chunks(
    collection: Collection,
    chunks: Sequence[RuleChunk],
    embedding_model: EmbeddingModel,
) -> None:
    if not chunks:
        return

    documents = [chunk.content for chunk in chunks]
    embeddings = embedding_model.embed_documents(documents)
    collection.upsert(
        ids=[chunk.chunk_id for chunk in chunks],
        documents=documents,
        metadatas=[chunk.chroma_metadata() for chunk in chunks],
        embeddings=embeddings,
    )


def _iter_rulebook_files(
    paths: str | Path | Sequence[str | Path],
) -> tuple[Path, ...]:
    if isinstance(paths, (str, Path)):
        candidates: Sequence[str | Path] = [paths]
    else:
        candidates = paths

    files: list[Path] = []
    for raw_path in candidates:
        path = Path(raw_path)
        if path.is_file() and path.suffix.lower() in SUPPORTED_RULEBOOK_EXTENSIONS:
            files.append(path)
        elif path.is_dir():
            files.extend(
                child
                for child in sorted(path.rglob("*"))
                if child.is_file()
                and child.suffix.lower() in SUPPORTED_RULEBOOK_EXTENSIONS
            )
    return tuple(sorted(files))


def _infer_document_scope(
    path: Path,
    *,
    document_type: str | None,
    visibility: str | None,
) -> tuple[str, str]:
    is_module = _is_module_document(path)
    return (
        document_type or ("module_dm_only" if is_module else "rules_core"),
        visibility or ("dm_only" if is_module else "public"),
    )


def _is_module_document(path: Path) -> bool:
    return any(part.lower() == "modules" for part in path.parts)


def _read_rulebook_pages(path: Path) -> tuple[RulePage, ...]:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return _read_pdf_pages(path)
    return (RulePage(page_number=0, text=_read_text_file(path)),)


def _read_pdf_pages(path: Path) -> tuple[RulePage, ...]:
    try:
        from pypdf import PdfReader
    except ImportError as error:
        raise RuntimeError(
            "PDF rulebook ingestion requires the 'pypdf' package. "
            "Install project requirements before ingesting PDF rulebooks."
        ) from error

    reader = PdfReader(str(path))
    pages: list[RulePage] = []
    for index, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        if text.strip():
            pages.append(RulePage(page_number=index, text=_normalize_text(text)))
    return tuple(pages)


def _read_text_file(path: Path) -> str:
    raw = path.read_bytes()
    for encoding in ("utf-8-sig", "utf-8", "gb18030"):
        try:
            return _normalize_text(raw.decode(encoding))
        except UnicodeDecodeError:
            continue
    return _normalize_text(raw.decode("utf-8", errors="replace"))


def _normalize_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _split_text(
    text: str,
    *,
    chunk_size: int,
    chunk_overlap: int,
) -> tuple[str, ...]:
    paragraphs = [part.strip() for part in re.split(r"\n\s*\n", text) if part.strip()]
    if not paragraphs:
        return tuple(_split_long_text(text, chunk_size, chunk_overlap))

    chunks: list[str] = []
    current = ""
    for paragraph in paragraphs:
        if len(paragraph) > chunk_size:
            if current:
                chunks.append(current.strip())
                current = ""
            chunks.extend(_split_long_text(paragraph, chunk_size, chunk_overlap))
            continue

        candidate = paragraph if not current else f"{current}\n\n{paragraph}"
        if len(candidate) <= chunk_size:
            current = candidate
        else:
            chunks.append(current.strip())
            current = paragraph

    if current:
        chunks.append(current.strip())
    return tuple(chunk for chunk in chunks if chunk)


def _split_long_text(text: str, chunk_size: int, chunk_overlap: int) -> list[str]:
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end == len(text):
            break
        start = max(end - chunk_overlap, start + 1)
    return chunks


def _infer_section_title(text: str, *, fallback: str) -> str:
    for line in text.splitlines():
        candidate = line.strip().strip("#").strip()
        if not candidate:
            continue
        if len(candidate) > 96:
            continue
        if _looks_like_heading(candidate):
            return candidate
    return fallback


def _looks_like_heading(text: str) -> bool:
    if text.endswith(":"):
        return True
    words = text.split()
    if len(words) <= 8 and text[:1].isupper():
        return True
    return bool(re.match(r"^(chapter|part|appendix)\b", text, flags=re.IGNORECASE))


def _slug(text: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", text.lower()).strip("_")
    if slug:
        return slug
    digest = hashlib.sha1(text.encode("utf-8")).hexdigest()[:10]
    return f"doc_{digest}"
