import type { VercelRequest, VercelResponse } from "@vercel/node";
import { list } from "@vercel/blob";

export default async function handler(req: VercelRequest, res: VercelResponse) {
  if (req.method !== "GET") {
    return res.status(405).json({ error: "Method not allowed" });
  }

  const { id } = req.query;
  if (typeof id !== "string") {
    return res.status(400).json({ error: "Missing id" });
  }

  const { blobs } = await list({ prefix: `runs/${id}/` });

  if (blobs.length === 0) {
    return res.status(404).json({ id, status: "not_found" });
  }

  const entries = await Promise.all(
    blobs.map(async (blob) => {
      const r = await fetch(blob.url);
      const data = await r.json();
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

  return res.json({
    id,
    status: error ? "error" : completed ? "completed" : "running",
    meta,
    stages,
    completed,
    error,
  });
}
