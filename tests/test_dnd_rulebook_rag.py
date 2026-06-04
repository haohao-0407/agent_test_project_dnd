from __future__ import annotations

from pathlib import Path

from playscript_agent.rag import (
    HashEmbeddingModel,
    RuleAccessContext,
    build_rule_retriever,
    create_chroma_client,
    ingest_rulebooks,
    load_rule_documents,
)
from playscript_agent.rag.filters import (
    build_rule_chroma_where_filter,
    metadata_matches_filter,
)
from playscript_agent.rag.rules import chunk_rule_documents


PROJECT_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_RULEBOOK = PROJECT_ROOT / "tests" / "fixtures" / "basic_rules.md"


def test_loads_and_chunks_text_rulebook():
    documents = load_rule_documents(FIXTURE_RULEBOOK)
    chunks = chunk_rule_documents(documents, chunk_size=120, chunk_overlap=20)

    assert len(documents) == 1
    assert chunks
    assert chunks[0].source == "basic_rules.md"
    assert chunks[0].page_start == 0
    assert chunks[0].chroma_metadata()["domain"] == "dnd_rules"
    assert chunks[0].chroma_metadata()["visibility"] == "public"


def test_rule_access_filter_excludes_dm_only_for_players():
    player_filter = build_rule_chroma_where_filter(
        RuleAccessContext.for_player("hero")
    )

    assert metadata_matches_filter(
        {"visibility": "public"},
        player_filter,
    )
    assert metadata_matches_filter(
        {"visibility": "character:hero"},
        player_filter,
    )
    assert not metadata_matches_filter(
        {"visibility": "dm_only"},
        player_filter,
    )
    assert not metadata_matches_filter(
        {"visibility": "character:other"},
        player_filter,
    )


def test_ingests_rulebook_into_chroma_and_retrieves_relevant_chunk():
    embedder = HashEmbeddingModel()

    collection, result = ingest_rulebooks(
        FIXTURE_RULEBOOK,
        client=create_chroma_client(persist_directory=None),
        collection_name="dnd_rules_test",
        embedding_model=embedder,
        persist_directory=None,
        chunk_size=180,
        chunk_overlap=20,
    )
    retriever = build_rule_retriever(
        collection,
        embedder,
        RuleAccessContext.for_player("hero"),
    )

    chunks = retriever.search("armor class attack roll", k=2)

    assert result.chunk_count >= 1
    assert collection.count() == result.chunk_count
    assert any("Armor Class" in chunk.content for chunk in chunks)
    assert all(Path(chunk.metadata["source"]).suffix == ".md" for chunk in chunks)
