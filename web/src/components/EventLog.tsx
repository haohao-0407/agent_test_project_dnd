import { useEffect, useRef } from "react";
import type { EventLogEntry } from "../api/types";

type EventLogProps = {
  events: EventLogEntry[];
};

export function EventLog({ events }: EventLogProps) {
  const logRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (logRef.current) {
      logRef.current.scrollTop = logRef.current.scrollHeight;
    }
  }, [events]);

  return (
    <div className="event-log" aria-live="polite" ref={logRef}>
      {events.map((event, index) => (
        <article className={`event ${event.type}`} key={`${event.time}-${index}`}>
          <div className="event-meta">
            <span>{event.speaker}</span>
            <span>{event.time}</span>
          </div>
          <div>{event.text}</div>
        </article>
      ))}
    </div>
  );
}
