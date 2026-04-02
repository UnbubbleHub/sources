"use client";

import { useState, useCallback, type ComponentType } from "react";
import { useRouter } from "next/navigation";
import {
  IconBinaryTree,
  IconTags,
  IconChartDots3,
} from "@tabler/icons-react";
import { Logo } from "./Logo";
import { SearchBar } from "./SearchBar";
import { ApiKeysPanel } from "./ApiKeysPanel";
import { generate } from "@/app/actions";

const HOW_IT_WORKS: {
  icon: ComponentType<{ size?: number; stroke?: number; className?: string }>;
  title: string;
  description: string;
}[] = [
  {
    icon: IconBinaryTree,
    title: "PCA query expansion",
    description: "Generates perspective-diverse queries via LLM, then deduplicates with PCA dimensionality reduction",
  },
  {
    icon: IconTags,
    title: "Structured annotation",
    description: "Classifies sources on MBFC 7-point political lean, Boydstun policy frames, and stakeholder type",
  },
  {
    icon: IconChartDots3,
    title: "MMR diversity ranking",
    description: "Re-ranks via Maximal Marginal Relevance using weighted perspective distance (political lean, frames, stakeholder)",
  },
];

const EXAMPLE_QUERIES = [
  "US-Cuba diplomatic tensions over migration policy",
  "EU AI Act enforcement and tech industry response",
  "Global semiconductor supply chain restructuring",
  "Amazon rainforest deforestation policy debate",
  "NATO expansion and Arctic security concerns",
];

export function App() {
  const router = useRouter();
  const [query, setQuery] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [apiKeyError, setApiKeyError] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = useCallback(async () => {
    if (!query.trim()) return;
    if (!apiKey.trim()) {
      setApiKeyError(true);
      return;
    }
    setApiKeyError(false);
    setSubmitting(true);
    try {
      const { id } = await generate(query.trim(), apiKey.trim());
      router.push(`/search?id=${id}&q=${encodeURIComponent(query.trim())}`);
    } catch {
      setSubmitting(false);
    }
  }, [query, apiKey, router]);

  return (
    <div className="flex flex-1 flex-col items-center justify-between px-6 py-12">
      {/* Zone 1 — Hero (compact) */}
      <div />
      <div className="flex flex-col items-center w-full max-w-2xl">
        <div className="flex flex-col items-center gap-2 mb-2">
          <Logo />
          <span className="text-zinc-400 dark:text-zinc-500 text-sm">
            Analyzes sources from diverse perspectives
          </span>
        </div>

        {/* Zone 2 — Form unit */}
        <div className="w-full mt-8 rounded-2xl border border-zinc-200 dark:border-zinc-800 bg-zinc-50/50 dark:bg-zinc-900/50 p-5 flex flex-col gap-4">
          <SearchBar
            value={query}
            onChange={setQuery}
            onSubmit={handleSubmit}
            disabled={submitting}
          />

          <ApiKeysPanel
            apiKey={apiKey}
            onChange={(v) => {
              setApiKey(v);
              if (apiKeyError && v.trim()) setApiKeyError(false);
            }}
            error={apiKeyError}
          />
        </div>

        {/* Example queries */}
        <div className="flex flex-wrap justify-center gap-2 mt-4">
          <span className="text-xs text-zinc-400 dark:text-zinc-500 mr-1 py-1.5">
            Try:
          </span>
          {EXAMPLE_QUERIES.map((q) => (
            <button
              key={q}
              type="button"
              onClick={() => setQuery(q)}
              className="text-xs px-3 py-1.5 rounded-full border border-zinc-200 dark:border-zinc-800 text-zinc-500 dark:text-zinc-400 hover:border-accent hover:text-accent transition-colors cursor-pointer"
            >
              {q}
            </button>
          ))}
        </div>

        {/* How it works */}
        <div className="mt-10 w-full grid grid-cols-1 sm:grid-cols-3 gap-6">
          {HOW_IT_WORKS.map((step) => (
            <div key={step.title} className="flex flex-col gap-2">
              <step.icon size={20} stroke={1.5} className="text-zinc-400 dark:text-zinc-500" />
              <span className="text-xs font-medium text-foreground">{step.title}</span>
              <span className="text-[11px] text-zinc-400 dark:text-zinc-500 leading-relaxed">{step.description}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Zone 3 — Footer */}
      <div className="flex flex-col items-center gap-3 mt-12">
        <p className="text-xs text-zinc-400 dark:text-zinc-500 text-center">
          ~105k tokens (Haiku) and 5 web searches per run — approximately $0.20
        </p>
        <a
          href="https://github.com/UnbubbleHub/sources"
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-2 text-xs text-zinc-400 dark:text-zinc-500 hover:text-zinc-600 dark:hover:text-zinc-300 transition-colors"
        >
          <svg
            width="14"
            height="14"
            viewBox="0 0 16 16"
            fill="currentColor"
            aria-hidden="true"
          >
            <path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.01 8.01 0 0016 8c0-4.42-3.58-8-8-8z" />
          </svg>
          Open source on GitHub
        </a>
      </div>
    </div>
  );
}
