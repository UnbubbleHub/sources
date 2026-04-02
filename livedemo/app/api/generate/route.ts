import crypto from "crypto";
import { after } from "next/server";
import { list, put } from "@vercel/blob";

export async function POST(req: Request) {
  const { query, api_key } = await req.json();

  // Deterministic ID: hash(query + date) → same query on same day = same id
  const today = new Date().toISOString().slice(0, 10);
  const id = crypto
    .createHash("sha256")
    .update(query + today)
    .digest("hex")
    .slice(0, 16);

  // Idempotency: if _meta.json already exists, skip re-running
  const { blobs } = await list({ prefix: `runs/${id}/_meta.json` });
  if (blobs.length > 0) {
    return Response.json({ id });
  }

  // Write _meta.json immediately
  await put(
    `runs/${id}/_meta.json`,
    JSON.stringify({ query, started_at: new Date().toISOString(), date: today }),
    { access: "public", contentType: "application/json" },
  );

  // Fire pipeline in background — return id immediately
  after(async () => {
    const baseUrl = process.env.VERCEL_URL
      ? `https://${process.env.VERCEL_URL}`
      : "http://localhost:3000";

    const res = await fetch(`${baseUrl}/api/run`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query, api_key }),
    });

    if (!res.ok || !res.body) {
      await put(
        `runs/${id}/_error.json`,
        JSON.stringify({ error: `Python function returned ${res.status}` }),
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
      buffer = lines.pop()!; // keep incomplete line in buffer

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
  });

  return Response.json({ id });
}
