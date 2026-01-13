import { int, mysqlEnum, mysqlTable, text, timestamp, varchar, bigint, boolean } from "drizzle-orm/mysql-core";

/**
 * Core user table backing auth flow.
 */
export const users = mysqlTable("users", {
  id: int("id").autoincrement().primaryKey(),
  openId: varchar("openId", { length: 64 }).notNull().unique(),
  name: text("name"),
  email: varchar("email", { length: 320 }),
  loginMethod: varchar("loginMethod", { length: 64 }),
  role: mysqlEnum("role", ["user", "admin"]).default("user").notNull(),
  createdAt: timestamp("createdAt").defaultNow().notNull(),
  updatedAt: timestamp("updatedAt").defaultNow().onUpdateNow().notNull(),
  lastSignedIn: timestamp("lastSignedIn").defaultNow().notNull(),
});

export type User = typeof users.$inferSelect;
export type InsertUser = typeof users.$inferInsert;

/**
 * Telegram authentication sessions
 * Links web app auth tokens to Telegram user IDs
 */
export const telegramSessions = mysqlTable("telegram_sessions", {
  id: int("id").autoincrement().primaryKey(),
  authToken: varchar("authToken", { length: 64 }).notNull().unique(),
  telegramUserId: bigint("telegramUserId", { mode: "number" }),
  telegramUsername: varchar("telegramUsername", { length: 255 }),
  userId: int("userId").references(() => users.id),
  verified: boolean("verified").default(false).notNull(),
  createdAt: timestamp("createdAt").defaultNow().notNull(),
  expiresAt: timestamp("expiresAt").notNull(),
});

export type TelegramSession = typeof telegramSessions.$inferSelect;
export type InsertTelegramSession = typeof telegramSessions.$inferInsert;

/**
 * Video library
 * Stores metadata and file information for downloaded videos
 */
export const videos = mysqlTable("videos", {
  id: int("id").autoincrement().primaryKey(),
  userId: int("userId").notNull().references(() => users.id),
  youtubeId: varchar("youtubeId", { length: 64 }), // Optional - only for YouTube videos
  title: text("title").notNull(),
  description: text("description"),
  thumbnailUrl: text("thumbnailUrl"),
  duration: int("duration"), // Duration in seconds
  fileKey: text("fileKey").notNull(), // S3 file key
  fileUrl: text("fileUrl").notNull(), // S3 URL
  fileSize: bigint("fileSize", { mode: "number" }), // File size in bytes
  mimeType: varchar("mimeType", { length: 100 }),
  status: mysqlEnum("status", ["downloading", "ready", "failed"]).default("downloading").notNull(),
  createdAt: timestamp("createdAt").defaultNow().notNull(),
  updatedAt: timestamp("updatedAt").defaultNow().onUpdateNow().notNull(),
});

export type Video = typeof videos.$inferSelect;
export type InsertVideo = typeof videos.$inferInsert;

/**
 * Download queue
 * Tracks video download requests from Telegram bot
 */
export const downloadQueue = mysqlTable("download_queue", {
  id: int("id").autoincrement().primaryKey(),
  userId: int("userId").notNull().references(() => users.id),
  youtubeUrl: text("youtubeUrl").notNull(),
  youtubeId: varchar("youtubeId", { length: 64 }), // Optional - only for YouTube videos
  status: mysqlEnum("status", ["pending", "processing", "completed", "failed"]).default("pending").notNull(),
  errorMessage: text("errorMessage"),
  videoId: int("videoId").references(() => videos.id),
  createdAt: timestamp("createdAt").defaultNow().notNull(),
  updatedAt: timestamp("updatedAt").defaultNow().onUpdateNow().notNull(),
});

export type DownloadQueue = typeof downloadQueue.$inferSelect;
export type InsertDownloadQueue = typeof downloadQueue.$inferInsert;
