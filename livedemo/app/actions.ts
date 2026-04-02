"use server";

import crypto from "crypto";
import { after } from "next/server";
import { list, put } from "@vercel/blob";

export async function generate(query: string, apiKey: string, date?: string) {
  console.log(`[actions.generate] apiKey: ${apiKey ? `${apiKey.slice(0, 8)}...${apiKey.slice(-4)} (len=${apiKey.length})` : "EMPTY"}`);
  // Deterministic ID: hash(query + date) → same query on same day = same id
  const today = date ?? new Date().toISOString().slice(0, 10);
  const id = crypto
    .createHash("sha256")
    .update(query + today)
    .digest("hex")
    .slice(0, 16);

  // Idempotency: if _meta.json already exists, skip re-running
  const { blobs } = await list({ prefix: `runs/${id}/_meta.json` });
  if (blobs.length > 0) {
    return { id };
  }

  // Write _meta.json immediately
  await put(
    `runs/${id}/_meta.json`,
    JSON.stringify({ query, started_at: new Date().toISOString(), date: today }),
    { access: "public", contentType: "application/json" },
  );

  // Fire pipeline in background — return id immediately
  after(async () => {
    const baseUrl = process.env.PUBLIC_URL
      || (process.env.VERCEL_URL ? `https://${process.env.VERCEL_URL}` : "http://localhost:3000");

    try {
      const payload = { query, api_key: apiKey };
      console.log(`[actions.after] calling /api/run, api_key: ${apiKey ? `${apiKey.slice(0, 8)}...${apiKey.slice(-4)} (len=${apiKey.length})` : "EMPTY"}`);
      const res = await fetch(`${baseUrl}/api/run`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${process.env.INTERNAL_API_SECRET}`,
        },
        body: JSON.stringify(payload),
      });

      if (!res.ok || !res.body) {
        let body = "";
        try { body = await res.text(); } catch {}
        await put(
          `runs/${id}/_error.json`,
          JSON.stringify({
            error: `Python function returned ${res.status}`,
            status: res.status,
            statusText: res.statusText,
            body,
            url: res.url,
            timestamp: new Date().toISOString(),
          }),
          { access: "public", contentType: "application/json" },
        );
        return;
      }

      // Read JSONL stream incrementally — write one blob per stage as it arrives
      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });

        const lines = buffer.split("\n");
        buffer = lines.pop()!;

        for (const line of lines) {
          if (!line.trim()) continue;
          const data = JSON.parse(line);

          if (data.type === "stage") {
            const suffix = data.component ? `__${data.component}` : "";
            const name = `${String(data.step).padStart(2, "0")}_${data.stage}${suffix}.json`;
            await put(`runs/${id}/${name}`, JSON.stringify(data), {
              access: "public",
              contentType: "application/json",
            });
          } else if (data.type === "completed") {
            await put(`runs/${id}/_completed.json`, JSON.stringify(data), {
              access: "public",
              contentType: "application/json",
            });
          }
        }
      }
    } catch (err) {
      await put(
        `runs/${id}/_error.json`,
        JSON.stringify({
          error: String(err),
          stack: err instanceof Error ? err.stack : undefined,
          timestamp: new Date().toISOString(),
        }),
        { access: "public", contentType: "application/json" },
      );
    }
  });

  return { id };
}

export async function getRunStatus(id: string) {
  const { blobs } = await list({ prefix: `runs/${id}/` });

  if (blobs.length === 0) {
    return { id, status: "not_found" as const, meta: null, stages: [], completed: null, error: null };
  }

  const entries = await Promise.all(
    blobs.map(async (blob) => {
      const res = await fetch(blob.url);
      const data = await res.json();
      const name = blob.pathname.split("/").pop()!;
      return { name, data };
    }),
  );

  const meta = entries.find((e) => e.name === "_meta.json")?.data ?? null;
  const completed = entries.find((e) => e.name === "_completed.json")?.data ?? null;
  const error = entries.find((e) => e.name === "_error.json")?.data ?? null;
  const stages = entries
    .filter((e) => !e.name.startsWith("_"))
    .sort((a, b) => a.name.localeCompare(b.name))
    .map((e) => e.data);

  return {
    id,
    status: error ? ("error" as const) : completed ? ("completed" as const) : ("running" as const),
    meta,
    stages,
    completed,
    error,
  };
}
