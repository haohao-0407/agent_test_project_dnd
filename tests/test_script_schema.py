from pathlib import Path
import unittest

from playscript_agent.script import load_script


DEMO_ROOT = Path(__file__).resolve().parents[1] / "scripts" / "demo"


class ScriptSchemaTest(unittest.TestCase):
    def test_demo_script_loads_as_valid_bundle(self) -> None:
        bundle = load_script(DEMO_ROOT)

        self.assertEqual(bundle.meta.script_id, "midnight-gallery")
        self.assertEqual({c.character_id for c in bundle.characters}, {"lin_an", "zhao_yu"})
        self.assertGreaterEqual(len(bundle.chunks), 10)
        self.assertEqual(
            {chunk.clue_id for chunk in bundle.chunks if chunk.clue_id},
            {"watch_crack", "resignation_letter", "silver_lighter"},
        )

    def test_chunks_export_chroma_metadata_with_empty_clue_sentinel(self) -> None:
        bundle = load_script(DEMO_ROOT)
        background = next(chunk for chunk in bundle.chunks if chunk.chunk_id == "background:public")

        self.assertEqual(background.chroma_metadata()["clue_id"], "")


if __name__ == "__main__":
    unittest.main()
