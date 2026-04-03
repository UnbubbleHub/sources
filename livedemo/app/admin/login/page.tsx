"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { adminLogin } from "@/app/admin/actions";

export default function AdminLoginPage() {
  const router = useRouter();
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    const result = await adminLogin(password);
    if (result.error) {
      setError(result.error);
      setLoading(false);
    } else {
      router.push("/admin/runs");
    }
  };

  return (
    <div className="flex flex-1 items-center justify-center px-6">
      <div className="w-full max-w-xs">
        <div className="mb-8 text-center">
          <h1 className="text-sm font-semibold tracking-wide uppercase text-zinc-400 dark:text-zinc-500">
            Admin
          </h1>
        </div>

        <form onSubmit={handleSubmit} className="flex flex-col gap-3">
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="Password"
            autoFocus
            className="w-full px-3 py-2 text-sm rounded-lg border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 text-foreground placeholder:text-zinc-400 dark:placeholder:text-zinc-600 focus:outline-none focus:ring-2 focus:ring-accent/40 focus:border-accent transition-colors"
          />

          {error && (
            <p className="text-xs text-red-500 dark:text-red-400">{error}</p>
          )}

          <button
            type="submit"
            disabled={loading || !password}
            className="w-full px-3 py-2 text-sm font-medium rounded-lg bg-accent text-white hover:bg-accent-hover disabled:opacity-40 transition-colors cursor-pointer disabled:cursor-not-allowed"
          >
            {loading ? "..." : "Sign in"}
          </button>
        </form>
      </div>
    </div>
  );
}
