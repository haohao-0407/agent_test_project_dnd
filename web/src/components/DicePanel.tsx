import { FormEvent, useState } from "react";
import type { DiceMode, DiceResult } from "../api/types";

type DicePanelProps = {
  selectedTokenId: string | null;
  onRoll: (input: {
    expression: string;
    reason: string;
    advantage: DiceMode;
    rollerId?: string | null;
  }) => Promise<DiceResult>;
};

export function DicePanel({ selectedTokenId, onRoll }: DicePanelProps) {
  const [expression, setExpression] = useState("1d20+3");
  const [reason, setReason] = useState("ability check");
  const [advantage, setAdvantage] = useState<DiceMode>("normal");
  const [lastResult, setLastResult] = useState<string>("等待投掷");

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    const result = await onRoll({
      expression,
      reason,
      advantage,
      rollerId: selectedTokenId || "manual"
    });
    setLastResult(`${result.expression} -> ${result.total} | rolls ${result.rolls.join(", ")}`);
  }

  return (
    <aside className="tool-panel" aria-labelledby="tool-title">
      <div className="panel-header">
        <div>
          <p className="eyebrow">Tools</p>
          <h2 id="tool-title">骰子</h2>
        </div>
      </div>
      <form className="dice-form" onSubmit={handleSubmit}>
        <label>
          <span>公式</span>
          <input value={expression} onChange={(event) => setExpression(event.target.value)} />
        </label>
        <label>
          <span>原因</span>
          <input value={reason} onChange={(event) => setReason(event.target.value)} />
        </label>
        <div className="segmented" aria-label="advantage mode">
          {(["normal", "advantage", "disadvantage"] as DiceMode[]).map((mode) => (
            <button
              className={advantage === mode ? "active" : ""}
              key={mode}
              onClick={() => setAdvantage(mode)}
              type="button"
            >
              {mode === "normal" ? "普通" : mode === "advantage" ? "优势" : "劣势"}
            </button>
          ))}
        </div>
        <button type="submit">掷骰</button>
      </form>
      <div className="dice-result">{lastResult}</div>
    </aside>
  );
}
