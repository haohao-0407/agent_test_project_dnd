from __future__ import annotations

import argparse
from pathlib import Path

from playscript_agent.rag import (
    DEFAULT_DOCUMENT_DIR,
    DEFAULT_RULE_COLLECTION_NAME,
    HashEmbeddingModel,
    RuleAccessContext,
    SentenceTransformerEmbeddingModel,
    build_rule_retriever,
    create_chroma_client,
    ingest_rulebooks,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a DND rulebook RAG demo.")
    parser.add_argument(
        "--document-root",
        default=str(DEFAULT_DOCUMENT_DIR),
        help="Rulebook file or directory. Defaults to the project document folder.",
    )
    parser.add_argument("--query", default="How does armor class work?")
    parser.add_argument("--player-id", default="player")
    parser.add_argument("--dm", action="store_true", help="Use DM all-seeing scope.")
    parser.add_argument(
        "--real-embedding",
        action="store_true",
        help="Use sentence-transformers instead of fast hash embeddings.",
    )
    parser.add_argument("--k", type=int, default=5)
    args = parser.parse_args()

    embedder = (
        SentenceTransformerEmbeddingModel()
        if args.real_embedding
        else HashEmbeddingModel()
    )
    client = None if args.real_embedding else create_chroma_client(persist_directory=None)
    collection_name = (
        DEFAULT_RULE_COLLECTION_NAME
        if args.real_embedding
        else "dnd_rule_chunks_hash_demo"
    )
    ingest_kwargs = {
        "client": client,
        "collection_name": collection_name,
        "embedding_model": embedder,
        "paths": Path(args.document_root),
    }
    if not args.real_embedding:
        ingest_kwargs["persist_directory"] = None

    collection, result = ingest_rulebooks(**ingest_kwargs)
    context = (
        RuleAccessContext.for_dm()
        if args.dm
        else RuleAccessContext.for_player(args.player_id)
    )
    retriever = build_rule_retriever(collection, embedder, context)
    chunks = retriever.search(args.query, k=args.k)

    print(f"ingested: {result.chunk_count} chunks -> {result.collection_name}")
    print(f"scope: {'dm' if args.dm else args.player_id}")
    for index, chunk in enumerate(chunks, start=1):
        source = chunk.metadata.get("source", "")
        page = chunk.metadata.get("page_start", "")
        section = chunk.metadata.get("section", "")
        visibility = chunk.metadata.get("visibility", "")
        print(f"\n{index}. {source} p.{page} [{visibility}] {section}")
        print(chunk.content)


if __name__ == "__main__":
    main()
