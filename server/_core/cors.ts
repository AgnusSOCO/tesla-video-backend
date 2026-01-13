import { Request, Response, NextFunction } from "express";

/**
 * CORS middleware for separate frontend/backend deployment
 * Allows requests from Vercel frontend to Railway backend
 */
export function corsMiddleware(req: Request, res: Response, next: NextFunction) {
  // Get allowed origins from environment variable or use defaults
  const allowedOrigins = process.env.ALLOWED_ORIGINS?.split(",") || [
    process.env.FRONTEND_URL || "http://localhost:5173",
    "https://tesla-video-player-woad.vercel.app", // Default Vercel domain
  ];

  const origin = req.headers.origin;

  // Allow requests from allowed origins or if no origin header (server-to-server)
  if (origin && allowedOrigins.includes(origin)) {
    res.setHeader("Access-Control-Allow-Origin", origin);
  } else if (!origin) {
    // For server-to-server requests or direct API calls
    res.setHeader("Access-Control-Allow-Origin", "*");
  } else if (process.env.NODE_ENV === "development") {
    // In development, allow all origins
    res.setHeader("Access-Control-Allow-Origin", origin);
  }

  res.setHeader("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS");
  res.setHeader("Access-Control-Allow-Headers", "Content-Type, Authorization, Cookie");
  res.setHeader("Access-Control-Allow-Credentials", "true");
  res.setHeader("Access-Control-Max-Age", "86400"); // Cache preflight for 24 hours

  // Handle preflight requests
  if (req.method === "OPTIONS") {
    res.sendStatus(200);
    return;
  }

  next();
}
