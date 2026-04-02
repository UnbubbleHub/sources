import { list } from "@vercel/blob";

export async function GET(
  _req: Request,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params;
  const { blobs } = await list({ prefix: `runs/${id}/` });

  if (blobs.length === 0) {
    return Response.json({ status: "not_found" }, { status: 404 });
  }

  // Fetch all blobs in parallel
  const entries = await Promise.all(
    blobs.map(async (blob) => {
      const res = await fetch(blob.url);
      const data = await res.json();
      const name = blob.pathname.split("/").pop()!;
      return { name, data };
    }),
  );

  const meta = entries.find((e) => e.name === "_meta.json")?.data;
  const completed = entries.find((e) => e.name === "_completed.json")?.data;
  const error = entries.find((e) => e.name === "_error.json")?.data;
  const stages = entries
    .filter((e) => !e.name.startsWith("_"))
    .sort((a, b) => a.name.localeCompare(b.name))
    .map((e) => e.data);

  return Response.json({
    id,
    status: error ? "error" : completed ? "completed" : "running",
    meta,
    stages,
    completed,
    error,
  });
}
