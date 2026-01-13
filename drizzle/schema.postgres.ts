import { integer, pgEnum, pgTable, text, timestamp, varchar, bigint, boolean } from "drizzle-orm/pg-core";

/**
 * PostgreSQL schema for Supabase deployment
 * Core user table backing auth flow.
 */
export const roleEnum = pgEnum("role", ["user", "admin"]);
export const videoStatusEnum = pgEnum("video_status", ["downloading", "ready", "failed"]);
export const downloadStatusEnum = pgEnum("download_status", ["pending", "processing", "completed", "failed"]);

export const users = pgTable("users", {
  id: integer("id").primaryKey().generatedAlwaysAsIdentity(),
  openId: varchar("open_id", { length: 64 }).notNull().unique(),
  name: text("name"),
  email: varchar("email", { length: 320 }),
  loginMethod: varchar("login_method", { length: 64 }),
  role: roleEnum("role").default("user").notNull(),
  createdAt: timestamp("created_at").defaultNow().notNull(),
  updatedAt: timestamp("updated_at").defaultNow().notNull(),
  lastSignedIn: timestamp("last_signed_in").defaultNow().notNull(),
});

export type User = typeof users.$inferSelect;
export type InsertUser = typeof users.$inferInsert;

/**
 * Telegram authentication sessions
 * Links web app auth tokens to Telegram user IDs
 */
export const telegramSessions = pgTable("telegram_sessions", {
  id: integer("id").primaryKey().generatedAlwaysAsIdentity(),
  authToken: varchar("auth_token", { length: 64 }).notNull().unique(),
  telegramUserId: bigint("telegram_user_id", { mode: "number" }),
  telegramUsername: varchar("telegram_username", { length: 255 }),
  userId: integer("user_id").references(() => users.id),
  verified: boolean("verified").default(false).notNull(),
  createdAt: timestamp("created_at").defaultNow().notNull(),
  expiresAt: timestamp("expires_at").notNull(),
});

export type TelegramSession = typeof telegramSessions.$inferSelect;
export type InsertTelegramSession = typeof telegramSessions.$inferInsert;

/**
 * Video library
 * Stores metadata and file information for downloaded videos
 */
export const videos = pgTable("videos", {
  id: integer("id").primaryKey().generatedAlwaysAsIdentity(),
  userId: integer("user_id").notNull().references(() => users.id),
  youtubeId: varchar("youtube_id", { length: 64 }).notNull(),
  title: text("title").notNull(),
  description: text("description"),
  thumbnailUrl: text("thumbnail_url"),
  duration: integer("duration"), // Duration in seconds
  fileKey: text("file_key").notNull(), // S3 file key
  fileUrl: text("file_url").notNull(), // S3 URL
  fileSize: bigint("file_size", { mode: "number" }), // File size in bytes
  mimeType: varchar("mime_type", { length: 100 }),
  status: videoStatusEnum("status").default("downloading").notNull(),
  createdAt: timestamp("created_at").defaultNow().notNull(),
  updatedAt: timestamp("updated_at").defaultNow().notNull(),
});

export type Video = typeof videos.$inferSelect;
export type InsertVideo = typeof videos.$inferInsert;

/**
 * Download queue
 * Tracks video download requests from Telegram bot
 */
export const downloadQueue = pgTable("download_queue", {
  id: integer("id").primaryKey().generatedAlwaysAsIdentity(),
  userId: integer("user_id").notNull().references(() => users.id),
  youtubeUrl: text("youtube_url").notNull(),
  youtubeId: varchar("youtube_id", { length: 64 }).notNull(),
  status: downloadStatusEnum("status").default("pending").notNull(),
  errorMessage: text("error_message"),
  videoId: integer("video_id").references(() => videos.id),
  createdAt: timestamp("created_at").defaultNow().notNull(),
  updatedAt: timestamp("updated_at").defaultNow().notNull(),
});

export type DownloadQueue = typeof downloadQueue.$inferSelect;
export type InsertDownloadQueue = typeof downloadQueue.$inferInsert;
