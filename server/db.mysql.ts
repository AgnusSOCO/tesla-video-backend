import { eq, desc, and } from "drizzle-orm";
import { drizzle } from "drizzle-orm/mysql2";
import { 
  InsertUser, 
  users, 
  videos, 
  InsertVideo,
  telegramSessions,
  InsertTelegramSession,
  downloadQueue,
  InsertDownloadQueue
} from "../drizzle/schema";
import { ENV } from './_core/env';

let _db: ReturnType<typeof drizzle> | null = null;

export async function getDb() {
  if (!_db && process.env.DATABASE_URL) {
    try {
      _db = drizzle(process.env.DATABASE_URL);
    } catch (error) {
      console.warn("[Database] Failed to connect:", error);
      _db = null;
    }
  }
  return _db;
}

export async function upsertUser(user: InsertUser): Promise<void> {
  if (!user.openId) {
    throw new Error("User openId is required for upsert");
  }

  const db = await getDb();
  if (!db) {
    console.warn("[Database] Cannot upsert user: database not available");
    return;
  }

  try {
    const values: InsertUser = {
      openId: user.openId,
    };
    const updateSet: Record<string, unknown> = {};

    const textFields = ["name", "email", "loginMethod"] as const;
    type TextField = (typeof textFields)[number];

    const assignNullable = (field: TextField) => {
      const value = user[field];
      if (value === undefined) return;
      const normalized = value ?? null;
      values[field] = normalized;
      updateSet[field] = normalized;
    };

    textFields.forEach(assignNullable);

    if (user.lastSignedIn !== undefined) {
      values.lastSignedIn = user.lastSignedIn;
      updateSet.lastSignedIn = user.lastSignedIn;
    }
    if (user.role !== undefined) {
      values.role = user.role;
      updateSet.role = user.role;
    } else if (user.openId === ENV.ownerOpenId) {
      values.role = 'admin';
      updateSet.role = 'admin';
    }

    if (!values.lastSignedIn) {
      values.lastSignedIn = new Date();
    }

    if (Object.keys(updateSet).length === 0) {
      updateSet.lastSignedIn = new Date();
    }

    await db.insert(users).values(values).onDuplicateKeyUpdate({
      set: updateSet,
    });
  } catch (error) {
    console.error("[Database] Failed to upsert user:", error);
    throw error;
  }
}

export async function getUserByOpenId(openId: string) {
  const db = await getDb();
  if (!db) {
    console.warn("[Database] Cannot get user: database not available");
    return undefined;
  }

  const result = await db.select().from(users).where(eq(users.openId, openId)).limit(1);

  return result.length > 0 ? result[0] : undefined;
}

// Telegram Session Management
export async function createTelegramSession(session: InsertTelegramSession) {
  const db = await getDb();
  if (!db) throw new Error("Database not available");

  await db.insert(telegramSessions).values(session);
}

export async function getTelegramSessionByToken(authToken: string) {
  const db = await getDb();
  if (!db) return undefined;

  const result = await db
    .select()
    .from(telegramSessions)
    .where(eq(telegramSessions.authToken, authToken))
    .limit(1);

  return result.length > 0 ? result[0] : undefined;
}

export async function updateTelegramSession(
  authToken: string,
  updates: Partial<InsertTelegramSession>
) {
  const db = await getDb();
  if (!db) throw new Error("Database not available");

  await db
    .update(telegramSessions)
    .set(updates)
    .where(eq(telegramSessions.authToken, authToken));
}

// Video Management
export async function createVideo(video: InsertVideo) {
  const db = await getDb();
  if (!db) throw new Error("Database not available");

  const result = await db.insert(videos).values(video);
  return result[0].insertId;
}

export async function getUserVideos(userId: number) {
  const db = await getDb();
  if (!db) return [];

  return await db
    .select()
    .from(videos)
    .where(and(eq(videos.userId, userId), eq(videos.status, "ready")))
    .orderBy(desc(videos.createdAt));
}

export async function getVideoById(videoId: number, userId: number) {
  const db = await getDb();
  if (!db) return undefined;

  const result = await db
    .select()
    .from(videos)
    .where(and(eq(videos.id, videoId), eq(videos.userId, userId)))
    .limit(1);

  return result.length > 0 ? result[0] : undefined;
}

export async function updateVideo(videoId: number, updates: Partial<InsertVideo>) {
  const db = await getDb();
  if (!db) throw new Error("Database not available");

  await db.update(videos).set(updates).where(eq(videos.id, videoId));
}

export async function deleteVideo(videoId: number, userId: number) {
  const db = await getDb();
  if (!db) throw new Error("Database not available");

  await db
    .delete(videos)
    .where(and(eq(videos.id, videoId), eq(videos.userId, userId)));
}

// Download Queue Management
export async function createDownloadRequest(request: InsertDownloadQueue) {
  const db = await getDb();
  if (!db) throw new Error("Database not available");

  const result = await db.insert(downloadQueue).values(request);
  return result[0].insertId;
}

export async function getDownloadRequest(requestId: number) {
  const db = await getDb();
  if (!db) return undefined;

  const result = await db
    .select()
    .from(downloadQueue)
    .where(eq(downloadQueue.id, requestId))
    .limit(1);

  return result.length > 0 ? result[0] : undefined;
}

export async function updateDownloadRequest(
  requestId: number,
  updates: Partial<InsertDownloadQueue>
) {
  const db = await getDb();
  if (!db) throw new Error("Database not available");

  await db.update(downloadQueue).set(updates).where(eq(downloadQueue.id, requestId));
}

export async function getPendingDownloads() {
  const db = await getDb();
  if (!db) return [];

  return await db
    .select()
    .from(downloadQueue)
    .where(eq(downloadQueue.status, "pending"))
    .orderBy(downloadQueue.createdAt);
}
