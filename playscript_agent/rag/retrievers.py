from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from chromadb.api.models.Collection import Collection

from playscript_agent.rag.embeddings import EmbeddingModel
from playscript_agent.rag.filters import (
    RuleAccessContext,
    build_chroma_where_filter,
    build_rule_chroma_where_filter,
)
from playscript_agent.script import AccessContext


@dataclass(frozen=True, slots=True)
class RetrievedChunk:
    chunk_id: str
    content: str
    metadata: dict[str, Any]
    distance: float | None


class ScopedRetriever:
    def __init__(
        self,
        collection: Collection,
        embedding_model: EmbeddingModel,
        context: AccessContext,
        *,
        default_k: int = 4,
    ) -> None:
        self.collection = collection
        self.embedding_model = embedding_model
        self.context = context
        self.default_k = default_k

    def search(self, query: str, *, k: int | None = None) -> list[RetrievedChunk]:
        limit = k or self.default_k
        where_filter = build_chroma_where_filter(self.context)
        candidate_count = max(limit, min(_collection_count(self.collection), limit * 4))
        raw = self.collection.query(
            query_embeddings=[self.embedding_model.embed_query(query)],
            n_results=candidate_count,
            where=where_filter or None,
            include=["documents", "metadatas", "distances"],
        )
        chunks = _parse_query_result(raw)
        return _rerank(query, chunks)[:limit]


class RuleRetriever:
    def __init__(
        self,
        collection: Collection,
        embedding_model: EmbeddingModel,
        context: RuleAccessContext | None = None,
        *,
        default_k: int = 6,
    ) -> None:
        self.collection = collection
        self.embedding_model = embedding_model
        self.context = context or RuleAccessContext.for_dm()
        self.default_k = default_k

    def search(self, query: str, *, k: int | None = None) -> list[RetrievedChunk]:
        limit = k or self.default_k
        where_filter = build_rule_chroma_where_filter(self.context)
        candidate_count = max(limit, min(_collection_count(self.collection), limit * 4))
        raw = self.collection.query(
            query_embeddings=[self.embedding_model.embed_query(query)],
            n_results=candidate_count,
            where=where_filter or None,
            include=["documents", "metadatas", "distances"],
        )
        chunks = _parse_query_result(raw)
        return _rerank(query, chunks)[:limit]


def build_scoped_retriever(
    collection: Collection,
    embedding_model: EmbeddingModel,
    context: AccessContext,
    *,
    default_k: int = 4,
) -> ScopedRetriever:
    return ScopedRetriever(
        collection=collection,
        embedding_model=embedding_model,
        context=context,
        default_k=default_k,
    )


def build_rule_retriever(
    collection: Collection,
    embedding_model: EmbeddingModel,
    context: RuleAccessContext | None = None,
    *,
    default_k: int = 6,
) -> RuleRetriever:
    return RuleRetriever(
        collection=collection,
        embedding_model=embedding_model,
        context=context,
        default_k=default_k,
    )


def _parse_query_result(result: dict[str, Any]) -> list[RetrievedChunk]:
    ids = result.get("ids", [[]])[0]
    documents = result.get("documents", [[]])[0]
    metadatas = result.get("metadatas", [[]])[0]
    distances = result.get("distances", [[]])[0] if result.get("distances") else []
    chunks: list[RetrievedChunk] = []
    for index, chunk_id in enumerate(ids):
        chunks.append(
            RetrievedChunk(
                chunk_id=chunk_id,
                content=documents[index],
                metadata=metadatas[index] or {},
                distance=distances[index] if index < len(distances) else None,
            )
        )
    return chunks


def _rerank(query: str, chunks: list[RetrievedChunk]) -> list[RetrievedChunk]:
    return sorted(
        chunks,
        key=lambda chunk: (
            -_lexical_score(query, f"{chunk.metadata.get('title', '')} {chunk.content}"),
            chunk.distance if chunk.distance is not None else 0.0,
        ),
    )


def _lexical_score(query: str, text: str) -> int:
    query_tokens = set(_tokens(query))
    text_tokens = set(_tokens(text))
    return len(query_tokens & text_tokens)


def _tokens(text: str) -> list[str]:
    words = [word.lower() for word in text.split() if word.strip()]
    if words:
        return words + [char for word in words for char in word if not char.isspace()]
    return [char for char in text.lower() if not char.isspace()]


def _collection_count(collection: Collection) -> int:
    try:
        return collection.count()
    except Exception:
        return 0
