import { StageIndicator, type StageStatus } from "./StageIndicator";
import type { DemoStage } from "../types";

export interface StageState {
  name: string;
  key: string;
  status: StageStatus;
  durationMs: number;
}

interface PipelineLoaderProps {
  query: string;
  stages: StageState[];
  stageData?: DemoStage[];
}

export function PipelineLoader({
  query,
  stages,
  stageData,
}: PipelineLoaderProps) {
  return (
    <div className="flex flex-col items-center w-full max-w-2xl mx-auto animate-fade-in-up">
      <div className="text-center mb-12">
        <p className="text-xs uppercase tracking-widest text-zinc-400 dark:text-zinc-500 mb-3">
          Analyzing
        </p>
        <p className="text-2xl text-foreground leading-relaxed">
          <span className="text-zinc-300 dark:text-zinc-600">&ldquo;</span>
          {query}
          <span className="text-zinc-300 dark:text-zinc-600">&rdquo;</span>
        </p>
      </div>

      <div className="w-full">
        {stages.map((stage, i) => {
          const data = stageData?.find((d) => d.stage === stage.key);
          return (
            <StageIndicator
              key={stage.key}
              name={stage.name}
              status={stage.status}
              isLast={i === stages.length - 1}
              stageData={stage.status !== "pending" ? data : undefined}
            />
          );
        })}
      </div>
    </div>
  );
}
