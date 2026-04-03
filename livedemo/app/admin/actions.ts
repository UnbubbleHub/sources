"use server";

import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { createAdminToken, verifyAdminToken } from "./auth";

export async function adminLogin(password: string): Promise<{ error?: string }> {
  const expected = process.env.ADMIN_PASSWORD;
  if (!expected) return { error: "Admin login not configured" };
  if (password !== expected) return { error: "Wrong password" };

  const token = createAdminToken();
  const jar = await cookies();
  jar.set("unbubble_admin", token, {
    httpOnly: true,
    secure: true,
    sameSite: "strict",
    path: "/admin",
    maxAge: 60 * 60 * 24, // 24h
  });

  return {};
}

export async function adminLogout() {
  const jar = await cookies();
  jar.delete("unbubble_admin");
  redirect("/admin/login");
}

export async function checkAdmin(): Promise<boolean> {
  const jar = await cookies();
  const token = jar.get("unbubble_admin")?.value;
  if (!token) return false;
  return verifyAdminToken(token);
}
