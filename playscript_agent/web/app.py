from __future__ import annotations

import argparse
import json
import mimetypes
import random
import re
from copy import deepcopy
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Literal, TypedDict


STATIC_ROOT = Path(__file__).resolve().parent / "static"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765
DICE_PATTERN = re.compile(r"^\s*(?:(\d*)d(\d+))\s*([+-]\s*\d+)?\s*$", re.IGNORECASE)

ToolName = Literal["roll_dice"]


class ToolCall(TypedDict):
    name: ToolName
    arguments: dict[str, Any]


GAME_STATE: dict[str, Any] = {
    "session": {
        "id": "demo-dnd-session",
        "title": "灰烬边境",
        "mode": "exploration",
        "round": 1,
        "currentTurn": "kael",
    },
    "map": {
        "id": "roadside-ruin",
        "name": "废弃驿站",
        "width": 12,
        "height": 8,
        "gridSize": 48,
        "terrain": [
            {"x": 4, "y": 1, "type": "wall"},
            {"x": 5, "y": 1, "type": "wall"},
            {"x": 6, "y": 1, "type": "wall"},
            {"x": 4, "y": 2, "type": "wall"},
            {"x": 7, "y": 2, "type": "wall"},
            {"x": 2, "y": 5, "type": "water"},
            {"x": 3, "y": 5, "type": "water"},
            {"x": 9, "y": 4, "type": "difficult"},
            {"x": 10, "y": 4, "type": "difficult"},
        ],
        "annotations": [
            {"x": 6, "y": 3, "label": "破门"},
            {"x": 10, "y": 6, "label": "火光"},
        ],
    },
    "tokens": [
        {"id": "kael", "name": "凯尔", "kind": "player", "x": 2, "y": 3},
        {"id": "mira", "name": "米拉", "kind": "player", "x": 3, "y": 4},
        {"id": "goblin-1", "name": "地精", "kind": "monster", "x": 8, "y": 3},
        {"id": "wolf-1", "name": "座狼", "kind": "monster", "x": 9, "y": 5},
    ],
    "characters": [
        {
            "id": "kael",
            "name": "凯尔",
            "class": "战士 3",
            "race": "人类",
            "hp": {"current": 24, "max": 30, "temp": 0},
            "ac": 17,
            "speed": 30,
            "attributes": {"STR": 16, "DEX": 12, "CON": 14, "INT": 10, "WIS": 11, "CHA": 9},
            "skills": ["运动", "威吓", "察觉"],
            "attacks": ["长剑 +5 1d8+3", "短弓 +3 1d6+1"],
            "conditions": [],
        },
        {
            "id": "mira",
            "name": "米拉",
            "class": "法师 3",
            "race": "高等精灵",
            "hp": {"current": 15, "max": 18, "temp": 0},
            "ac": 13,
            "speed": 30,
            "attributes": {"STR": 8, "DEX": 14, "CON": 12, "INT": 17, "WIS": 13, "CHA": 11},
            "skills": ["奥秘", "调查", "历史"],
            "attacks": ["火焰箭 +5 1d10", "匕首 +4 1d4+2"],
            "conditions": ["专注"],
        },
    ],
    "events": [
        {
            "type": "dm",
            "speaker": "DM",
            "text": "雨停后，废弃驿站只剩半堵墙和一扇被火熏黑的门。远处有低沉的喘息声。",
            "time": "12:00",
        }
    ],
}


