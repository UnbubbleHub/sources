import { redirect } from "next/navigation";
import { isAdmin } from "@/app/admin/auth";
import { AdminNav } from "@/app/admin/components";
import { sql } from "@/app/db";

const PAGE_SIZE = 30;

export default async function AdminRunsPage(props: {
  searchParams: Promise<{ page?: string }>;
}) {
  if (!(await isAdmin())) redirect("/admin/login");

  const searchParams = await props.searchParams;
  const page = Math.max(1, parseInt(searchParams.page ?? "1", 10) || 1);
  const offset = (page - 1) * PAGE_SIZE;

  const [runs, countResult] = await Promise.all([
    sql(
      "SELECT run_id, visitor_id, timestamp, query, date, status, cost FROM analytics_runs ORDER BY timestamp DESC LIMIT $1 OFFSET $2",
      [PAGE_SIZE, offset],
    ),
    sql("SELECT COUNT(*) AS total FROM analytics_runs"),
  ]);

  const total = parseInt(countResult[0].total as string, 10);
  const totalPages = Math.ceil(total / PAGE_SIZE);

  return (
    <div className="min-h-full flex flex-col">
      <AdminNav active="runs" />

      <main className="flex-1 px-6 py-8">
        <div className="max-w-5xl mx-auto">
          <h1 className="text-lg font-semibold text-foreground mb-6">
            Pipeline Runs
            <span className="ml-2 text-sm font-normal text-zinc-400 dark:text-zinc-500">
              ({total})
            </span>
          </h1>

          {runs.length === 0 ? (
            <p className="text-sm text-zinc-400 dark:text-zinc-500">No runs yet.</p>
          ) : (
            <div className="overflow-x-auto rounded-lg border border-zinc-200 dark:border-zinc-800">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-zinc-200 dark:border-zinc-800 bg-zinc-50 dark:bg-zinc-900/60">
                    <th className="text-left px-4 py-2.5 text-xs font-medium text-zinc-500 dark:text-zinc-400 uppercase tracking-wider">Run ID</th>
                    <th className="text-left px-4 py-2.5 text-xs font-medium text-zinc-500 dark:text-zinc-400 uppercase tracking-wider">Query</th>
                    <th className="text-left px-4 py-2.5 text-xs font-medium text-zinc-500 dark:text-zinc-400 uppercase tracking-wider">Date</th>
                    <th className="text-left px-4 py-2.5 text-xs font-medium text-zinc-500 dark:text-zinc-400 uppercase tracking-wider">Status</th>
                    <th className="text-right px-4 py-2.5 text-xs font-medium text-zinc-500 dark:text-zinc-400 uppercase tracking-wider">Cost</th>
                    <th className="text-left px-4 py-2.5 text-xs font-medium text-zinc-500 dark:text-zinc-400 uppercase tracking-wider">Visitor</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-zinc-100 dark:divide-zinc-800/60">
                  {runs.map((run) => (
                    <tr key={run.run_id as string} className="hover:bg-zinc-50 dark:hover:bg-zinc-900/40 transition-colors">
                      <td className="px-4 py-3 font-mono text-xs text-zinc-500 dark:text-zinc-400">
                        <a
                          href={`/search?id=${run.run_id as string}&q=${encodeURIComponent(run.query as string)}`}
                          className="hover:text-accent transition-colors"
                        >
                          {(run.run_id as string).slice(0, 8)}
                        </a>
                      </td>
                      <td className="px-4 py-3 text-foreground max-w-xs truncate">{run.query as string}</td>
                      <td className="px-4 py-3 text-zinc-500 dark:text-zinc-400 whitespace-nowrap">
                        {new Date(run.timestamp as string).toLocaleString("en-US", {
                          month: "short", day: "numeric", hour: "2-digit", minute: "2-digit",
                        })}
                      </td>
                      <td className="px-4 py-3">
                        <span className={`inline-flex items-center gap-1.5 text-xs font-medium ${
                          run.status === "completed"
                            ? "text-emerald-600 dark:text-emerald-400"
                            : run.status === "error"
                              ? "text-red-500 dark:text-red-400"
                              : "text-amber-500 dark:text-amber-400"
                        }`}>
                          <span className={`w-1.5 h-1.5 rounded-full ${
                            run.status === "completed"
                              ? "bg-emerald-500"
                              : run.status === "error"
                                ? "bg-red-500"
                                : "bg-amber-500 animate-pulse-dot"
                          }`} />
                          {run.status as string}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-right font-mono text-xs text-zinc-500 dark:text-zinc-400">
                        {run.cost != null ? `$${Number(run.cost).toFixed(3)}` : "\u2014"}
                      </td>
                      <td className="px-4 py-3 font-mono text-xs text-zinc-500 dark:text-zinc-400">
                        {run.visitor_id ? (run.visitor_id as string).slice(0, 8) : "\u2014"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {totalPages > 1 && (
            <div className="mt-4 flex items-center justify-center gap-2">
              {page > 1 && (
                <a
                  href={`/admin/runs?page=${page - 1}`}
                  className="px-3 py-1.5 text-xs font-medium text-accent hover:text-accent-hover border border-zinc-200 dark:border-zinc-800 rounded-lg transition-colors"
                >
                  Prev
                </a>
              )}
              <span className="text-xs text-zinc-400 dark:text-zinc-500">
                Page {page} of {totalPages}
              </span>
              {page < totalPages && (
                <a
                  href={`/admin/runs?page=${page + 1}`}
                  className="px-3 py-1.5 text-xs font-medium text-accent hover:text-accent-hover border border-zinc-200 dark:border-zinc-800 rounded-lg transition-colors"
                >
                  Next
                </a>
              )}
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
