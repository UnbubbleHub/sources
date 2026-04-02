"use client";

import { Suspense, useState, useEffect } from "react";
import { useSearchParams } from "next/navigation";
import { Logo } from "@/app/components/Logo";
import { PipelineLoader, type StageState } from "@/app/components/PipelineLoader";
import { SourcesTable } from "@/app/components/SourcesTable";
import { getRunStatus } from "@/app/actions";
import type { DemoStage, RankedSource } from "@/app/types";

const INITIAL_STAGES: StageState[] = [
  { name: "Query Generation", key: "query_generation", status: "pending", durationMs: 3400 },
  { name: "Aggregation", key: "aggregation", status: "pending", durationMs: 800 },
  { name: "Search", key: "search", status: "pending", durationMs: 8000 },
  { name: "Deduplication", key: "deduplication", status: "pending", durationMs: 600 },
  { name: "Annotation", key: "annotation", status: "pending", durationMs: 5000 },
  { name: "Ranking", key: "ranking", status: "pending", durationMs: 1200 },
];

function mapStages(completedStages: DemoStage[]): StageState[] {
  const completedKeys = new Set(completedStages.map((s) => s.stage));
  let foundActive = false;

  return INITIAL_STAGES.map((s) => {
    if (completedKeys.has(s.key)) {
      return { ...s, status: "complete" as const };
    }
    if (!foundActive) {
      foundActive = true;
      return { ...s, status: "active" as const };
    }
    return { ...s, status: "pending" as const };
  });
}

type Phase = "missing" | "loading" | "results" | "empty" | "error";

export default function SearchPageWrapper() {
  return (
    <Suspense>
      <SearchPage />
    </Suspense>
  );
}

function SearchPage() {
  const searchParams = useSearchParams();
  const runId = searchParams.get("id");
  const queryParam = searchParams.get("q");

  const [phase, setPhase] = useState<Phase>(runId ? "loading" : "missing");
  const [query, setQuery] = useState(queryParam ?? "");
  const [stages, setStages] = useState<StageState[]>(
    INITIAL_STAGES.map((s) => ({ ...s, status: "pending" as const }))
  );
  const [stageData, setStageData] = useState<DemoStage[]>([]);
  const [rankedSources, setRankedSources] = useState<RankedSource[]>([]);
  const [runData, setRunData] = useState<unknown>(null);
  const [errorMessage, setErrorMessage] = useState<string>("");

  useEffect(() => {
    if (!runId) return;

    let cancelled = false;

    const poll = async () => {
      try {
        const status = await getRunStatus(runId);

        if (cancelled) return;

        if (status.status === "not_found") {
          // Pipeline hasn't written anything yet — keep polling
          return;
        }

        if (status.meta?.query && !query) {
          setQuery(status.meta.query);
        }

        if (status.status === "error") {
          setErrorMessage(status.error?.error ?? "Pipeline failed");
          setPhase("error");
          return;
        }

        // Update stages from polled data
        setStageData(status.stages);
        setStages(mapStages(status.stages));

        if (status.status === "completed") {
          const ranking = status.stages.find((s: DemoStage) => s.stage === "ranking");
          const sources = (ranking?.output ?? []) as RankedSource[];
          setRankedSources(sources);
          setRunData({ ...status, stages: status.stages });
          setPhase(sources.length > 0 ? "results" : "empty");
        }
      } catch {
        // Network error — keep polling
      }
    };

    poll();
    const interval = setInterval(poll, 2000);

    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, [runId]);

  if (phase === "missing") {
    return (
      <div className="flex flex-1 flex-col items-center justify-center px-6 py-16 gap-4">
        <p className="text-sm text-zinc-500 dark:text-zinc-400 text-center max-w-md">
          No search run specified.
        </p>
        <a
          href="/"
          className="text-xs text-accent hover:text-accent-hover transition-colors"
        >
          &larr; Start a new search
        </a>
      </div>
    );
  }

  if (phase === "error") {
    return (
      <div className="flex flex-1 flex-col items-center justify-center px-6 py-16 gap-4">
        <p className="text-sm text-red-500 dark:text-red-400 text-center max-w-md">
          {errorMessage}
        </p>
        <a
          href="/"
          className="text-xs text-accent hover:text-accent-hover transition-colors"
        >
          &larr; Try again
        </a>
      </div>
    );
  }

  if (phase === "loading") {
    return (
      <div className="flex flex-1 flex-col items-center justify-center px-6 py-16">
        <PipelineLoader query={query} stages={stages} stageData={stageData} />
      </div>
    );
  }

  const sourceCount = rankedSources.length;

  return (
    <div className="flex flex-col min-h-full animate-fade-in-up">
      {/* Header */}
      <header className="border-b border-zinc-200 dark:border-zinc-800 px-6 py-4">
        <div className="max-w-7xl mx-auto flex items-center gap-4">
          <a href="/" className="shrink-0">
            <Logo size="sm" />
          </a>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-foreground truncate">{query}</p>
            <p className="text-xs text-zinc-400 dark:text-zinc-500">
              {sourceCount > 0
                ? `${sourceCount} sources from diverse perspectives`
                : "No sources found"}
            </p>
          </div>
          {runData != null && (
            <button
              type="button"
              onClick={() => {
                const blob = new Blob([JSON.stringify(runData, null, 2)], { type: "application/json" });
                const url = URL.createObjectURL(blob);
                const a = document.createElement("a");
                a.href = url;
                a.download = `unbubble-run-${runId!.slice(0, 8)}.json`;
                a.click();
                URL.revokeObjectURL(url);
              }}
              className="shrink-0 flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-white bg-zinc-700 hover:bg-zinc-600 dark:bg-zinc-700 dark:hover:bg-zinc-600 rounded-lg transition-colors cursor-pointer"
            >
              <svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden="true">
                <path d="M7 2v7m0 0L4.5 6.5M7 9l2.5-2.5M3 11.5h8" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
              JSON
            </button>
          )}
        </div>
      </header>

      {/* Results */}
      <main className="flex-1 px-6 py-8">
        <div className="max-w-7xl mx-auto">
          {phase === "empty" ? (
            <div className="flex flex-col items-center justify-center py-20 gap-3">
              <p className="text-sm text-zinc-400 dark:text-zinc-500">
                No sources were found for this query.
              </p>
              <a
                href="/"
                className="text-xs text-accent hover:text-accent-hover transition-colors"
              >
                &larr; Try a different search
              </a>
            </div>
          ) : (
            <SourcesTable data={rankedSources} />
          )}
        </div>
      </main>

      {/* Footer */}
      {sourceCount > 0 && (
        <footer className="border-t border-zinc-200 dark:border-zinc-800 px-6 py-4">
          <div className="max-w-7xl mx-auto flex items-center justify-between text-xs text-zinc-400 dark:text-zinc-500">
            <span>
              {sourceCount} sources ranked
            </span>
          </div>
        </footer>
      )}
    </div>
  );
}
