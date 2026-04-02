export interface DemoStage {
  stage: string;
  component: string;
  input: unknown;
  output: unknown;
  usage: {
    api_calls?: Array<{
      model: string;
      input_tokens: number;
      output_tokens: number;
      web_searches: number;
    }>;
    input_tokens: number;
    output_tokens: number;
    web_searches: number;
    estimated_cost: number;
  } | null;
  cost_usd: number | null;
  timestamp: string;
  duration_seconds: number;
}

export interface SourceAnnotation {
  political_lean: string;
  policy_frames: string[];
  stakeholder_type: string;
  stance_summary: string;
  topic: string;
  geographic_focus: string;
}

export interface RankedSource {
  source: {
    url: string;
    source: string;
    published_at: string | null;
    query: {
      text: string;
      intent: string;
    };
    title: string;
    description: string | null;
  };
  annotation: SourceAnnotation;
  relevance_score: number;
}

export interface RunStatus {
  id: string;
  status: "not_found" | "running" | "completed" | "error";
  meta: { query: string; started_at: string; date: string } | null;
  stages: DemoStage[];
  completed: unknown;
  error: { error: string } | null;
}

export interface DemoRun {
  run_id: string;
  pipeline_type: string;
  event: {
    description: string;
    date: string | null;
    context: string | null;
  };
  started_at: string;
  completed_at: string;
  stages: DemoStage[];
  final_source_count: number;
  total_cost_usd: number;
}
