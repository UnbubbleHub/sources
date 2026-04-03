import { adminLogout } from "@/app/admin/actions";

export function AdminNav({ active }: { active: "runs" | "visits" }) {
  return (
    <header className="border-b border-zinc-200 dark:border-zinc-800 px-6 py-3">
      <div className="max-w-5xl mx-auto flex items-center gap-6">
        <span className="text-xs font-semibold tracking-wide uppercase text-zinc-400 dark:text-zinc-500">
          Admin
        </span>

        <nav className="flex items-center gap-1">
          <NavLink href="/admin/runs" active={active === "runs"}>Runs</NavLink>
          <NavLink href="/admin/visits" active={active === "visits"}>Visits</NavLink>
        </nav>

        <form action={adminLogout} className="ml-auto">
          <button
            type="submit"
            className="text-xs text-zinc-400 dark:text-zinc-500 hover:text-zinc-600 dark:hover:text-zinc-300 transition-colors cursor-pointer"
          >
            Sign out
          </button>
        </form>
      </div>
    </header>
  );
}

function NavLink({ href, active, children }: { href: string; active: boolean; children: React.ReactNode }) {
  return (
    <a
      href={href}
      className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors ${
        active
          ? "bg-zinc-100 dark:bg-zinc-800 text-foreground"
          : "text-zinc-400 dark:text-zinc-500 hover:text-foreground hover:bg-zinc-50 dark:hover:bg-zinc-800/50"
      }`}
    >
      {children}
    </a>
  );
}
