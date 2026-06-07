from __future__ import annotations

import shutil
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
from playscript_agent.api.services import rag_service


PROJECT_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_RULEBOOK = PROJECT_ROOT / "tests" / "fixtures" / "basic_rules.md"
TEST_TMP_ROOT = PROJECT_ROOT / ".tmp_tests"


def test_loads_and_chunks_text_rulebook():
    documents = load_rule_documents(FIXTURE_RULEBOOK)
    chunks = chunk_rule_documents(documents, chunk_size=120, chunk_overlap=20)

    assert len(documents) == 1
    assert chunks
    assert chunks[0].source == "basic_rules.md"
    assert chunks[0].page_start == 0
    assert chunks[0].chroma_metadata()["domain"] == "dnd_rules"
    assert chunks[0].chroma_metadata()["visibility"] == "public"


def test_csv_reference_tables_are_chunked_by_entry_and_xlsx_duplicates_are_ignored():
    document_root = _fresh_test_dir("csv_reference_tables") / "document"
    document_root.mkdir(parents=True)
    (document_root / "spells.xlsx").write_bytes(b"duplicate spreadsheet source")
    (document_root / "spells.csv").write_text(
        (
            "名称,来源,文本\n"
            '魔法飞弹,PHB,"你创造三枚闪光飞镖。\n'
            '每枚飞镖击中一个你选择的生物。"\n'
            "护盾术,PHB,直到你下一回合开始你获得 AC 加值。\n"
        ),
        encoding="utf-8",
    )

    documents = load_rule_documents(document_root)
    chunks = chunk_rule_documents(documents, chunk_size=20, chunk_overlap=5)

    assert len(documents) == 1
    assert documents[0].source_path.name == "spells.csv"
    assert documents[0].document_type == "rules_reference_table"
    assert len(chunks) == 2
    assert chunks[0].section == "魔法飞弹"
    assert "每枚飞镖击中一个你选择的生物" in chunks[0].content
    assert chunks[0].chroma_metadata()["type"] == "rules_reference_table"


def test_module_documents_default_to_dm_only_scope():
    document_root = _fresh_test_dir("module_scope") / "document"
    module_dir = document_root / "modules" / "lost_mine"
    module_dir.mkdir(parents=True)
    module_path = module_dir / "lost_mine.md"
    module_path.write_text(
        "# Lost Mine\n\nThe Black Spider keeps a secret map in Cragmaw Castle.",
        encoding="utf-8",
    )

    documents = load_rule_documents(document_root)

    assert len(documents) == 1
    assert documents[0].document_type == "module_dm_only"
    assert documents[0].visibility == "dm_only"


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


def test_module_dm_only_chunks_are_hidden_from_player_retrieval():
    document_root = _fresh_test_dir("module_retrieval") / "document"
    module_dir = document_root / "modules" / "lost_mine"
    module_dir.mkdir(parents=True)
    (document_root / "rules.md").write_text(
        "# Basic Rules\n\nArmor Class protects a creature from attack rolls.",
        encoding="utf-8",
    )
    (module_dir / "lost_mine.md").write_text(
        "# Lost Mine\n\nThe Black Spider hides in Wave Echo Cave with a secret map.",
        encoding="utf-8",
    )
    embedder = HashEmbeddingModel()
    collection, result = ingest_rulebooks(
        document_root,
        client=create_chroma_client(persist_directory=None),
        collection_name="dnd_rules_with_module_test",
        embedding_model=embedder,
        persist_directory=None,
        chunk_size=160,
        chunk_overlap=20,
    )

    player_retriever = build_rule_retriever(
        collection,
        embedder,
        RuleAccessContext.for_player("kael"),
    )
    dm_retriever = build_rule_retriever(collection, embedder, RuleAccessContext.for_dm())

    player_chunks = player_retriever.search("Black Spider Wave Echo secret map", k=5)
    dm_chunks = dm_retriever.search("Black Spider Wave Echo secret map", k=5)

    assert result.chunk_count >= 2
    assert all(chunk.metadata["visibility"] != "dm_only" for chunk in player_chunks)
    assert any(chunk.metadata["visibility"] == "dm_only" for chunk in dm_chunks)


