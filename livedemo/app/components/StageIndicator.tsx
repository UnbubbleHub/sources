import type { DemoStage } from "../types";
import { StageDetails } from "./StageDetails";

export type StageStatus = "pending" | "active" | "complete";

interface StageIndicatorProps {
  name: string;
  status: StageStatus;
  isLast: boolean;
  stageData?: DemoStage;
}

function StatusIcon({ status }: { status: StageStatus }) {
  if (status === "complete") {
    return (
      <div className="w-6 h-6 rounded-full bg-accent/15 flex items-center justify-center">
        <svg
          width="12"
          height="12"
          viewBox="0 0 12 12"
          fill="none"
          aria-hidden="true"
        >
          <path
            d="M2.5 6.5L4.5 8.5L9.5 3.5"
            stroke="currentColor"
            strokeWidth="1.5"
            strokeLinecap="round"
            strokeLinejoin="round"
            className="text-accent"
          />
        </svg>
      </div>
    );
  }

  if (status === "active") {
    return (
      <div className="w-6 h-6 rounded-full bg-accent flex items-center justify-center animate-pulse-dot">
        <div className="w-2 h-2 rounded-full bg-zinc-950" />
      </div>
    );
  }

  return (
    <div className="w-6 h-6 rounded-full border-2 border-zinc-200 dark:border-zinc-700" />
  );
}

function ChevronIcon() {
  return (
    <svg
      width="12"
      height="12"
      viewBox="0 0 12 12"
      className="shrink-0 transition-transform group-open:rotate-90 text-zinc-400 dark:text-zinc-600"
      fill="none"
    >
      <path
        d="M4 2.5L8 6L4 9.5"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
      />
    </svg>
  );
}

export function StageIndicator({
  name,
  status,
  isLast,
  stageData,
}: StageIndicatorProps) {
  const hasDetails = status !== "pending" && stageData;

  return (
    <div className="flex gap-4">
      <div className="flex flex-col items-center">
        <StatusIcon status={status} />
        {!isLast && (
          <div
            className={`w-px flex-1 min-h-6 transition-colors duration-500 ${
              status === "complete"
                ? "bg-accent/30"
                : "bg-zinc-200 dark:bg-zinc-800"
            }`}
          />
        )}
      </div>
      <div className={`pb-6 flex-1 min-w-0 ${isLast ? "" : ""}`}>
        {hasDetails ? (
          <details open={status === "active"} className="group">
            <summary className="cursor-pointer list-none flex items-center gap-1.5 select-none">
              <ChevronIcon />
              <p className="text-sm font-medium text-foreground transition-colors duration-300">
                {name}
              </p>
              {status === "active" && (
                <span className="text-[10px] font-mono text-accent animate-pulse">
                  running
                </span>
              )}
            </summary>
            <div className="mt-1.5 ml-[18px] animate-fade-in-up">
              <StageDetails stage={stageData} />
            </div>
          </details>
        ) : (
          <p
            className={`text-sm font-medium transition-colors duration-300 ${
              status === "pending"
                ? "text-zinc-400 dark:text-zinc-600"
                : "text-foreground"
            }`}
          >
            {name}
          </p>
        )}
      </div>
    </div>
  );
}
