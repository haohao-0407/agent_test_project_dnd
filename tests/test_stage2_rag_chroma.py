from pathlib import Path
import unittest

from playscript_agent.rag import (
    HashEmbeddingModel,
    build_scoped_retriever,
    create_chroma_client,
    ingest_script,
)
from playscript_agent.script import AccessContext


DEMO_ROOT = Path(__file__).resolve().parents[1] / "scripts" / "demo"


class Stage2ChromaRagTest(unittest.TestCase):
    def setUp(self) -> None:
        self.embedder = HashEmbeddingModel()
        self.collection, self.result = ingest_script(
            DEMO_ROOT,
            client=create_chroma_client(persist_directory=None),
            collection_name="stage2_test",
            embedding_model=self.embedder,
            persist_directory=None,
        )

    def test_ingest_writes_all_demo_chunks(self) -> None:
        self.assertEqual(self.result.chunk_count, 11)
        self.assertEqual(self.collection.count(), 11)

    def test_dm_retriever_can_search_truth(self) -> None:
        retriever = build_scoped_retriever(
            self.collection,
            self.embedder,
            AccessContext.for_dm(),
        )

        chunks = retriever.search("凶手 赵宇 真相", k=10)
        chunk_ids = {chunk.chunk_id for chunk in chunks}

        self.assertIn("truth:solution", chunk_ids)

    def test_player_retriever_excludes_hidden_truth_and_other_private_chunks(self) -> None:
        retriever = build_scoped_retriever(
            self.collection,
            self.embedder,
            AccessContext.for_player(
                "lin_an",
                current_phase=1,
                revealed_clues={"watch_crack"},
            ),
        )

        chunks = retriever.search("赵宇 打火机 真相 辞职信 怀表", k=10)
        chunk_ids = {chunk.chunk_id for chunk in chunks}

        self.assertIn("clue:watch_crack", chunk_ids)
        self.assertIn("character:lin_an:private", chunk_ids)
        self.assertNotIn("truth:solution", chunk_ids)
        self.assertNotIn("character:zhao_yu:private", chunk_ids)
        self.assertNotIn("clue:silver_lighter", chunk_ids)

    def test_revealed_character_clue_is_scoped_to_owner(self) -> None:
        lin_retriever = build_scoped_retriever(
            self.collection,
            self.embedder,
            AccessContext.for_player(
                "lin_an",
                current_phase=1,
                revealed_clues={"resignation_letter"},
            ),
        )
        zhao_retriever = build_scoped_retriever(
            self.collection,
            self.embedder,
            AccessContext.for_player(
                "zhao_yu",
                current_phase=1,
                revealed_clues={"resignation_letter"},
            ),
        )

        lin_ids = {chunk.chunk_id for chunk in lin_retriever.search("辞职信", k=10)}
        zhao_ids = {chunk.chunk_id for chunk in zhao_retriever.search("辞职信", k=10)}

        self.assertIn("clue:resignation_letter", lin_ids)
        self.assertNotIn("clue:resignation_letter", zhao_ids)


if __name__ == "__main__":
    unittest.main()
