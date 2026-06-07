import { FormEvent, useEffect, useState } from "react";
import { ApiError, logout, me, queryRules, type AuthSession } from "../api/client";
import type { RagChunk } from "../api/types";
import { JoinScreen } from "./JoinScreen";

const DEFAULT_QUERY = "How do opportunity attacks work?";

export function RulesLookupPage() {
  const [identity, setIdentity] = useState<AuthSession | null>(null);
  const [authChecked, setAuthChecked] = useState(false);
  const [query, setQuery] = useState(DEFAULT_QUERY);
  const [k, setK] = useState(4);
  const [chunks, setChunks] = useState<RagChunk[]>([]);
  const [hasSearched, setHasSearched] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    me()
      .then(setIdentity)
      .catch((apiError: Error) => {
        if (apiError instanceof ApiError && apiError.status === 401) {
          setIdentity(null);
          return;
        }
        setError(apiError.message);
      })
      .finally(() => setAuthChecked(true));
  }, []);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmedQuery = query.trim();
    if (!trimmedQuery) {
      setChunks([]);
      setHasSearched(false);
      setError("Enter a rule question first.");
      return;
    }

    setIsLoading(true);
    setError(null);
    setHasSearched(true);
    try {
      const response = await queryRules({ query: trimmedQuery, k });
      setChunks(response.chunks);
    } catch (apiError) {
      setChunks([]);
      setError(apiError instanceof Error ? apiError.message : "Rules lookup failed.");
    } finally {
      setIsLoading(false);
    }
  }

  async function handleLogout() {
    await logout();
    setIdentity(null);
    setChunks([]);
    setHasSearched(false);
  }

  if (!authChecked) {
    return <main className="app-shell">Loading rules...</main>;
  }

  if (!identity) {
    return <JoinScreen title="Join to search rules" onJoined={setIdentity} />;
  }

  return (
    <main className="app-shell">
      <header className="topbar">
        <div>
          <p className="eyebrow">Rules RAG</p>
          <h1>Rules Lookup</h1>
        </div>
        <div className="session-strip">
          <span>{identity.player?.displayName || identity.userId}</span>
          <a className="nav-link" href="/">
            返回战棋
          </a>
          <a className="nav-link" href="/characters/permanent">
            永久库
          </a>
          <button type="button" onClick={() => void handleLogout()}>
            Logout
          </button>
        </div>
      </header>

      <section className="rules-page">
        <form className="rules-query-panel" onSubmit={handleSubmit}>
          <div className="panel-header">
            <div>
              <p className="eyebrow">Query</p>
              <h2>Ask the rulebooks</h2>
            </div>
            <button type="submit" disabled={isLoading}>
              {isLoading ? "Searching..." : "Search"}
            </button>
          </div>

          <div className="rules-form-body">
            <label className="field">
              <span>Question</span>
              <textarea
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="Ask about a DND rule, spell, condition, or module fact..."
              />
            </label>

            <div className="form-grid two">
              <label className="field">
                <span>Chunks</span>
                <input
                  type="number"
                  min="1"
                  max="12"
                  value={k}
                  onChange={(event) => setK(clampChunkCount(event.target.value))}
                />
              </label>
            </div>

            <div className="rules-scope-card">
              <strong>{identity.player?.displayName || identity.userId}</strong>
              <span>{identity.role} scope</span>
            </div>
          </div>
        </form>

        <section className="rules-results-panel">
          <div className="panel-header">
            <div>
              <p className="eyebrow">Retrieved Context</p>
              <h2>{chunks.length} chunks</h2>
            </div>
          </div>

          {error ? <p className="rules-error">{error}</p> : null}
          {!error && !hasSearched ? (
            <p className="rules-empty">Run a search to inspect retrieved rule chunks.</p>
          ) : null}
          {!error && hasSearched && chunks.length === 0 && !isLoading ? (
            <p className="rules-empty">No matching rule chunks were returned.</p>
          ) : null}

          <div className="rules-results-list">
            {chunks.map((chunk, index) => (
              <RulesChunkCard key={chunk.chunkId} chunk={chunk} index={index} />
            ))}
          </div>
        </section>
      </section>
    </main>
  );
}

function RulesChunkCard({ chunk, index }: { chunk: RagChunk; index: number }) {
  const metadata = chunk.metadata || {};
  const title = metadata.title || metadata.section || chunk.chunkId;
  const source = metadata.source || metadata.source_id || "unknown source";
  const page = formatPageRange(metadata.page_start, metadata.page_end);
  const visibility = metadata.visibility || "unspecified";
  const remainingMetadata = Object.entries(metadata).filter(
    ([key]) => !["title", "section", "source", "source_id", "page_start", "page_end", "visibility"].includes(key)
  );

  return (
    <article className="rules-chunk-card">
      <div className="rules-chunk-heading">
        <div>
          <p className="eyebrow">Result {index + 1}</p>
          <h3>{String(title)}</h3>
        </div>
        <span className="rules-distance">
          {typeof chunk.distance === "number" ? chunk.distance.toFixed(4) : "score n/a"}
        </span>
      </div>

      <div className="rules-metadata-strip">
        <span>{String(source)}</span>
        <span>{page}</span>
        <span>{String(visibility)}</span>
      </div>

      <p className="rules-content">{chunk.content}</p>

      {remainingMetadata.length > 0 ? (
        <dl className="rules-metadata-grid">
          {remainingMetadata.map(([key, value]) => (
            <div key={key}>
              <dt>{key}</dt>
              <dd>{String(value)}</dd>
            </div>
          ))}
        </dl>
      ) : null}
    </article>
  );
}

function clampChunkCount(value: string): number {
  const parsed = Number.parseInt(value, 10);
  if (Number.isNaN(parsed)) return 1;
  return Math.min(12, Math.max(1, parsed));
}

function formatPageRange(
  pageStart: string | number | boolean | null | undefined,
  pageEnd: string | number | boolean | null | undefined
): string {
  if (pageStart === undefined || pageStart === null || pageStart === "") {
    return "page n/a";
  }
  if (pageEnd === undefined || pageEnd === null || pageEnd === "" || pageEnd === pageStart) {
    return `page ${String(pageStart)}`;
  }
  return `pages ${String(pageStart)}-${String(pageEnd)}`;
}
