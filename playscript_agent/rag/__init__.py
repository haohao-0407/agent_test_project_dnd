"""RAG helpers for deterministic visibility filters and Chroma retrieval."""

from playscript_agent.rag.embeddings import (
    EmbeddingModel,
    HashEmbeddingModel,
    SentenceTransformerEmbeddingModel,
)
from playscript_agent.rag.filters import RuleAccessContext
from playscript_agent.rag.ingest import IngestResult, create_chroma_client, ingest_script
from playscript_agent.rag.retrievers import (
    RetrievedChunk,
    RuleRetriever,
    ScopedRetriever,
    build_rule_retriever,
    build_scoped_retriever,
)
from playscript_agent.rag.rules import (
    DEFAULT_DOCUMENT_DIR,
    DEFAULT_MODULE_DIR,
    DEFAULT_RULE_COLLECTION_NAME,
    RuleChunk,
    RuleDocument,
    RulePage,
    chunk_rule_document,
    chunk_rule_documents,
    ingest_rulebooks,
    load_rule_document,
    load_rule_documents,
)

__all__ = [
    "DEFAULT_DOCUMENT_DIR",
    "DEFAULT_MODULE_DIR",
    "DEFAULT_RULE_COLLECTION_NAME",
    "EmbeddingModel",
    "HashEmbeddingModel",
    "IngestResult",
    "RetrievedChunk",
    "RuleAccessContext",
    "RuleChunk",
    "RuleDocument",
    "RulePage",
    "RuleRetriever",
    "ScopedRetriever",
    "SentenceTransformerEmbeddingModel",
    "build_rule_retriever",
    "build_scoped_retriever",
    "chunk_rule_document",
    "chunk_rule_documents",
    "create_chroma_client",
    "ingest_rulebooks",
    "ingest_script",
    "load_rule_document",
    "load_rule_documents",
]
