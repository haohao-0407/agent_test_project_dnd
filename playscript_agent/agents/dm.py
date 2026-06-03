from __future__ import annotations

from dataclasses import dataclass

from playscript_agent.script.schema import ScriptBundle, ScriptChunk


@dataclass(frozen=True, slots=True)
class DeterministicDM:
    """Offline DM used until a real LLM is configured.

    It keeps phase 1 runnable without API keys while preserving the future
    boundary: graph nodes ask a DM object for narration instead of hard-coding
    every sentence.
    """

    def opening(self, script: ScriptBundle) -> str:
        background = _one_chunk(script, "background:public")
        public_profiles = [
            f"{character.name}：{character.public_profile}"
            for character in script.characters
        ]
        return "\n".join(
            [
                f"欢迎来到《{script.meta.title}》。",
                background.content.strip(),
                "在场角色：",
                *public_profiles,
                "请当前玩家用角色身份做简短自我介绍。",
            ]
        )

    def reveal(self, script: ScriptBundle) -> str:
        truth = next(chunk for chunk in script.chunks if chunk.content_type == "truth")
        return "\n".join(
            [
                "复盘时间到。",
                truth.content.strip(),
            ]
        )


def _one_chunk(script: ScriptBundle, chunk_id: str) -> ScriptChunk:
    return next(chunk for chunk in script.chunks if chunk.chunk_id == chunk_id)
