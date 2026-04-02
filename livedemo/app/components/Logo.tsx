export function Logo({ size = "default" }: { size?: "default" | "sm" }) {
  if (size === "sm") {
    return (
      <span
        className="text-lg font-semibold text-accent"
        style={{ fontFamily: "var(--font-fira-code), monospace" }}
      >
        [sources]
      </span>
    );
  }

  return (
    <div className="flex flex-col items-center">
      <span
        className="text-3xl font-semibold text-accent"
        style={{ fontFamily: "var(--font-fira-code), monospace" }}
      >
        [sources]
      </span>
      <span className="text-sm text-zinc-400 dark:text-zinc-500">
        by UnbubbleHub
      </span>
    </div>
  );
}
