"use server";

import crypto from "crypto";
import { after } from "next/server";
import { get, list, put } from "@vercel/blob";

export async function generate(query: string, apiKey: string, date?: string) {
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
    { access: "private", contentType: "application/json" },
  );

  // Fire pipeline in background — return id immediately
  after(async () => {
    const baseUrl = process.env.PUBLIC_URL
      || (process.env.VERCEL_URL ? `https://${process.env.VERCEL_URL}` : "http://localhost:3000");

    try {
      const payload = { query, api_key: apiKey };
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
        console.error(`[actions.after] /api/run failed for run ${id}: ${res.status} ${res.statusText}`, body);
        await put(
          `runs/${id}/_error.json`,
          JSON.stringify({
            error: "Pipeline failed",
            timestamp: new Date().toISOString(),
          }),
          { access: "private", contentType: "application/json" },
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
              access: "private",
              contentType: "application/json",
            });
          } else if (data.type === "completed") {
            await put(`runs/${id}/_completed.json`, JSON.stringify(data), {
              access: "private",
              contentType: "application/json",
            });
          }
        }
      }
    } catch (err) {
      console.error(`[actions.after] pipeline error for run ${id}:`, err);
      await put(
        `runs/${id}/_error.json`,
        JSON.stringify({
          error: "Pipeline failed",
          timestamp: new Date().toISOString(),
        }),
        { access: "private", contentType: "application/json" },
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
      const result = await get(blob.pathname, { access: "private" });
      const name = blob.pathname.split("/").pop()!;
      if (!result) return { name, data: null };
      const text = await new Response(result.stream).text();
      const data = JSON.parse(text);
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
