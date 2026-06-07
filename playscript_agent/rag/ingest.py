from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import chromadb
from chromadb.api import ClientAPI


DEFAULT_CHROMA_DIR = Path(__file__).resolve().parents[2] / ".cache" / "chroma"


@dataclass(frozen=True, slots=True)
class IngestResult:
    collection_name: str
    chunk_count: int
    persist_directory: str | None


def create_chroma_client(
    *,
    persist_directory: str | Path | None = DEFAULT_CHROMA_DIR,
) -> ClientAPI:
    if persist_directory is None:
        return chromadb.Client()
    path = Path(persist_directory)
    path.mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(path=str(path))
