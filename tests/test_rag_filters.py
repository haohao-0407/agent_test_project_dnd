from pathlib import Path
import unittest

from playscript_agent.guard.policy import filter_visible_chunks
from playscript_agent.rag.filters import build_chroma_where_filter, metadata_matches_filter
from playscript_agent.script import AccessContext, load_script


DEMO_ROOT = Path(__file__).resolve().parents[1] / "scripts" / "demo"


class RagFiltersTest(unittest.TestCase):
    def setUp(self) -> None:
        self.bundle = load_script(DEMO_ROOT)

    def test_dm_can_see_all_chunks(self) -> None:
        context = AccessContext.for_dm()

        self.assertEqual(filter_visible_chunks(self.bundle.chunks, context), list(self.bundle.chunks))
        self.assertEqual(build_chroma_where_filter(context), {})

    def test_player_starts_with_public_and_own_profile_only(self) -> None:
        context = AccessContext.for_player("lin_an", current_phase=0)

        visible_ids = {chunk.chunk_id for chunk in filter_visible_chunks(self.bundle.chunks, context)}

        self.assertIn("background:public", visible_ids)
        self.assertIn("character:lin_an:private", visible_ids)
        self.assertNotIn("character:zhao_yu:private", visible_ids)
        self.assertNotIn("truth:solution", visible_ids)
        self.assertNotIn("clue:watch_crack", visible_ids)

    def test_revealed_public_clue_becomes_visible_in_phase(self) -> None:
        context = AccessContext.for_player(
            "lin_an",
            current_phase=1,
            revealed_clues={"watch_crack"},
        )

        visible_ids = {chunk.chunk_id for chunk in filter_visible_chunks(self.bundle.chunks, context)}

        self.assertIn("clue:watch_crack", visible_ids)
        self.assertNotIn("clue:resignation_letter", visible_ids)
        self.assertNotIn("clue:silver_lighter", visible_ids)

    def test_revealed_character_clue_is_visible_only_to_owner(self) -> None:
        lin_context = AccessContext.for_player(
            "lin_an",
            current_phase=1,
            revealed_clues={"resignation_letter"},
        )
        zhao_context = AccessContext.for_player(
            "zhao_yu",
            current_phase=1,
            revealed_clues={"resignation_letter"},
        )

        lin_visible = {chunk.chunk_id for chunk in filter_visible_chunks(self.bundle.chunks, lin_context)}
        zhao_visible = {chunk.chunk_id for chunk in filter_visible_chunks(self.bundle.chunks, zhao_context)}

        self.assertIn("clue:resignation_letter", lin_visible)
        self.assertNotIn("clue:resignation_letter", zhao_visible)

    def test_generated_chroma_filter_matches_policy_results(self) -> None:
        context = AccessContext.for_player(
            "zhao_yu",
            current_phase=1,
            revealed_clues={"watch_crack", "silver_lighter"},
        )
        where_filter = build_chroma_where_filter(context)

        policy_ids = {chunk.chunk_id for chunk in filter_visible_chunks(self.bundle.chunks, context)}
        metadata_ids = {
            chunk.chunk_id
            for chunk in self.bundle.chunks
            if metadata_matches_filter(chunk.chroma_metadata(), where_filter)
        }

        self.assertEqual(metadata_ids, policy_ids)


if __name__ == "__main__":
    unittest.main()