class DndWebHandler(BaseHTTPRequestHandler):
    server_version = "DndAgentWeb/0.1"

    def do_GET(self) -> None:
        if self.path in {"/", "/index.html"}:
            self._send_file(STATIC_ROOT / "index.html")
            return
        if self.path == "/api/state":
            self._send_json(snapshot_state())
            return
        if self.path.startswith("/static/"):
            relative = self.path.removeprefix("/static/").split("?", 1)[0]
            self._send_file(STATIC_ROOT / relative)
            return
        self._send_json({"error": "not found"}, status=HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:
        try:
            payload = self._read_json()
            if self.path == "/api/dice":
                self._send_json(handle_dice(payload))
                return
            if self.path == "/api/token/move":
                self._send_json(handle_token_move(payload))
                return
            if self.path == "/api/chat":
                self._send_json(handle_chat(payload))
                return
        except ValueError as error:
            self._send_json({"error": str(error)}, status=HTTPStatus.BAD_REQUEST)
            return
        self._send_json({"error": "not found"}, status=HTTPStatus.NOT_FOUND)

    def log_message(self, format: str, *args: Any) -> None:
        return

    def _read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        if length == 0:
            return {}
        raw = self.rfile.read(length)
        return json.loads(raw.decode("utf-8"))

    def _send_json(self, data: dict[str, Any], *, status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, path: Path) -> None:
        resolved = path.resolve()
        if not str(resolved).startswith(str(STATIC_ROOT.resolve())) or not resolved.is_file():
            self._send_json({"error": "not found"}, status=HTTPStatus.NOT_FOUND)
            return
        content_type = mimetypes.guess_type(str(resolved))[0] or "application/octet-stream"
        body = resolved.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def snapshot_state() -> dict[str, Any]:
    return deepcopy(GAME_STATE)


def handle_dice(payload: dict[str, Any]) -> dict[str, Any]:
    result = roll_dice(
        str(payload.get("expression", "1d20")),
        reason=str(payload.get("reason", "manual roll")),
        roller_id=payload.get("rollerId"),
        advantage=str(payload.get("advantage", "normal")),
    )
    append_event(
        {
            "type": "dice",
            "speaker": "Dice",
            "text": f"{result['expression']} = {result['total']} ({result['reason']})",
            "result": result,
        }
    )
    return {"result": result, "state": snapshot_state()}


def handle_token_move(payload: dict[str, Any]) -> dict[str, Any]:
    token_id = str(payload.get("tokenId", ""))
    x = int(payload.get("x"))
    y = int(payload.get("y"))
    if not (0 <= x < GAME_STATE["map"]["width"] and 0 <= y < GAME_STATE["map"]["height"]):
        raise ValueError("target square is outside the map")
    if _terrain_at(x, y) == "wall":
        raise ValueError("target square is blocked")

    token = _find_token(token_id)
    token["x"] = x
    token["y"] = y
    append_event(
        {
            "type": "system",
            "speaker": "Map",
            "text": f"{token['name']} moved to ({x + 1}, {y + 1}).",
        }
    )
    return {"state": snapshot_state()}


def handle_chat(payload: dict[str, Any]) -> dict[str, Any]:
    message = str(payload.get("message", "")).strip()
    if not message:
        raise ValueError("message is required")

    speaker = str(payload.get("speaker", "玩家"))
    append_event({"type": "player", "speaker": speaker, "text": message})

    tool_calls = plan_tool_calls(message, speaker=speaker)
    tool_results = [execute_tool_call(tool_call) for tool_call in tool_calls]
    append_event({"type": "dm", "speaker": "DM", "text": build_result_message(tool_results)})
    return {"toolCalls": tool_calls, "toolResults": tool_results, "state": snapshot_state()}


def plan_tool_calls(message: str, *, speaker: str) -> list[ToolCall]:
    lower_message = message.lower()
    if any(keyword in lower_message for keyword in ["attack", "攻击", "射击"]):
        return [
            {
                "name": "roll_dice",
                "arguments": {
                    "expression": "1d20+5",
                    "reason": "attack roll",
                    "roller_id": speaker,
                    "advantage": "normal",
                },
            }
        ]
    if any(keyword in lower_message for keyword in ["check", "调查", "侦查", "观察", "检定"]):
        return [
            {
                "name": "roll_dice",
                "arguments": {
                    "expression": "1d20+3",
                    "reason": "ability check",
                    "roller_id": speaker,
                    "advantage": "normal",
                },
            }
        ]
    return []


def execute_tool_call(tool_call: ToolCall) -> dict[str, Any]:
    if tool_call["name"] != "roll_dice":
        raise ValueError(f"unsupported tool call: {tool_call['name']}")

    arguments = tool_call["arguments"]
    dice_result = roll_dice(
        str(arguments["expression"]),
        reason=str(arguments["reason"]),
        roller_id=arguments.get("roller_id"),
        advantage=str(arguments.get("advantage", "normal")),
    )
    append_event(
        {
            "type": "dice",
            "speaker": "Dice",
            "text": f"{dice_result['expression']} = {dice_result['total']} ({dice_result['reason']})",
            "result": dice_result,
        }
    )
    return {"name": "roll_dice", "result": dice_result}


def build_result_message(tool_results: list[dict[str, Any]]) -> str:
    if not tool_results:
        return "行动已记录。"

    parts = []
    for tool_result in tool_results:
        if tool_result["name"] == "roll_dice":
            result = tool_result["result"]
            parts.append(f"{result['expression']} 结果为 {result['total']}")
    return "；".join(parts) + "。"


def roll_dice(
    expression: str,
    *,
    reason: str,
    roller_id: str | None = None,
    advantage: str = "normal",
) -> dict[str, Any]:
    match = DICE_PATTERN.match(expression)
    if not match:
        raise ValueError("dice expression must look like 1d20+5")

    count = int(match.group(1) or "1")
    sides = int(match.group(2))
    modifier = int((match.group(3) or "0").replace(" ", ""))
    if count < 1 or count > 50:
        raise ValueError("dice count must be between 1 and 50")
    if sides < 2 or sides > 1000:
        raise ValueError("dice sides must be between 2 and 1000")
    if advantage not in {"normal", "advantage", "disadvantage"}:
        raise ValueError("advantage must be normal, advantage, or disadvantage")

    kept_rolls: list[int]
    all_rolls: list[int]
    if advantage != "normal" and count == 1 and sides == 20:
        all_rolls = [random.randint(1, 20), random.randint(1, 20)]
        kept_rolls = [max(all_rolls) if advantage == "advantage" else min(all_rolls)]
    else:
        all_rolls = [random.randint(1, sides) for _ in range(count)]
        kept_rolls = all_rolls

    return {
        "expression": expression,
        "rolls": all_rolls,
        "kept": kept_rolls,
        "modifier": modifier,
        "total": sum(kept_rolls) + modifier,
        "reason": reason,
        "rollerId": roller_id,
        "advantage": advantage,
        "time": current_time(),
    }


def append_event(event: dict[str, Any]) -> None:
    event.setdefault("time", current_time())
    GAME_STATE["events"].append(event)
    GAME_STATE["events"] = GAME_STATE["events"][-80:]


def current_time() -> str:
    return datetime.now(timezone.utc).astimezone().strftime("%H:%M")


def _find_token(token_id: str) -> dict[str, Any]:
    for token in GAME_STATE["tokens"]:
        if token["id"] == token_id:
            return token
    raise ValueError(f"unknown token: {token_id}")


def _terrain_at(x: int, y: int) -> str | None:
    for terrain in GAME_STATE["map"]["terrain"]:
        if terrain["x"] == x and terrain["y"] == y:
            return terrain["type"]
    return None


def run(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT) -> None:
    server = ThreadingHTTPServer((host, port), DndWebHandler)
    print(f"DND web tabletop running at http://{host}:{port}")
    server.serve_forever()


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the DND web tabletop.")
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    args = parser.parse_args()
    run(host=args.host, port=args.port)


if __name__ == "__main__":
    main()
