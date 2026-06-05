from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from threading import RLock
from typing import Any

from playscript_agent.api.services.game_state import game_state


DEFAULT_RAG_K = 4
MAX_CONTEXT_CHARS_PER_CHUNK = 900


@dataclass(frozen=True, slots=True)
class RuleSearchHit:
    chunk_id: str
    content: str
    metadata: dict[str, Any]
    distance: float | None

    def as_dict(self) -> dict[str, Any]:
        return {
            "chunkId": self.chunk_id,
            "content": self.content,
            "metadata": self.metadata,
            "distance": self.distance,
        }


@dataclass(slots=True)
class _RuleIndexCache:
    collection: Any | None = None
    embedding_model: Any | None = None
    client: Any | None = None
    key: tuple[str, str, str] | None = None


_cache = _RuleIndexCache()
_cache_lock = RLock()


def reset_rule_rag_cache() -> None:
    with _cache_lock:
        _cache.collection = None
        _cache.embedding_model = None
        _cache.client = None
        _cache.key = None


def search_rules(
    query: str,
    *,
    user_id: str,
    k: int = DEFAULT_RAG_K,
    document_root: str | Path | None = None,
    collection_name: str | None = None,
    embedding_model: Any | None = None,
    client: Any | None = None,
    persist_directory: str | Path | None = None,
) -> list[RuleSearchHit]:
    query = query.strip()
    if not query:
        return []

    collection, embedder = ensure_rule_index(
        document_root=document_root,
        collection_name=collection_name,
        embedding_model=embedding_model,
        client=client,
        persist_directory=persist_directory,
    )
    context = _rule_access_context_for_user(user_id)
    retriever = _build_rule_retriever(collection, embedder, context, default_k=k)
    return [
        RuleSearchHit(
            chunk_id=chunk.chunk_id,
            content=chunk.content,
            metadata=dict(chunk.metadata),
            distance=chunk.distance,
        )
        for chunk in retriever.search(query, k=k)
    ]


def build_rule_context(
    query: str,
    *,
    user_id: str,
    k: int = DEFAULT_RAG_K,
) -> str:
    try:
        hits = search_rules(query, user_id=user_id, k=k)
    except Exception:
        return ""

    if not hits:
        return ""

    lines = [
        "Relevant DND rule/module context follows. It has already been filtered "
        "for the current user's access scope. Use it only when relevant, and do "
        "not invent rules or adventure facts beyond this context."
    ]
    for index, hit in enumerate(hits, start=1):
        metadata = hit.metadata
        source = metadata.get("source", "")
        page = metadata.get("page_start", "")
        visibility = metadata.get("visibility", "")
        title = metadata.get("title") or metadata.get("section") or hit.chunk_id
        content = _trim(hit.content, MAX_CONTEXT_CHARS_PER_CHUNK)
        lines.append(
            f"\n[{index}] {title} | source={source} page={page} visibility={visibility}\n"
            f"{content}"
        )
    return "\n".join(lines)


def ensure_rule_index(
    *,
    document_root: str | Path | None = None,
    collection_name: str | None = None,
    embedding_model: Any | None = None,
    client: Any | None = None,
    persist_directory: str | Path | None = None,
) -> tuple[Any, Any]:
    default_document_dir, default_collection_name, default_chroma_dir = _rag_defaults()
    effective_document_root = Path(document_root) if document_root else default_document_dir
    effective_collection_name = collection_name or default_collection_name
    effective_persist_directory = (
        Path(persist_directory)
        if persist_directory is not None
        else default_chroma_dir
    )
    key = (
        str(effective_document_root.resolve()),
        effective_collection_name,
        str(effective_persist_directory.resolve())
        if effective_persist_directory is not None
        else "<memory>",
    )

    with _cache_lock:
        if (
            _cache.collection is not None
            and _cache.embedding_model is not None
            and _cache.key == key
            and (client is None or client is _cache.client)
            and (embedding_model is None or embedding_model is _cache.embedding_model)
        ):
            return _cache.collection, _cache.embedding_model

        embedder = embedding_model or _sentence_transformer_embedding_model()
        chroma_client = client or _create_chroma_client(
            persist_directory=effective_persist_directory
        )
        collection = chroma_client.get_or_create_collection(
            name=effective_collection_name,
            embedding_function=None,
            metadata={"domain": "dnd_rules", "ruleset": "dnd5e"},
        )
        if collection.count() == 0:
            collection, _ = _ingest_rulebooks(
                effective_document_root,
                client=chroma_client,
                collection_name=effective_collection_name,
                embedding_model=embedder,
                persist_directory=effective_persist_directory,
            )

        _cache.collection = collection
        _cache.embedding_model = embedder
        _cache.client = chroma_client
        _cache.key = key
        return collection, embedder


def _rule_access_context_for_user(user_id: str) -> Any:
    rule_access_context = _rule_access_context_cls()
    if game_state.is_dm(user_id):
        return rule_access_context.for_dm()
    character_id = game_state.character_id_for_user(user_id) or user_id
    return rule_access_context.for_player(character_id)


def _trim(text: str, limit: int) -> str:
    normalized = text.strip()
    if len(normalized) <= limit:
        return normalized
    return normalized[: limit - 3].rstrip() + "..."


def _rag_defaults() -> tuple[Path, str, Path]:
    from playscript_agent.rag import DEFAULT_DOCUMENT_DIR, DEFAULT_RULE_COLLECTION_NAME
    from playscript_agent.rag.ingest import DEFAULT_CHROMA_DIR

    return DEFAULT_DOCUMENT_DIR, DEFAULT_RULE_COLLECTION_NAME, DEFAULT_CHROMA_DIR


def _create_chroma_client(*, persist_directory: str | Path | None) -> Any:
    from playscript_agent.rag import create_chroma_client

    return create_chroma_client(persist_directory=persist_directory)


def _sentence_transformer_embedding_model() -> Any:
    from playscript_agent.rag import SentenceTransformerEmbeddingModel

    return SentenceTransformerEmbeddingModel()


def _ingest_rulebooks(*args: Any, **kwargs: Any) -> tuple[Any, Any]:
    from playscript_agent.rag import ingest_rulebooks

    return ingest_rulebooks(*args, **kwargs)


def _build_rule_retriever(*args: Any, **kwargs: Any) -> Any:
    from playscript_agent.rag import build_rule_retriever

    return build_rule_retriever(*args, **kwargs)


def _rule_access_context_cls() -> Any:
    from playscript_agent.rag import RuleAccessContext

    return RuleAccessContext
