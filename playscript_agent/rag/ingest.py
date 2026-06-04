from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import chromadb
from chromadb.api import ClientAPI
from chromadb.api.models.Collection import Collection

from playscript_agent.rag.embeddings import (
    EmbeddingModel,
    SentenceTransformerEmbeddingModel,
)
from playscript_agent.script import ScriptBundle, load_script


DEFAULT_COLLECTION_NAME = "playscript_chunks"
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


def ingest_script(
    script_root: str | Path,
    *,
    client: ClientAPI | None = None,
    collection_name: str = DEFAULT_COLLECTION_NAME,
    embedding_model: EmbeddingModel | None = None,
    persist_directory: str | Path | None = DEFAULT_CHROMA_DIR,
) -> tuple[Collection, IngestResult]:
    script = load_script(script_root)
    chroma_client = client or create_chroma_client(persist_directory=persist_directory)
    collection = chroma_client.get_or_create_collection(
        name=collection_name,
        embedding_function=None,
        metadata={"script_id": script.meta.script_id, "script_title": script.meta.title},
    )
    embedder = embedding_model or SentenceTransformerEmbeddingModel()
    upsert_script_chunks(collection, script, embedder)
    return collection, IngestResult(
        collection_name=collection_name,
        chunk_count=len(script.chunks),
        persist_directory=str(persist_directory) if persist_directory is not None else None,
    )


def upsert_script_chunks(
    collection: Collection,
    script: ScriptBundle,
    embedding_model: EmbeddingModel,
) -> None:
    ids = [chunk.chunk_id for chunk in script.chunks]
    documents = [chunk.content for chunk in script.chunks]
    metadatas: list[dict[str, Any]] = [
        {
            **chunk.chroma_metadata(),
            "title": chunk.title,
            "script_id": script.meta.script_id,
            "script_title": script.meta.title,
        }
        for chunk in script.chunks
    ]
    embeddings = embedding_model.embed_documents(documents)
    collection.upsert(
        ids=ids,
        documents=documents,
        metadatas=metadatas,
        embeddings=embeddings,
    )
