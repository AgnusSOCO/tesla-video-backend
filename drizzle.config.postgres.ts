import { defineConfig } from "drizzle-kit";

export default defineConfig({
  schema: "./drizzle/schema.postgres.ts",
  out: "./drizzle/migrations-postgres",
  dialect: "postgresql",
  dbCredentials: {
    url: process.env.DATABASE_URL!,
  },
});
