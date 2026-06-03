from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Iterable

from playscript_agent.guard.policy import filter_hidden_chunks
from playscript_agent.script.schema import AccessContext, ScriptChunk


@dataclass(frozen=True, slots=True)
class OutputViolation:
    chunk_id: str
    title: str
    reason: str


def find_output_violations(
    text: str,
    protected_chunks: Iterable[ScriptChunk],
    context: AccessContext,
) -> list[OutputViolation]:
    """Flag obvious exact leaks of hidden stage-0 script content.

    This is intentionally conservative. The later LLM-facing guard can become
    semantic, but stage 0 only needs deterministic checks for known demo data.
    """

    normalized_text = _normalize(text)
    violations: list[OutputViolation] = []
    for chunk in filter_hidden_chunks(protected_chunks, context):
        for marker in _leak_markers(chunk):
            if marker and _normalize(marker) in normalized_text:
                violations.append(
                    OutputViolation(
                        chunk_id=chunk.chunk_id,
                        title=chunk.title,
                        reason="output contains hidden script marker",
                    )
                )
                break
    return violations


def assert_output_visible(
    text: str,
    protected_chunks: Iterable[ScriptChunk],
    context: AccessContext,
) -> None:
    violations = find_output_violations(text, protected_chunks, context)
    if violations:
        details = ", ".join(violation.chunk_id for violation in violations)
        raise PermissionError(f"output leaks hidden chunks: {details}")


def _leak_markers(chunk: ScriptChunk) -> list[str]:
    markers = [chunk.title.strip()]
    content = chunk.content.strip()
    if len(content) <= 80:
        markers.append(content)
    else:
        markers.append(content[:80])
    return markers


def _normalize(text: str) -> str:
    return "".join(text.lower().split())
