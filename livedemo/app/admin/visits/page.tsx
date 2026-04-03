import { redirect } from "next/navigation";
import { isAdmin } from "@/app/admin/auth";
import { AdminNav } from "@/app/admin/components";
import { sql } from "@/app/db";

export default async function AdminVisitsPage() {
  if (!(await isAdmin())) redirect("/admin/login");

  const [todayStats, yesterdayStats, weekStats, dailyBreakdown, topReferrers, recent] =
    await Promise.all([
      sql(`
        SELECT COUNT(*) AS total, COUNT(DISTINCT visitor_id) AS unique_visitors
        FROM analytics_visits WHERE timestamp >= CURRENT_DATE
      `),
      sql(`
        SELECT COUNT(*) AS total, COUNT(DISTINCT visitor_id) AS unique_visitors
        FROM analytics_visits WHERE timestamp >= CURRENT_DATE - INTERVAL '1 day' AND timestamp < CURRENT_DATE
      `),
      sql(`
        SELECT
          COUNT(*) AS total,
          COUNT(DISTINCT visitor_id) AS unique_visitors,
          COUNT(DISTINCT visitor_id) FILTER (WHERE visitor_id IN (
            SELECT visitor_id FROM analytics_visits
            WHERE timestamp >= CURRENT_DATE - INTERVAL '7 days'
            GROUP BY visitor_id HAVING COUNT(*) > 1
          )) AS returning_visitors
        FROM analytics_visits WHERE timestamp >= CURRENT_DATE - INTERVAL '7 days'
      `),
      sql(`
        SELECT DATE(timestamp) AS day, COUNT(*) AS total, COUNT(DISTINCT visitor_id) AS unique_visitors
        FROM analytics_visits
        WHERE timestamp >= CURRENT_DATE - INTERVAL '6 days'
        GROUP BY DATE(timestamp)
        ORDER BY day
      `),
      sql(`
        SELECT
          CASE
            WHEN referrer IS NULL OR referrer = '' THEN '(direct)'
            ELSE SUBSTRING(referrer FROM '://([^/]+)')
          END AS host,
          COUNT(*) AS count
        FROM analytics_visits
        WHERE timestamp >= CURRENT_DATE - INTERVAL '7 days'
        GROUP BY host
        ORDER BY count DESC
        LIMIT 5
      `),
      sql(`
        SELECT visitor_id, timestamp, path
        FROM analytics_visits
        ORDER BY timestamp DESC
        LIMIT 20
      `),
    ]);

  const todayTotal = parseInt(todayStats[0].total as string, 10);
  const todayUnique = parseInt(todayStats[0].unique_visitors as string, 10);
  const yesterdayTotal = parseInt(yesterdayStats[0].total as string, 10);
  const yesterdayUnique = parseInt(yesterdayStats[0].unique_visitors as string, 10);
  const weekTotal = parseInt(weekStats[0].total as string, 10);
  const weekUnique = parseInt(weekStats[0].unique_visitors as string, 10);
  const weekReturning = parseInt(weekStats[0].returning_visitors as string, 10);

  // Fill in missing days for the bar chart
  const dayMap = new Map(dailyBreakdown.map((d) => [d.day as string, d]));
  const days: { day: string; total: number; unique: number }[] = [];
  for (let i = 6; i >= 0; i--) {
    const d = new Date(Date.now() - i * 86400000).toISOString().slice(0, 10);
    const entry = dayMap.get(d);
    days.push({
      day: d,
      total: entry ? parseInt(entry.total as string, 10) : 0,
      unique: entry ? parseInt(entry.unique_visitors as string, 10) : 0,
    });
  }
  const maxDaily = Math.max(...days.map((d) => d.total), 1);

  return (
    <div className="min-h-full flex flex-col">
      <AdminNav active="visits" />

      <main className="flex-1 px-6 py-8">
        <div className="max-w-4xl mx-auto">
          <h1 className="text-lg font-semibold text-foreground mb-6">Visits</h1>

          {/* Stat cards */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-8">
            <StatCard label="Today" value={todayTotal} sub={`${todayUnique} unique`} />
            <StatCard label="Yesterday" value={yesterdayTotal} sub={`${yesterdayUnique} unique`} />
            <StatCard label="7-day total" value={weekTotal} sub={`${weekUnique} unique`} />
            <StatCard label="Returning (7d)" value={weekReturning} sub={`of ${weekUnique} visitors`} />
          </div>

          {/* Daily bar chart */}
          <section className="mb-8">
            <h2 className="text-xs font-medium text-zinc-500 dark:text-zinc-400 uppercase tracking-wider mb-3">Last 7 days</h2>
            <div className="flex items-end gap-2 h-28">
              {days.map((d) => (
                <div key={d.day} className="flex-1 flex flex-col items-center gap-1">
                  <span className="text-[10px] font-mono text-zinc-400 dark:text-zinc-500">{d.total}</span>
                  <div
                    className="w-full rounded-t bg-accent/70 transition-all"
                    style={{ height: `${Math.max((d.total / maxDaily) * 80, 2)}px` }}
                  />
                  <span className="text-[10px] text-zinc-400 dark:text-zinc-500">
                    {d.day.slice(5)}
                  </span>
                </div>
              ))}
            </div>
          </section>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-8">
            {/* Top referrers */}
            <section>
              <h2 className="text-xs font-medium text-zinc-500 dark:text-zinc-400 uppercase tracking-wider mb-3">Top Referrers</h2>
              {topReferrers.length === 0 ? (
                <p className="text-xs text-zinc-400 dark:text-zinc-500">No visits yet.</p>
              ) : (
                <div className="flex flex-col gap-1.5">
                  {topReferrers.map((r) => (
                    <div key={r.host as string} className="flex items-center justify-between text-sm">
                      <span className="text-foreground truncate">{r.host as string}</span>
                      <span className="text-xs font-mono text-zinc-400 dark:text-zinc-500 ml-2">{r.count as number}</span>
                    </div>
                  ))}
                </div>
              )}
            </section>

            {/* Recent visits */}
            <section>
              <h2 className="text-xs font-medium text-zinc-500 dark:text-zinc-400 uppercase tracking-wider mb-3">Recent Visits</h2>
              <div className="flex flex-col gap-1">
                {recent.map((v, i) => (
                  <div key={`${v.visitor_id}-${v.timestamp}-${i}`} className="flex items-center gap-2 text-xs py-1">
                    <span className="font-mono text-zinc-400 dark:text-zinc-500 shrink-0">
                      {(v.visitor_id as string).slice(0, 8)}
                    </span>
                    <span className="text-zinc-300 dark:text-zinc-700 shrink-0">{v.path as string}</span>
                    <span className="text-zinc-400 dark:text-zinc-500 ml-auto whitespace-nowrap">
                      {new Date(v.timestamp as string).toLocaleString("en-US", {
                        month: "short", day: "numeric", hour: "2-digit", minute: "2-digit",
                      })}
                    </span>
                  </div>
                ))}
              </div>
            </section>
          </div>
        </div>
      </main>
    </div>
  );
}

function StatCard({ label, value, sub }: { label: string; value: number; sub: string }) {
  return (
    <div className="rounded-lg border border-zinc-200 dark:border-zinc-800 bg-zinc-50/50 dark:bg-zinc-900/50 p-4">
      <p className="text-xs text-zinc-500 dark:text-zinc-400 mb-1">{label}</p>
      <p className="text-2xl font-semibold text-foreground tabular-nums">{value}</p>
      <p className="text-[11px] text-zinc-400 dark:text-zinc-500 mt-0.5">{sub}</p>
    </div>
  );
}
