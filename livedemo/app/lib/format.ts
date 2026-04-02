export const LEAN_COLORS: Record<string, { bg: string; text: string }> = {
  left: { bg: "bg-blue-100 dark:bg-blue-900/40", text: "text-blue-700 dark:text-blue-300" },
  center_left: { bg: "bg-sky-100 dark:bg-sky-900/40", text: "text-sky-700 dark:text-sky-300" },
  center: { bg: "bg-zinc-100 dark:bg-zinc-800", text: "text-zinc-600 dark:text-zinc-300" },
  center_right: { bg: "bg-orange-100 dark:bg-orange-900/40", text: "text-orange-700 dark:text-orange-300" },
  right: { bg: "bg-red-100 dark:bg-red-900/40", text: "text-red-700 dark:text-red-300" },
};

export const STAKEHOLDER_LABELS: Record<string, string> = {
  government: "Government",
  journalist: "Journalist",
  academic: "Academic",
  civil_society: "Civil Society",
  international_org: "Int'l Org",
  other: "Other",
};

export function formatLean(lean: string) {
  return lean.replace(/_/g, "-");
}

export function formatFrame(frame: string) {
  return frame.replace(/_/g, " ").replace(/and/g, "&");
}
