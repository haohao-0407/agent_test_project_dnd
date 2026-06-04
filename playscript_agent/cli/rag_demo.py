from __future__ import annotations

import argparse
from pathlib import Path

from playscript_agent.rag import (
    HashEmbeddingModel,
    SentenceTransformerEmbeddingModel,
    build_scoped_retriever,
    create_chroma_client,
    ingest_script,
)
from playscript_agent.script import AccessContext


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a stage-2 scoped RAG demo.")
    parser.add_argument(
        "--script-root",
        default=str(Path(__file__).resolve().parents[2] / "scripts" / "demo"),
    )
    parser.add_argument("--query", default="怀表 蓝色 油彩 真相")
    parser.add_argument("--player-id", default="lin_an")
    parser.add_argument("--phase", type=int, default=1)
    parser.add_argument("--revealed", nargs="*", default=["watch_crack"])
    parser.add_argument("--dm", action="store_true", help="Use DM all-seeing scope.")
    parser.add_argument(
        "--real-embedding",
        action="store_true",
        help="Use sentence-transformers instead of fast hash embeddings.",
    )
    args = parser.parse_args()

    embedder = (
        SentenceTransformerEmbeddingModel()
        if args.real_embedding
        else HashEmbeddingModel()
    )
    client = None if args.real_embedding else create_chroma_client(persist_directory=None)
    ingest_kwargs = {
        "client": client,
        "collection_name": (
            "playscript_chunks_bge_small_zh_v1_5"
            if args.real_embedding
            else "playscript_chunks_hash_demo"
        ),
        "embedding_model": embedder,
    }
    if not args.real_embedding:
        ingest_kwargs["persist_directory"] = None
    collection, result = ingest_script(args.script_root, **ingest_kwargs)
    context = (
        AccessContext.for_dm()
        if args.dm
        else AccessContext.for_player(
            args.player_id,
            current_phase=args.phase,
            revealed_clues=args.revealed,
        )
    )
    retriever = build_scoped_retriever(collection, embedder, context)
    chunks = retriever.search(args.query, k=5)

    print(f"ingested: {result.chunk_count} chunks -> {result.collection_name}")
    print(f"scope: {'dm' if args.dm else args.player_id}")
    for index, chunk in enumerate(chunks, start=1):
        title = chunk.metadata.get("title", chunk.chunk_id)
        visibility = chunk.metadata.get("visibility", "")
        clue_id = chunk.metadata.get("clue_id", "")
        print(f"\n{index}. {title} [{visibility} clue={clue_id}]")
        print(chunk.content)


if __name__ == "__main__":
    main()
