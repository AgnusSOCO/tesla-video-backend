import { COOKIE_NAME } from "@shared/const";
import { getSessionCookieOptions } from "./_core/cookies";
import { systemRouter } from "./_core/systemRouter";
import { publicProcedure, protectedProcedure, router } from "./_core/trpc";
import { z } from "zod";
import { nanoid } from "nanoid";
import {
  createTelegramSession,
  getTelegramSessionByToken,
  updateTelegramSession,
  getUserVideos,
  getVideoById,
  deleteVideo,
  createDownloadRequest,
} from "./db";
import { TRPCError } from "@trpc/server";

export const appRouter = router({
  system: systemRouter,
  
  auth: router({
    me: publicProcedure.query(opts => opts.ctx.user),
    
    logout: publicProcedure.mutation(({ ctx }) => {
      const cookieOptions = getSessionCookieOptions(ctx.req);
      ctx.res.clearCookie(COOKIE_NAME, { ...cookieOptions, maxAge: -1 });
      return { success: true } as const;
    }),

    // Generate QR code auth token for Telegram login
    generateAuthToken: publicProcedure.mutation(async () => {
      const authToken = nanoid(32);
      const expiresAt = new Date(Date.now() + 10 * 60 * 1000); // 10 minutes

      await createTelegramSession({
        authToken,
        expiresAt,
        verified: false,
      });

      return { authToken };
    }),

    // Check if auth token has been verified by Telegram bot
    checkAuthStatus: publicProcedure
      .input(z.object({ authToken: z.string() }))
      .query(async ({ input }) => {
        const session = await getTelegramSessionByToken(input.authToken);

        if (!session) {
          throw new TRPCError({
            code: "NOT_FOUND",
            message: "Auth token not found or expired",
          });
        }

        if (session.expiresAt < new Date()) {
          throw new TRPCError({
            code: "UNAUTHORIZED",
            message: "Auth token expired",
          });
        }

        return {
          verified: session.verified,
          userId: session.userId,
          telegramUsername: session.telegramUsername,
        };
      }),

    // Login with verified Telegram session
    loginWithTelegram: publicProcedure
      .input(z.object({ authToken: z.string() }))
      .mutation(async ({ input, ctx }) => {
        const session = await getTelegramSessionByToken(input.authToken);

        if (!session || !session.verified || !session.userId) {
          throw new TRPCError({
            code: "UNAUTHORIZED",
            message: "Invalid or unverified auth token",
          });
        }

        if (session.expiresAt < new Date()) {
          throw new TRPCError({
            code: "UNAUTHORIZED",
            message: "Auth token expired",
          });
        }

        // Get user from database to get openId
        const { getUserByOpenId } = await import("./db");
        const user = await getUserByOpenId(`telegram_${session.telegramUserId}`);

        if (!user) {
          throw new TRPCError({
            code: "NOT_FOUND",
            message: "User not found in database",
          });
        }

        // Create JWT session token using SDK
        const { sdk } = await import("./_core/sdk");
        const sessionToken = await sdk.createSessionToken(user.openId, {
          name: user.name || session.telegramUsername || "User",
        });

        // Set session cookie with JWT token
        const cookieOptions = getSessionCookieOptions(ctx.req);
        ctx.res.cookie(COOKIE_NAME, sessionToken, cookieOptions);

        return { success: true, userId: session.userId };
      }),
  }),

  videos: router({
    // List all videos for current user
    list: protectedProcedure.query(async ({ ctx }) => {
      const videos = await getUserVideos(ctx.user.id);
      return videos;
    }),

    // Get single video details
    get: protectedProcedure
      .input(z.object({ videoId: z.number() }))
      .query(async ({ ctx, input }) => {
        const video = await getVideoById(input.videoId, ctx.user.id);

        if (!video) {
          throw new TRPCError({
            code: "NOT_FOUND",
            message: "Video not found",
          });
        }

        return video;
      }),

    // Delete video
    delete: protectedProcedure
      .input(z.object({ videoId: z.number() }))
      .mutation(async ({ ctx, input }) => {
        const video = await getVideoById(input.videoId, ctx.user.id);

        if (!video) {
          throw new TRPCError({
            code: "NOT_FOUND",
            message: "Video not found",
          });
        }

        await deleteVideo(input.videoId, ctx.user.id);

        return { success: true };
      }),

    // Request video download (called by Telegram bot via API)
    requestDownload: protectedProcedure
      .input(
        z.object({
          youtubeUrl: z.string().url(),
          youtubeId: z.string(),
        })
      )
      .mutation(async ({ ctx, input }) => {
        const requestId = await createDownloadRequest({
          userId: ctx.user.id,
          youtubeUrl: input.youtubeUrl,
          youtubeId: input.youtubeId,
          status: "pending",
        });

        return { requestId, status: "pending" };
      }),
  }),
});

export type AppRouter = typeof appRouter;
