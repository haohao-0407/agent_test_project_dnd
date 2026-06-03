from pathlib import Path
import unittest

from playscript_agent.guard.output import assert_output_visible, find_output_violations
from playscript_agent.script import AccessContext, load_script


DEMO_ROOT = Path(__file__).resolve().parents[1] / "scripts" / "demo"


class OutputGuardTest(unittest.TestCase):
    def setUp(self) -> None:
        self.bundle = load_script(DEMO_ROOT)

    def test_player_output_cannot_include_hidden_truth_marker(self) -> None:
        context = AccessContext.for_player("lin_an", current_phase=1, revealed_clues={"watch_crack"})
        text = "我觉得真相是：凶手是赵宇。"

        violations = find_output_violations(text, self.bundle.chunks, context)

        self.assertEqual([violation.chunk_id for violation in violations], ["truth:solution"])

    def test_visible_public_clue_can_be_mentioned_after_reveal(self) -> None:
        context = AccessContext.for_player("lin_an", current_phase=1, revealed_clues={"watch_crack"})
        text = "碎裂怀表停在八点四十二分，这一点很关键。"

        assert_output_visible(text, self.bundle.chunks, context)


if __name__ == "__main__":
    unittest.main()
