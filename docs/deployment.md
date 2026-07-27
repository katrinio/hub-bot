# Deployment Guide — The Hub Bot Production

## Architecture Overview

```
Telegram API
      ↑ (HTTPS outbound)
      ↓
┌──────────────────────────┐
│   The Hub Bot Container  │
│  (Python 3.14 + aiogram) │
│   Polling-based          │
│   No HTTP server         │
└──────────────────────────┘
      ↑
      ↓
┌──────────────────────────┐
│   Docker Compose         │
│   (compose.yml)          │
└──────────────────────────┘
      ↑
      ↓
┌──────────────────────────┐
│   VPS                    │
│   (Linux, Docker daemon) │
└──────────────────────────┘
```

**Key properties:**
- ✓ Single polling instance (one bot token, one process)
- ✓ No HTTP server, no public port
- ✓ Restart policy: `unless-stopped`
- ✓ Graceful shutdown via SIGTERM
- ✓ Logs to stdout/stderr (Docker captures them)
- ✓ Configuration via environment variables

---

## Prerequisites

On the target VPS:

1. **Docker and Docker Compose** installed
   ```bash
   docker --version       # ≥ 20.10
   docker compose version # ≥ 2.x
   ```

2. **Production secrets:**
   - `TELEGRAM_BOT_TOKEN` (from @BotFather)
   - `HUB_AUTH_SECRET` (32-byte hex from `openssl rand -hex 32`)
   - `POSTBOX_URL` (e.g., https://postbox.finpipe.net)

3. **Access to repository** (git clone)

---

## Required Environment Variables

### TELEGRAM_BOT_TOKEN

Telegram bot token from @BotFather.

```
Format: <numeric>:<alphanumeric>
Example: 123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11
```

**Do NOT share or commit this token.**

### HUB_AUTH_SECRET

Shared secret for signing JWT tokens between Hub Bot and Postbox.

```bash
# Generate a new random secret:
openssl rand -hex 32
```

**Critical:** This value must be **identical** in:
- The Hub Bot (`.env`)
- Postbox deployment

**Do NOT regenerate this during updates** unless rotating all secrets.

### POSTBOX_URL

Public URL where Postbox is deployed.

```
Examples:
  https://postbox.finpipe.net
  https://postbox.example.com
```

Used to generate auth URLs for users (not hardcoded).

---

## Directory Structure

Production layout on VPS:

```
/home/username/projects/hub-bot/
├── compose.yml          # Docker Compose configuration
├── .env                 # Production secrets (mode 600)
├── Dockerfile           # Build configuration
├── .dockerignore        # Build exclusions
├── src/                 # Application source
├── pyproject.toml       # Dependencies
├── poetry.lock          # Locked versions
└── docs/                # Documentation
```

**On your machine (before deploy):**

```bash
git clone https://github.com/katrintt/the-hub-bot.git
cd the-hub-bot
```

---

## First Deployment

⚠️ **BEFORE YOU START:** Stop any local bot instances with the same token:

```bash
pkill -f "python -m hub_bot"     # Kill local bot if running
sleep 2                          # Wait for cleanup
ps aux | grep "python -m hub_bot"  # Verify it's stopped (should be empty)
```

**Why?** Only ONE polling instance can use the token. Running both local and production simultaneously will cause conflicts.

---

### 1. Prepare Environment File

```bash
# Copy template
cp .env.example .env

# Restrict permissions (production secrets)
chmod 600 .env

# Edit with production values
nano .env
```

Fill in:
```
TELEGRAM_BOT_TOKEN=<your-bot-token>
HUB_AUTH_SECRET=<32-byte-hex-secret>
POSTBOX_URL=https://postbox.finpipe.net
```

### 2. Build Docker Image

```bash
# Build locally or pull from registry
docker compose build

# Verify build
docker images | grep the-hub-bot
```

### 3. Start Container

```bash
# Start in background (detached)
docker compose up -d

# Check status
docker compose ps
```

Expected output:
```
NAME            STATUS          PORTS
the-hub-bot     Up 2 seconds    
```

### 4. Verify Startup

```bash
# View last 100 lines of logs
docker compose logs --tail=100 hub-bot

# Expected log output:
# INFO - Starting polling
# INFO - Bot session started
```

If you see configuration errors:
```
ERROR - TELEGRAM_BOT_TOKEN not found
```

Then check `.env` values and permissions without printing secrets:
```bash
test -s .env && ls -l .env
docker compose restart hub-bot
docker compose logs --tail=100 hub-bot
```

### 5. Run Smoke Test

See [Smoke Test](#smoke-test) section below.

---

## Update Flow

Production deploy is automated by GitHub Actions. A push or merge to `main` starts `.github/workflows/deploy.yml`.
The workflow first runs:

```bash
poetry run pytest
poetry run ruff check .
poetry run mypy src
```

Only after those checks pass, GitHub Actions connects to the VPS over SSH and runs the production deploy script.
Pull requests are not deployed before merge.

The same workflow also supports manual redeploy through **GitHub Actions → Deploy Production → Run workflow**.

### Remote Deploy Script

The workflow executes this on the VPS:

```bash
set -euo pipefail

cd ~/projects/hub-bot

git fetch origin main
git reset --hard origin/main

docker compose build
docker compose up -d --remove-orphans

docker compose ps
sleep 5
docker compose ps

container_id="$(docker compose ps -q hub-bot)"
if [ -z "$container_id" ]; then
  echo "hub-bot container is missing after deploy"
  docker compose ps
  docker compose logs --tail=100 hub-bot
  exit 1
fi

status="$(docker inspect -f '{{.State.Status}}' "$container_id")"
restarting="$(docker inspect -f '{{.State.Restarting}}' "$container_id")"

if [ "$status" != "running" ] || [ "$restarting" = "true" ]; then
  echo "hub-bot container is not healthy after deploy: status=$status restarting=$restarting"
  docker compose ps
  docker compose logs --tail=100 hub-bot
  exit 1
fi

docker compose logs --tail=50 hub-bot
docker image prune -f
```

The deploy intentionally does not run `docker compose down`, does not run `git clean`, does not scale the service, and does not start another bot instance in CI.
`git reset --hard origin/main` updates tracked files only; the production `.env` is untracked/gitignored and remains only on the VPS.
GitHub Actions passes only SSH connection secrets and never passes or prints application secrets such as `TELEGRAM_BOT_TOKEN`, `HUB_AUTH_SECRET`, or `POSTBOX_URL`.

The workflow uses:

```yaml
concurrency:
  group: production-deploy
  cancel-in-progress: true
```

This prevents overlapping production deploy jobs for the polling bot.

### Rollback

If the new version has issues:

```bash
cd ~/projects/hub-bot

git log --oneline
git reset --hard <known-good-commit>
docker compose build
docker compose up -d

docker compose ps
docker compose logs --tail=100 hub-bot
```

The next automatic deploy from `main` will reset production back to `origin/main`. To make rollback durable, revert or fix `main` and let the workflow deploy that commit.

---

## Operational Tasks

### View Logs

Run these on the VPS from `~/projects/hub-bot`.

**Live logs (follow mode):**
```bash
docker compose logs -f hub-bot
```

**Last N lines:**
```bash
docker compose logs --tail=100 hub-bot
```

**Timestamps enabled:**
```bash
docker compose logs --timestamps hub-bot
```

### Restart Container

Useful after configuration changes or to recover from transient issues:

```bash
# Restart (maintains data/logs)
docker compose restart hub-bot

# Forceful restart
docker compose kill hub-bot
docker compose up -d
```

### Stop Container

For maintenance:

```bash
# Graceful stop (SIGTERM, allows clean shutdown)
docker compose stop hub-bot

# Verify stopped
docker compose ps

# Restart
docker compose start hub-bot
```

### Check Resource Usage

```bash
docker stats the-hub-bot
```

Shows: CPU %, memory usage, network I/O, block I/O.

### Inspect Container

```bash
# Running processes
docker compose exec hub-bot ps aux

# Current working directory
docker compose exec hub-bot pwd
```

---

## Logs and Monitoring

### Log Output

All logs from the container are captured by Docker and can be viewed:

```bash
docker compose logs hub-bot
```

**Format:**
```
2026-07-27 14:35:12,345 - hub_bot.handlers - INFO - Hub auth: created new user for telegram_id=123456789
2026-07-27 14:35:13,456 - hub_bot.bot - INFO - Starting polling
```

### Important: Secrets NOT Logged

Verified in code:
- ✓ `TELEGRAM_BOT_TOKEN` — never logged
- ✓ `HUB_AUTH_SECRET` — never logged
- ✓ JWT tokens — never logged
- ✓ Full Postbox auth URLs — never logged (only error types)

Example safe logging:
```python
# ✓ GOOD: Only error type (not token)
logger.error("Failed to create Postbox auth token: %s", type(e).__name__)

# ✗ BAD (not in code): Would log secret
# logger.error(f"Secret: {secret}")
```

### Log Rotation

Docker json-file driver is configured with log rotation:
- **Max file size:** 10 MB
- **Max files:** 3 (30 MB total per container)

Located at:
```
/var/lib/docker/containers/<container-id>/<container-id>-json.log
```

No manual rotation needed.

---

## Graceful Shutdown

The bot correctly handles shutdown signals:

```bash
# SIGTERM from 'docker compose stop'
docker compose stop hub-bot

# OR from 'docker compose down'
docker compose down
```

**What happens:**

1. Docker sends SIGTERM to bot process
2. aiogram gracefully stops polling
3. Bot closes Telegram session
4. Logs: `"Bot session closed"`
5. Process exits (exit code 0)

**Timeout:** Docker waits 10 seconds for graceful shutdown, then kills.

You can verify this behavior:
```bash
docker compose stop --time=20 hub-bot  # Custom timeout
```

---

## Restart Behavior

### Automatic Restart (after crash)

Configured in `compose.yml`:
```yaml
restart: unless-stopped
```

**What it does:**
- Bot crashes? Automatically restarts
- Bot runs successfully? Continues running
- VPS reboots? Bot starts automatically
- Manual `docker compose stop`? Container stops (respects unless-stopped)

### Testing Restart

```bash
# Force container exit (simulates crash)
docker compose exec hub-bot kill 1

# Check logs (should show restart)
docker compose logs --tail=20 hub-bot

# Verify it's running again
docker compose ps
```

---

## Health Strategy

### Current Approach: Process + Restart Policy

This Hub Bot deployment uses a minimal health strategy:

1. **Process alive check:** Docker restarts if main process dies
2. **Restart policy:** Automatic recovery from crashes
3. **Manual monitoring:** Administrator checks logs periodically

**Why not a dedicated healthcheck?**
- No HTTP server to check (polling bot)
- Adding FastAPI just for health would add complexity
- Simple `docker stats` is sufficient for this service

### Simple Monitoring (Manual)

```bash
# Is container running?
docker compose ps

# Recent logs (check for errors)
docker compose logs --tail=50 hub-bot | grep -i error

# Resource usage
docker stats the-hub-bot
```

For production, recommend:
- Set up log aggregation (e.g., Loki) for metrics
- Configure alerts on error patterns
- Daily manual checks of logs

---

## ⚠️ CRITICAL REQUIREMENT: Single Polling Instance

🚨 **MUST READ BEFORE FIRST DEPLOY** 🚨

Only ONE polling instance must be active with a given Telegram bot token at any time.

### Why?

Telegram only allows one polling connection per bot. If multiple instances poll:
- Both receive updates (duplicate processing)
- Conflicts arise in shared state
- Bot behavior becomes unpredictable

### How to ensure it?

1. **Never scale the service:**
   ```yaml
   # ✓ CORRECT (compose.yml):
   services:
     hub-bot:
       # No replicas, no scaling
   ```

   ```bash
   # ✗ WRONG (would break polling):
   docker compose up -d --scale hub-bot=3
   ```

2. **STOP the local bot before starting production:**
   ```bash
   # ✗ CRITICAL ERROR: Both polling with same token
   poetry run python -m hub_bot &
   docker compose up -d  # BREAKS — both will fight for updates
   
   # ✓ CORRECT: Only one instance
   pkill -f "python -m hub_bot"     # Kill local bot
   sleep 2
   docker compose up -d             # Start production
   ```
   
   **Warning:** If you leave local bot running during production smoke test:
   - Both instances receive updates (duplicates)
   - Messages may be handled by wrong instance
   - Bot appears "broken" or unreliable
   - Telegram API sees polling conflicts

3. **Verify single instance:**
   ```bash
   docker compose ps | grep hub-bot  # Should show 1 container
   docker stats the-hub-bot           # Should show 1 process
   ```

---

## Shared Secret: HUB_AUTH_SECRET

### Requirement

Hub Bot and Postbox **must share the same `HUB_AUTH_SECRET`**.

If they differ:
- Hub Bot generates tokens with one secret
- Postbox tries to verify with different secret
- Verification fails: "Invalid signature"

### Setup

**First time:**
```bash
# Generate ONE secret
SECRET=$(openssl rand -hex 32)
echo $SECRET  # Note it

# Set in Hub Bot
echo "HUB_AUTH_SECRET=$SECRET" >> .env

# Set in Postbox
# (Postbox also has HUB_AUTH_SECRET in its .env)
```

**Never change during operation** unless rotating all tokens (rare).

### Verification

After deployment, test auth flow end-to-end:

1. Click Postbox button in Hub Bot
2. Open Postbox link
3. Check Postbox logs: no "Invalid signature" errors
4. User should be logged in

If you see in Postbox logs:
```
InvalidSignature: Signature verification failed
```

Then `HUB_AUTH_SECRET` values don't match. Fix it:
```bash
# Update Hub Bot secret
sed -i 's/HUB_AUTH_SECRET=.*/HUB_AUTH_SECRET=<correct-secret>/' .env

# Restart
docker compose restart hub-bot
```

---

## Smoke Test

After deployment, run this checklist to verify everything works:

### Prerequisites

- Hub Bot container is running (`docker compose ps`)
- You have a valid Telegram account
- You can access deployed Postbox

### Test Steps

1. **Container running**
   ```bash
   docker compose ps
   # STATUS: Up X seconds
   ```

2. **No startup errors**
   ```bash
   docker compose logs hub-bot | grep -i error
   # Should show: (no errors, only info/debug)
   ```

3. **Open Telegram, send /start**
   - Expected: See "The Hub" menu with apps

4. **Click "📦 Postbox" button**
   - Expected: See "Всё готово. Ссылка для входа действует 5 минут."
   - Button: "Открыть Postbox ↗" (with valid URL)
   - Button: "← The Hub"

5. **Click "Открыть Postbox ↗" button**
   - Browser opens auth URL
   - URL format: `https://postbox.finpipe.net/auth/hub?token=...`
   - **Token should NOT be visible after redirect** (URL should show just `/`)

6. **Postbox login succeeds**
   - You see Postbox home screen
   - User is authenticated (verified)

7. **Go back to Telegram, send /start again**
   - Menu appears again
   - Can repeat steps 4-6

8. **Test restart**
   ```bash
   docker compose restart hub-bot
   
   # Wait 2 seconds for startup
   sleep 2
   
   # Send /start in Telegram
   # Should work same as step 3
   ```

**If any step fails:**

```bash
# Check logs for errors
docker compose logs --tail=100 hub-bot

# Common issues:
# - "TELEGRAM_BOT_TOKEN not found" → check .env
# - "HUB_AUTH_SECRET not configured" → check Postbox
# - "POSTBOX_URL not configured" → check .env
# - No response from bot → check Docker status, network connectivity
```

---

## Security Checklist

Before production:

- [x] Container runs as non-root user (`appuser`)
- [x] `.env` not committed to git (add to `.gitignore`)
- [x] `.env` permissions: `600` (readable only by owner)
- [x] Secrets NOT in Dockerfile build args
- [x] Secrets NOT in image layers (docker image inspect)
- [x] Secrets NOT logged by application
- [x] No published ports in `compose.yml`
- [x] `HUB_AUTH_SECRET` matches Postbox deployment
- [x] `.dockerignore` excludes `.git`, `.env`, secrets
- [x] Only one polling instance active
- [x] Logs are captured by Docker driver

---

## Configuration References

### Environment Variables

```bash
# Required
TELEGRAM_BOT_TOKEN=<bot-token>
HUB_AUTH_SECRET=<hex-secret>
POSTBOX_URL=https://postbox.finpipe.net
```

### Files

- `compose.yml` — Docker Compose configuration
- `.env` — Production secrets (not committed)
- `Dockerfile` — Container build definition
- `pyproject.toml` — Python dependencies
- `poetry.lock` — Locked versions

### Useful Commands

```bash
# Deployment
docker compose build
docker compose up -d
docker compose down

# Operations
docker compose logs -f hub-bot
docker compose restart hub-bot
docker compose ps
docker stats the-hub-bot

# Debugging
docker compose exec hub-bot env
docker compose exec hub-bot ps aux
```

---

## Troubleshooting

### Bot doesn't start / exits immediately

```bash
docker compose logs hub-bot
```

**Common causes:**

1. **Missing TELEGRAM_BOT_TOKEN**
   ```
   ERROR - TELEGRAM_BOT_TOKEN not found
   ```
   Fix: Set in `.env`, restart

2. **Network issues** (can't reach Telegram API)
   ```
   ERROR - requests.ConnectionError: HTTPConnectionPool
   ```
   Fix: Check VPS internet, proxy settings

3. **Invalid token format**
   ```
   ERROR - ...InvalidBotTokenException
   ```
   Fix: Verify token from @BotFather, no extra spaces

### Bot starts but doesn't respond to /start

```bash
# Check logs
docker compose logs hub-bot | grep -i start

# Verify handlers are loaded
docker compose logs hub-bot | grep -i "handler\|router"

# Restart
docker compose restart hub-bot
```

### Can't connect to Postbox from Hub auth button

```bash
# Check that POSTBOX_URL is present without printing its value
docker compose exec hub-bot sh -c 'test -n "$POSTBOX_URL"'

# Verify it's reachable from VPS
docker compose exec hub-bot curl -I https://postbox.finpipe.net

# Check logs for auth errors
docker compose logs hub-bot | grep -i postbox
```

### High memory or CPU usage

```bash
docker stats the-hub-bot

# Check for polling loops or event leaks
docker compose logs --tail=200 hub-bot | tail -50
```

If excessive, check for bot crash/restart loop:
```bash
docker compose logs hub-bot | grep -i restart
```

---

## Next Steps

### Monitoring & Observability

For production, consider:
- Log aggregation (Loki, ELK)
- Metrics collection (Prometheus)
- Alerting (Grafana, PagerDuty)
- But keep this stage minimal; add as needed

### Automated Deployments

GitHub Actions automatically deploys production after a successful push or merge to `main`.
Manual redeploy is available from **GitHub Actions → Deploy Production → Run workflow**.
The diagnostic `SSH Check` workflow remains manual and does not deploy code.

---

## Support & Documentation

For issues:

1. Check logs: `docker compose logs hub-bot`
2. Review this guide's Troubleshooting section
3. Check application documentation: `docs/auth.md`, `docs/architecture.md`
4. Review code: `src/hub_bot/__main__.py` (startup), `src/hub_bot/handlers.py` (auth)

---

**Last updated:** 2026-07-28
**Version:** 1.1 (Automated GitHub Actions production deployment)