def _fresh_test_dir(name: str) -> Path:
    path = TEST_TMP_ROOT / name
    shutil.rmtree(path, ignore_errors=True)
    path.mkdir(parents=True, exist_ok=True)
    return path


def test_backend_rule_rag_reuses_cached_and_persisted_index(monkeypatch):
    document_root = _fresh_test_dir("backend_rule_rag_reuse") / "document"
    persist_directory = document_root.parent / "chroma"
    document_root.mkdir(parents=True)
    (document_root / "rules.md").write_text(
        "# Basic Rules\n\nArmor Class protects a creature from attack rolls.",
        encoding="utf-8",
    )
    embedder = HashEmbeddingModel()
    collection_name = "backend_rule_rag_reuse_test"
    ingest_calls: list[int] = []
    real_ingest = rag_service._ingest_rulebooks

    def counting_ingest(*args, **kwargs):
        ingest_calls.append(1)
        return real_ingest(*args, **kwargs)

    rag_service.reset_rule_rag_cache()
    monkeypatch.setattr(rag_service, "_ingest_rulebooks", counting_ingest)
    monkeypatch.setattr(
        rag_service,
        "_rule_access_context_for_user",
        lambda user_id: RuleAccessContext.for_player("kael"),
    )
    try:
        first_chunks = rag_service.search_rules(
            "armor class attack roll",
            user_id="player-kael",
            document_root=document_root,
            collection_name=collection_name,
            embedding_model=embedder,
            persist_directory=persist_directory,
        )
        second_chunks = rag_service.search_rules(
            "armor class",
            user_id="player-kael",
            document_root=document_root,
            collection_name=collection_name,
            embedding_model=embedder,
            persist_directory=persist_directory,
        )

        assert first_chunks
        assert second_chunks
        assert len(ingest_calls) == 1

        def fail_ingest(*args, **kwargs):
            raise AssertionError("existing persisted rule index should be reused")

        rag_service.reset_rule_rag_cache()
        monkeypatch.setattr(rag_service, "_ingest_rulebooks", fail_ingest)
        persisted_chunks = rag_service.search_rules(
            "armor class",
            user_id="player-kael",
            document_root=document_root,
            collection_name=collection_name,
            embedding_model=embedder,
            persist_directory=persist_directory,
        )

        assert persisted_chunks
    finally:
        rag_service.reset_rule_rag_cache()


def test_backend_rule_rag_rebuilds_persisted_index_when_sources_change(monkeypatch):
    document_root = _fresh_test_dir("backend_rule_rag_source_change") / "document"
    persist_directory = document_root.parent / "chroma"
    document_root.mkdir(parents=True)
    rulebook_path = document_root / "rules.md"
    rulebook_path.write_text(
        "# Armor\n\nArmor Class protects a creature from attack rolls.",
        encoding="utf-8",
    )
    embedder = HashEmbeddingModel()
    collection_name = "backend_rule_rag_source_change_test"
    ingest_calls: list[int] = []
    real_ingest = rag_service._ingest_rulebooks

    def counting_ingest(*args, **kwargs):
        ingest_calls.append(1)
        return real_ingest(*args, **kwargs)

    monkeypatch.setattr(rag_service, "_ingest_rulebooks", counting_ingest)
    monkeypatch.setattr(
        rag_service,
        "_rule_access_context_for_user",
        lambda user_id: RuleAccessContext.for_player("kael"),
    )
    rag_service.reset_rule_rag_cache()
    try:
        armor_chunks = rag_service.search_rules(
            "armor class",
            user_id="player-kael",
            document_root=document_root,
            collection_name=collection_name,
            embedding_model=embedder,
            persist_directory=persist_directory,
        )

        rulebook_path.write_text(
            "# Stealth\n\nStealth checks help a hidden creature avoid notice.",
            encoding="utf-8",
        )
        rag_service.reset_rule_rag_cache()
        stealth_chunks = rag_service.search_rules(
            "stealth hidden notice",
            user_id="player-kael",
            document_root=document_root,
            collection_name=collection_name,
            embedding_model=embedder,
            persist_directory=persist_directory,
        )

        assert any("Armor Class" in chunk.content for chunk in armor_chunks)
        assert any("Stealth checks" in chunk.content for chunk in stealth_chunks)
        assert len(ingest_calls) == 2
    finally:
        rag_service.reset_rule_rag_cache()
