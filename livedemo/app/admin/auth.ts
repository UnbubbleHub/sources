import crypto from "crypto";
import { cookies } from "next/headers";

const TOKEN_TTL_MS = 24 * 60 * 60 * 1000; // 24 hours

function sign(payload: string, secret: string): string {
  return crypto.createHmac("sha256", secret).update(payload).digest("hex");
}

/** Create a signed admin session token. */
export function createAdminToken(): string {
  const secret = process.env.ADMIN_SECRET;
  if (!secret) throw new Error("ADMIN_SECRET not configured");
  const expiry = Date.now() + TOKEN_TTL_MS;
  return `${expiry}.${sign(String(expiry), secret)}`;
}

/** Verify a signed admin session token. Returns true if valid and not expired. */
export function verifyAdminToken(token: string): boolean {
  const secret = process.env.ADMIN_SECRET;
  if (!secret) return false;
  const dot = token.indexOf(".");
  if (dot === -1) return false;
  const expiry = token.slice(0, dot);
  const sig = token.slice(dot + 1);
  if (Date.now() > Number(expiry)) return false;
  const expected = sign(expiry, secret);
  return crypto.timingSafeEqual(Buffer.from(sig), Buffer.from(expected));
}

/** Check if current request has a valid admin session. */
export async function isAdmin(): Promise<boolean> {
  const jar = await cookies();
  const token = jar.get("unbubble_admin")?.value;
  if (!token) return false;
  return verifyAdminToken(token);
}
