import { describe, expect, it } from "vitest";
import { appRouter } from "./routers";
import type { TrpcContext } from "./_core/context";

type AuthenticatedUser = NonNullable<TrpcContext["user"]>;

function createAuthContext(userId: number = 1): TrpcContext {
  const user: AuthenticatedUser = {
    id: userId,
    openId: `test-user-${userId}`,
    email: `test${userId}@example.com`,
    name: `Test User ${userId}`,
    loginMethod: "telegram",
    role: "user",
    createdAt: new Date(),
    updatedAt: new Date(),
    lastSignedIn: new Date(),
  };

  const ctx: TrpcContext = {
    user,
    req: {
      protocol: "https",
      headers: {},
    } as TrpcContext["req"],
    res: {
      clearCookie: () => {},
    } as TrpcContext["res"],
  };

  return ctx;
}

describe("videos.list", () => {
  it("returns empty array for authenticated user with no videos", async () => {
    const ctx = createAuthContext();
    const caller = appRouter.createCaller(ctx);

    const result = await caller.videos.list();

    expect(Array.isArray(result)).toBe(true);
    expect(result.length).toBe(0);
  });

  it("requires authentication", async () => {
    const ctx: TrpcContext = {
      user: undefined,
      req: {
        protocol: "https",
        headers: {},
      } as TrpcContext["req"],
      res: {
        clearCookie: () => {},
      } as TrpcContext["res"],
    };

    const caller = appRouter.createCaller(ctx);

    await expect(caller.videos.list()).rejects.toThrow();
  });
});

describe("videos.requestDownload", () => {
  it("creates download request with valid YouTube URL", async () => {
    const ctx = createAuthContext();
    const caller = appRouter.createCaller(ctx);

    const result = await caller.videos.requestDownload({
      youtubeUrl: "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
      youtubeId: "dQw4w9WgXcQ",
    });

    expect(result).toHaveProperty("requestId");
    expect(result.status).toBe("pending");
    expect(typeof result.requestId).toBe("number");
  });

  it("requires authentication for download requests", async () => {
    const ctx: TrpcContext = {
      user: undefined,
      req: {
        protocol: "https",
        headers: {},
      } as TrpcContext["req"],
      res: {
        clearCookie: () => {},
      } as TrpcContext["res"],
    };

    const caller = appRouter.createCaller(ctx);

    await expect(
      caller.videos.requestDownload({
        youtubeUrl: "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        youtubeId: "dQw4w9WgXcQ",
      })
    ).rejects.toThrow();
  });
});

describe("auth.generateAuthToken", () => {
  it("generates unique auth token", async () => {
    const ctx = createAuthContext();
    const caller = appRouter.createCaller(ctx);

    const result = await caller.auth.generateAuthToken();

    expect(result).toHaveProperty("authToken");
    expect(typeof result.authToken).toBe("string");
    expect(result.authToken.length).toBeGreaterThan(0);
  });

  it("generates different tokens on multiple calls", async () => {
    const ctx = createAuthContext();
    const caller = appRouter.createCaller(ctx);

    const result1 = await caller.auth.generateAuthToken();
    const result2 = await caller.auth.generateAuthToken();

    expect(result1.authToken).not.toBe(result2.authToken);
  });
});
