"use server";

import crypto from "crypto";
import { cookies, headers } from "next/headers";
import { sql } from "@/app/db";

/** Get or create a visitor ID cookie, and record the visit in Postgres. */
export async function trackVisit(path: string) {
  const jar = await cookies();
  let visitorId = jar.get("unbubble_vid")?.value;

  if (!visitorId) {
    visitorId = crypto.randomUUID();
    jar.set("unbubble_vid", visitorId, {
      httpOnly: true,
      secure: true,
      sameSite: "strict",
      path: "/",
      maxAge: 60 * 60 * 24 * 365, // 1 year
    });
  }

  if (process.env.NODE_ENV === "development") return visitorId;

  const hdrs = await headers();
  const referrer = hdrs.get("referer") ?? null;
  const ua = hdrs.get("user-agent") ?? null;

  // Fire-and-forget — don't block the page
  sql(
    "INSERT INTO analytics_visits (visitor_id, path, referrer, user_agent) VALUES ($1, $2, $3, $4)",
    [visitorId, path, referrer, ua],
  ).catch((err) => console.error("[analytics] visit insert failed:", err));

  return visitorId;
}

/** Read the visitor ID from the cookie (does not create one). */
export async function getVisitorId(): Promise<string | null> {
  const jar = await cookies();
  return jar.get("unbubble_vid")?.value ?? null;
}
