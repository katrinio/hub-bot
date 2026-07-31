# Deployment Guide — The Hub Bot

## Production Startup Flow

### Prerequisites
1. `.env` file is **CRITICAL** — must exist on VPS with all variables set:
   ```bash
   TELEGRAM_BOT_TOKEN=<your_token>
   DATABASE_URL=sqlite+aiosqlite:///./data/hub.db
   ADMIN_TELEGRAM_ID=<your_telegram_id>
   APP_TIMEZONE=Europe/Belgrade
   POSTBOX_URL=<your_url>
   HUB_AUTH_SECRET=<your_secret>
   ```

2. `.env` should be in `.gitignore` (secrets!)
3. `./data` directory must exist and be writable by container user

### First-Time Deploy

```bash
# 1. On VPS, create .env with production values
scp .env user@vps:/path/to/hub-bot/

# 2. Check that .env is readable
docker compose config | grep -A 20 "hub-bot:"

# 3. Verify DATABASE_URL before starting
docker compose run --rm \
  --env-file .env \
  hub-bot sh -c 'test -n "$DATABASE_URL" && echo "✓ DATABASE_URL: $DATABASE_URL"'

# 4. Run migrations (creates schema)
docker compose run --rm \
  --env-file .env \
  hub-bot alembic upgrade head

# 5. Start bot in background
docker compose up -d --remove-orphans
```

### Verify Deployment

```bash
# Check logs
docker compose logs hub-bot

# Verify database was created
docker compose exec hub-bot ls -la ./data/hub.db

# Test bot connection by sending /start to bot
```

### Restart (Preserve Data)

```bash
# .env is preserved, data/ is mounted as volume
docker compose restart hub-bot

# Or full restart:
docker compose down
docker compose up -d
```

### Troubleshooting

#### "ERROR: DATABASE_URL not set"
- Check `.env` file exists in project root
- Verify `env_file: .env` in `compose.yml`
- Run: `docker compose config | grep -i database_url`

#### "Database is locked"
- Ensure only one container instance running: `docker compose ps`
- Check file permissions: `ls -la data/hub.db`

#### "Alembic: No such table: users"
- Migrations didn't run, run manually:
  ```bash
  docker compose run --rm --env-file .env hub-bot alembic upgrade head
  ```

## Environment Variables

| Variable | Required | Default | Notes |
|----------|----------|---------|-------|
| `TELEGRAM_BOT_TOKEN` | ✅ Yes | — | From @BotFather |
| `DATABASE_URL` | ✅ Yes | — | SQLite path inside container: `sqlite+aiosqlite:///./data/hub.db` |
| `ADMIN_TELEGRAM_ID` | ❌ No | — | Numeric only; /stats unavailable if not set |
| `APP_TIMEZONE` | ❌ No | `Europe/Belgrade` | For "today" calculation in stats |
| `POSTBOX_URL` | ❌ No | — | App integration URL |
| `HUB_AUTH_SECRET` | ✅ Yes | — | For Postbox auth tokens |

## Deployment Checklist

- [ ] `.env` file created with all required variables
- [ ] `.env` is **NOT** in git (check `.gitignore`)
- [ ] `.data/` directory exists and writable
- [ ] `docker compose config` shows correct env_file
- [ ] `docker compose run` diagnostics pass
- [ ] Migrations run successfully (`alembic upgrade head`)
- [ ] `docker compose up -d` starts without errors
- [ ] Bot responds to `/start` command
- [ ] Logs show "Starting polling" without errors

## File Permissions

Inside container, bot runs as non-root `appuser`:
```dockerfile
USER appuser
```

Make sure `/app/data` is writable:
```bash
docker compose exec hub-bot touch ./data/test.txt && rm ./data/test.txt
```

## Database Backups

SQLite database is at `./data/hub.db` on VPS.

Backup before major updates:
```bash
cp data/hub.db data/hub.db.backup.$(date +%Y%m%d_%H%M%S)
```
