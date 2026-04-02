interface ApiKeysPanelProps {
  apiKey: string;
  onChange: (value: string) => void;
  error?: boolean;
}

export function ApiKeysPanel({ apiKey, onChange, error }: ApiKeysPanelProps) {
  return (
    <div className="w-full">
      <div className="flex flex-col gap-1">
        <label
          htmlFor="key-claude"
          className={`text-xs flex items-center gap-1.5 transition-colors ${
            error
              ? "text-red-500"
              : "text-zinc-500 dark:text-zinc-400"
          }`}
        >
          Claude API Key
          <span className="text-red-400">*</span>
        </label>
        <input
          id="key-claude"
          type="password"
          value={apiKey}
          onChange={(e) => onChange(e.target.value)}
          placeholder="sk-ant-..."
          className={`font-mono text-sm h-9 px-3 bg-zinc-50 dark:bg-zinc-900 border rounded-lg outline-none transition-colors placeholder:text-zinc-300 dark:placeholder:text-zinc-700 ${
            error
              ? "border-red-400 focus:border-red-500"
              : "border-zinc-200 dark:border-zinc-800 focus:border-zinc-400 dark:focus:border-zinc-600"
          }`}
        />
        {error && (
          <p className="text-xs text-red-500 mt-0.5">
            A Claude API key is required to run the pipeline.
          </p>
        )}
      </div>
    </div>
  );
}
