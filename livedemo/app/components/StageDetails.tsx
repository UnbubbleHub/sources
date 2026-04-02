import type { DemoStage } from "../types";

function formatCost(usd: number): string {
  if (usd < 0.01) return `$${usd.toFixed(4)}`;
  return `$${usd.toFixed(3)}`;
}

function formatDuration(seconds: number): string {
  if (seconds < 0.01) return "<0.01s";
  if (seconds < 1) return `${(seconds * 1000).toFixed(0)}ms`;
  return `${seconds.toFixed(1)}s`;
}

function UsagePills({
  duration,
  cost,
  tokenCount,
  webSearches,
}: {
  duration: number;
  cost: number | null;
  tokenCount?: number;
  webSearches?: number;
}) {
  return (
    <div className="flex flex-wrap gap-1.5 mt-1.5">
      <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-zinc-100 dark:bg-zinc-800 text-zinc-500 dark:text-zinc-400">
        {formatDuration(duration)}
      </span>
      {cost != null && cost > 0 && (
        <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-zinc-100 dark:bg-zinc-800 text-zinc-500 dark:text-zinc-400">
          {formatCost(cost)}
        </span>
      )}
      {tokenCount != null && tokenCount > 0 && (
        <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-zinc-100 dark:bg-zinc-800 text-zinc-500 dark:text-zinc-400">
          {tokenCount.toLocaleString()} tokens
        </span>
      )}
      {webSearches != null && webSearches > 0 && (
        <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-zinc-100 dark:bg-zinc-800 text-zinc-500 dark:text-zinc-400">
          {webSearches} web searches
        </span>
      )}
    </div>
  );
}

