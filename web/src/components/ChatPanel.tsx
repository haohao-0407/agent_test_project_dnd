import { FormEvent, useState } from "react";
import type { EventLogEntry } from "../api/types";
import { EventLog } from "./EventLog";

type ChatPanelProps = {
  events: EventLogEntry[];
  onSend: (message: string) => Promise<void>;
};

export function ChatPanel({ events, onSend }: ChatPanelProps) {
  const [message, setMessage] = useState("");
  const [isSending, setIsSending] = useState(false);
  const [sendError, setSendError] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    const text = message.trim();
    if (!text) return;
    setIsSending(true);
    setSendError(null);
    try {
      await onSend(text);
      setMessage("");
    } catch (error) {
      setSendError(error instanceof Error ? error.message : "发送失败");
    } finally {
      setIsSending(false);
    }
  }

  return (
    <section className="chat-panel" aria-labelledby="chat-title">
      <div className="panel-header">
        <div>
          <p className="eyebrow">DM</p>
          <h2 id="chat-title">行动与叙事</h2>
        </div>
      </div>
      <EventLog events={events} />
      <form className="chat-form" onSubmit={handleSubmit}>
        {sendError ? <p className="chat-error">{sendError}</p> : null}
        <input
          autoComplete="off"
          name="message"
          onChange={(event) => setMessage(event.target.value)}
          placeholder="描述你的行动"
          value={message}
        />
        <button disabled={isSending} type="submit">
          发送
        </button>
      </form>
    </section>
  );
}
