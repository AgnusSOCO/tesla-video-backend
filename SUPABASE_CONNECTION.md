# Supabase Database Connection Details

Your Tesla Video Player Supabase project has been successfully created!

## Project Information

- **Project Name**: tesla-video-player
- **Project ID**: mvcrhadtrdtjpkrunnto
- **Region**: us-east-1 (US East)
- **Status**: ACTIVE_HEALTHY
- **PostgreSQL Version**: 17.6.1.063
- **API URL**: https://mvcrhadtrdtjpkrunnto.supabase.co

## Database Connection

To get your connection string:

1. Go to [Supabase Dashboard](https://supabase.com/dashboard/project/mvcrhadtrdtjpkrunnto)
2. Navigate to **Settings** → **Database**
3. Scroll to **Connection string**
4. Select **Connection pooling** → **Transaction mode**
5. Copy the connection string (it will look like):
   ```
   postgresql://postgres.mvcrhadtrdtjpkrunnto:[YOUR-PASSWORD]@aws-0-us-east-1.pooler.supabase.com:6543/postgres
   ```
6. Replace `[YOUR-PASSWORD]` with your actual database password

## Database Schema Created

The following tables have been successfully created:

### 1. **users**
- Stores user information from authentication
- Columns: id, open_id, name, email, login_method, role, created_at, updated_at, last_signed_in
- Indexes: unique on open_id

### 2. **telegram_sessions**
- Links Telegram accounts to web app sessions
- Columns: id, auth_token, telegram_user_id, telegram_username, user_id, verified, created_at, expires_at
- Indexes: unique on auth_token, index on auth_token
- Foreign key: user_id → users.id

### 3. **videos**
- Stores video metadata and file information
- Columns: id, user_id, youtube_id, title, description, thumbnail_url, duration, file_key, file_url, file_size, mime_type, status, created_at, updated_at
- Indexes: user_id, youtube_id
- Foreign key: user_id → users.id

### 4. **download_queue**
- Tracks video download requests
- Columns: id, user_id, youtube_url, youtube_id, status, error_message, video_id, created_at, updated_at
- Indexes: user_id, status
- Foreign keys: user_id → users.id, video_id → videos.id

## Enums Created

- **role**: 'user', 'admin'
- **video_status**: 'downloading', 'ready', 'failed'
- **download_status**: 'pending', 'processing', 'completed', 'failed'

## Performance Indexes

The following indexes have been created for optimal query performance:

- `idx_videos_user_id` on videos(user_id)
- `idx_videos_youtube_id` on videos(youtube_id)
- `idx_telegram_sessions_token` on telegram_sessions(auth_token)
- `idx_download_queue_user_id` on download_queue(user_id)
- `idx_download_queue_status` on download_queue(status)

## Next Steps

1. **Get your connection string** from the Supabase dashboard (see instructions above)

2. **Add to Railway** environment variables:
   ```bash
   DATABASE_URL=your-connection-string-here
   ```

3. **Add to Telegram bot** environment variables:
   ```bash
   DATABASE_URL=your-connection-string-here
   ```

4. **Test the connection** locally:
   ```bash
   export DATABASE_URL="your-connection-string"
   npm run db:push
   ```

## Supabase Dashboard

Access your project dashboard at:
https://supabase.com/dashboard/project/mvcrhadtrdtjpkrunnto

From there you can:
- View and edit data in the Table Editor
- Monitor database performance
- Set up Row Level Security (RLS) policies
- Configure storage buckets
- View logs and metrics
- Manage API keys

## Cost

This project is on the **Pro plan** at **$10/month**, which includes:
- 8 GB database storage
- 50 GB bandwidth per month
- 100 GB file storage
- Daily backups
- Point-in-time recovery
- Better performance and support

## Security Recommendations

1. **Enable Row Level Security (RLS)** on all tables to ensure users can only access their own data
2. **Use environment variables** for connection strings (never commit to git)
3. **Rotate database password** regularly
4. **Enable SSL** for all connections (already enabled by default)
5. **Monitor usage** in the Supabase dashboard

## Support

For Supabase-specific issues:
- [Supabase Documentation](https://supabase.com/docs)
- [Supabase Support](https://supabase.com/support)
- [Supabase Discord](https://discord.supabase.com)

---

**Database is ready to use!** 🎉

Copy your connection string and add it to Railway and your Telegram bot configuration.