function QueryGenerationDetails({ stage }: { stage: DemoStage }) {
  const queries = (stage.output ?? []) as Array<{ text: string; intent: string }>;
  return (
    <div className="space-y-2">
      <UsagePills
        duration={stage.duration_seconds}
        cost={stage.cost_usd}
        tokenCount={stage.usage?.input_tokens}
      />
      <div className="space-y-1.5 mt-2">
        {queries.map((q, i) => (
          <div
            key={i}
            className="text-xs border-l-2 border-accent/30 pl-2.5 py-0.5"
          >
            <p className="font-medium text-foreground/80">{q.text}</p>
            <p className="text-zinc-400 dark:text-zinc-500 mt-0.5">
              {q.intent}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}

function AggregationDetails({ stage }: { stage: DemoStage }) {
  const input = (stage.input ?? []) as Array<unknown>;
  const output = (stage.output ?? []) as Array<unknown>;
  return (
    <div>
      <UsagePills duration={stage.duration_seconds} cost={stage.cost_usd} />
      <p className="text-xs text-zinc-500 dark:text-zinc-400 mt-2">
        {input.length} queries in &rarr; {output.length} queries out
      </p>
    </div>
  );
}

function SearchDetails({ stage }: { stage: DemoStage }) {
  const sources = (stage.output ?? []) as Array<{
    url: string;
    source: string;
    title: string;
    published_at: string | null;
    query: { text: string; intent: string };
  }>;

  const totalWebSearches = stage.usage?.api_calls?.reduce(
    (sum, c) => sum + (c.web_searches || 0),
    0
  );
  const totalTokens =
    (stage.usage?.input_tokens || 0) + (stage.usage?.output_tokens || 0);

  // Group by query text
  const byQuery = new Map<string, typeof sources>();
  for (const s of sources) {
    const key = s.query.text;
    if (!byQuery.has(key)) byQuery.set(key, []);
    byQuery.get(key)!.push(s);
  }

  return (
    <div>
      <UsagePills
        duration={stage.duration_seconds}
        cost={stage.cost_usd}
        tokenCount={totalTokens}
        webSearches={totalWebSearches}
      />
      <p className="text-xs text-zinc-500 dark:text-zinc-400 mt-2 mb-2">
        {sources.length} sources found across {byQuery.size} queries
      </p>
      <div className="space-y-2">
        {[...byQuery.entries()].map(([queryText, querySources]) => (
          <details key={queryText} className="group/q">
            <summary className="text-xs font-medium text-foreground/70 cursor-pointer hover:text-foreground/90 transition-colors list-none flex items-center gap-1.5">
              <svg
                width="10"
                height="10"
                viewBox="0 0 10 10"
                className="shrink-0 transition-transform group-open/q:rotate-90"
                fill="currentColor"
              >
                <path d="M3 1.5L7 5L3 8.5" stroke="currentColor" strokeWidth="1.5" fill="none" strokeLinecap="round" />
              </svg>
              <span className="truncate">{queryText}</span>
              <span className="text-zinc-400 dark:text-zinc-600 shrink-0">
                ({querySources.length})
              </span>
            </summary>
            <div className="ml-4 mt-1 space-y-1">
              {querySources.map((s) => (
                <div key={s.url} className="text-[11px] flex items-baseline gap-1.5 text-zinc-500 dark:text-zinc-400">
                  <span className="text-zinc-400 dark:text-zinc-600 shrink-0 font-mono">
                    {s.source}
                  </span>
                  <span className="truncate">{s.title}</span>
                </div>
              ))}
            </div>
          </details>
        ))}
      </div>
    </div>
  );
}

function DeduplicationDetails({ stage }: { stage: DemoStage }) {
  const input = (stage.input ?? { source_count: 0 }) as { source_count: number };
  const output = (stage.output ?? { source_count: 0 }) as { source_count: number };
  const removed = input.source_count - output.source_count;
  return (
    <div>
      <UsagePills duration={stage.duration_seconds} cost={stage.cost_usd} />
      <p className="text-xs text-zinc-500 dark:text-zinc-400 mt-2">
        {input.source_count} sources in &rarr; {output.source_count} unique
        {removed > 0 && (
          <span className="text-zinc-400 dark:text-zinc-600">
            {" "}({removed} duplicates removed)
          </span>
        )}
      </p>
    </div>
  );
}

const LEAN_COLORS: Record<string, string> = {
  left: "bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300",
  "center-left":
    "bg-sky-100 text-sky-700 dark:bg-sky-900/40 dark:text-sky-300",
  center:
    "bg-zinc-100 text-zinc-600 dark:bg-zinc-800 dark:text-zinc-300",
  "center-right":
    "bg-orange-100 text-orange-700 dark:bg-orange-900/40 dark:text-orange-300",
  right: "bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300",
};

function AnnotationDetails({ stage }: { stage: DemoStage }) {
  const items = (stage.output ?? []) as Array<{
    source: { title: string; source: string };
    annotation: {
      political_lean: string;
      stakeholder_type: string;
      stance_summary: string;
      policy_frames: string[];
    };
    relevance_score: number;
  }>;

  const totalTokens =
    (stage.usage?.input_tokens || 0) + (stage.usage?.output_tokens || 0);

  // Count political leans
  const leanCounts = new Map<string, number>();
  for (const item of items) {
    const lean = item.annotation.political_lean;
    leanCounts.set(lean, (leanCounts.get(lean) || 0) + 1);
  }

  return (
    <div>
      <UsagePills
        duration={stage.duration_seconds}
        cost={stage.cost_usd}
        tokenCount={totalTokens}
      />
      <div className="flex flex-wrap gap-1.5 mt-2">
        {[...leanCounts.entries()].map(([lean, count]) => (
          <span
            key={lean}
            className={`text-[10px] font-medium px-2 py-0.5 rounded-full ${
              LEAN_COLORS[lean] || LEAN_COLORS.center
            }`}
          >
            {lean} ({count})
          </span>
        ))}
      </div>
      <div className="space-y-1 mt-2">
        {items.slice(0, 8).map((item) => (
          <div
            key={item.source.title}
            className="text-[11px] flex items-baseline gap-1.5"
          >
            <span
              className={`shrink-0 px-1 py-px rounded text-[9px] font-medium ${
                LEAN_COLORS[item.annotation.political_lean] ||
                LEAN_COLORS.center
              }`}
            >
              {item.annotation.political_lean}
            </span>
            <span className="text-zinc-400 dark:text-zinc-600 shrink-0 font-mono">
              {item.source.source}
            </span>
            <span className="truncate text-zinc-500 dark:text-zinc-400">
              {item.annotation.stance_summary}
            </span>
          </div>
        ))}
        {items.length > 8 && (
          <p className="text-[10px] text-zinc-400 dark:text-zinc-600 pl-1">
            +{items.length - 8} more
          </p>
        )}
      </div>
    </div>
  );
}

function RankingDetails({ stage }: { stage: DemoStage }) {
  const items = (stage.output ?? []) as Array<{
    source: { title: string; source: string; url: string };
    annotation: { political_lean: string; stakeholder_type: string };
    relevance_score: number;
  }>;

  return (
    <div>
      <UsagePills duration={stage.duration_seconds} cost={stage.cost_usd} />
      <p className="text-xs text-zinc-500 dark:text-zinc-400 mt-2 mb-2">
        Top {items.length} diverse sources (MMR)
      </p>
      <div className="space-y-1">
        {items.map((item, i) => (
          <div
            key={item.source.url}
            className="text-[11px] flex items-baseline gap-1.5"
          >
            <span className="text-zinc-400 dark:text-zinc-600 shrink-0 font-mono w-4 text-right">
              {i + 1}.
            </span>
            <span
              className={`shrink-0 px-1 py-px rounded text-[9px] font-medium ${
                LEAN_COLORS[item.annotation.political_lean] ||
                LEAN_COLORS.center
              }`}
            >
              {item.annotation.political_lean}
            </span>
            <span className="text-zinc-400 dark:text-zinc-600 shrink-0 font-mono">
              {item.source.source}
            </span>
            <span className="truncate text-zinc-500 dark:text-zinc-400">
              {item.source.title}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

const STAGE_RENDERERS: Record<
  string,
  (props: { stage: DemoStage }) => React.ReactNode
> = {
  query_generation: QueryGenerationDetails,
  aggregation: AggregationDetails,
  search: SearchDetails,
  deduplication: DeduplicationDetails,
  annotation: AnnotationDetails,
  ranking: RankingDetails,
};

export function StageDetails({ stage }: { stage: DemoStage }) {
  const Renderer = STAGE_RENDERERS[stage.stage];
  if (!Renderer) return null;
  return <Renderer stage={stage} />;
}
