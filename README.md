# Tesla Video Player - Backend API

Backend API server for Tesla Video Player. Handles video management, Telegram authentication, and serves the tRPC API.

## Tech Stack

### Backend API
- **Node.js 22** with TypeScript
- **Express** - Web server
- **tRPC** - Type-safe API
- **Drizzle ORM** - Database ORM
- **PostgreSQL** (Supabase) - Database
- **Zod** - Schema validation

### Telegram Bot
- **Python 3.11+**
- **python-telegram-bot** - Telegram bot framework
- **yt-dlp** - YouTube video downloader
- **qrcode** - QR code generation

## Environment Variables

Required environment variables:

```bash
# Database
DATABASE_URL=postgresql://...

# Server
PORT=3000
NODE_ENV=production

# CORS (frontend URL)
FRONTEND_URL=https://your-frontend.vercel.app

# JWT Secret
JWT_SECRET=your-secret-key

# OAuth (if using Manus OAuth)
OAUTH_SERVER_URL=https://api.manus.im
VITE_APP_ID=your-app-id
OWNER_OPEN_ID=your-owner-id
OWNER_NAME=your-name
```

## Development

### Backend API

```bash
# Install dependencies
npm install

# Run database migrations
npm run db:push

# Start development server
npm run dev
```

### Telegram Bot

```bash
# Navigate to bot directory
cd telegram-bot

# Install Python dependencies
pip install -r requirements.txt

# Set environment variables
export TELEGRAM_BOT_TOKEN=your-bot-token
export DATABASE_URL=your-database-url
export API_URL=http://localhost:3000

# Run the bot
python bot.py
```

See `telegram-bot/README.md` for detailed setup instructions.

## Production Deployment

### Railway

1. Create new Railway project
2. Connect this GitHub repository
3. Add environment variables
4. Railway will auto-deploy using Dockerfile

### Docker

```bash
# Build
docker build -t tesla-video-backend .

# Run
docker run -p 3000:3000 --env-file .env tesla-video-backend
```

## API Endpoints

- `GET /health` - Health check
- `POST /api/trpc/*` - tRPC API endpoints

## Database Schema

See `drizzle/schema.postgres.ts` for full schema.

Main tables:
- `users` - User accounts
- `telegram_sessions` - Telegram auth sessions
- `videos` - Video library
- `download_queue` - Download requests

## License

MIT
