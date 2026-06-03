from pathlib import Path
import unittest

from langgraph.types import Command

from playscript_agent.graph import build_game_graph, create_initial_state


DEMO_ROOT = Path(__file__).resolve().parents[1] / "scripts" / "demo"


class Stage1GraphTest(unittest.TestCase):
    def test_graph_interrupts_for_human_intro_then_reveals_truth(self) -> None:
        app = build_game_graph()
        config = {"configurable": {"thread_id": "stage1-flow"}}
        state = create_initial_state(
            script_root=str(DEMO_ROOT),
            human_player_id="lin_an",
            thread_id="stage1-flow",
            session_id="stage1-session",
        )

        interrupted = app.invoke(state, config)

        self.assertIn("__interrupt__", interrupted)
        prompt = interrupted["__interrupt__"][0].value
        self.assertEqual(prompt["type"], "player_introduction")
        self.assertEqual(prompt["participant_id"], "lin_an")
        self.assertEqual(interrupted["phase"], "introductions")
        self.assertFalse(interrupted["is_complete"])

        public_text = "\n".join(event["content"] for event in interrupted["public_events"])
        private_text = "\n".join(event["content"] for event in interrupted["private_events"])
        self.assertIn("午夜画廊", public_text)
        self.assertIn("请当前玩家", public_text)
        self.assertNotIn("凶手是赵宇", public_text)
        self.assertIn("保险柜半开", private_text)
        self.assertNotIn("欠沈知衡一笔钱", private_text)

        completed = app.invoke(Command(resume="我是林安，今晚我只想弄清真相。"), config)

        self.assertTrue(completed["is_complete"])
        self.assertEqual(completed["phase"], "complete")
        self.assertEqual(completed["turn_count"], 1)
        completed_text = "\n".join(event["content"] for event in completed["public_events"])
        self.assertIn("我是林安", completed_text)
        self.assertIn("凶手是赵宇", completed_text)


if __name__ == "__main__":
    unittest.main()
