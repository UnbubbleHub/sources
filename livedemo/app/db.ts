import { neon } from "@neondatabase/serverless";

const neonSql = neon(process.env.DATABASE_URL!);

export function sql(text: string, params: unknown[] = []) {
  return neonSql.query(text, params);
}
