# Discord Plex Liveboard Bot

A Discord bot focused on Plex server status tracking, staff notifications, and a live status board.

## Features

### Liveboards
- `/plexliveboardstart`, `/plexliveboardrefresh`, and `/plexliveboardstop` manage a Plex status board
- Plex statuses update automatically from webhook log messages and optional direct URL health checks
- The liveboard includes a user-facing button that lets members report their assigned Plex server as down when the board is wrong
- Staff can clear those manual down reports directly from the staff report message

### Admin Commands
- `/reportpings` toggles staff pings for Plex down reports
- `/synccommands` forces a slash-command sync for the current server

### Presence and Reliability
- Rotating `Watching ...` bot presence themed around IPTV, channels, and trending media
- Persistent Discord views so buttons keep working across bot restarts
- Dockerized deployment for straightforward hosting
- SQLite persistence for Plex statuses, liveboards, and manual override state

## Bot Presence (Watching Status)

The bot displays a rotating **“Watching …”** status themed around IPTV, live TV, and popular shows/movies.

### How it works
- Status updates every **5 minutes**
- Titles are chosen from:
  - Local IPTV / TV channel names
  - IPTV-themed phrases

### Example statuses
- Watching BBC One
- Watching Sky Sports News
- Watching IPTV playlists

## Plex URL health checks

The Plex liveboard can also poll three direct server URLs every 5 minutes and fold those results into the stored Plex status values.

Add these values to your `.env` to enable the poller:

```env
PLEX_ALPHA_URL=https://alpha.example.com/web/index.html
PLEX_OMEGA_URL=https://omega.example.com/web/index.html
PLEX_DELTA_URL=https://delta.example.com/web/index.html
PLEX_PROBE_TIMEOUT_SECONDS=15
PLEX_PROBE_INTERVAL_MINUTES=5
```

Rules used by the poller:
- If the response status is `404`, the server is marked `Down`
- If the response is `200` but the trimmed/lowercased body is exactly `404 page not found`, the server is marked `Down`
- If the host times out or cannot be reached, the server is marked `Down`
- Any other successful response is treated as `Up`

If none of the three Plex URL values are set, webhook-only behavior remains in place. If you enable the poller, set all three URLs together.

Manual down reports remain sticky while the server is still unhealthy, but they no longer require staff cleanup once recovery is confirmed. If a later Plex webhook or URL health check detects that the same server is back up, the bot automatically clears the staff report and restores the liveboard status to `Up`.

## Setup

### 1. Clone the repo
```bash 
git clone https://github.com/yourname/discord-reports-bot.git
cd discord-reports-bot
```

### 2. Create environment file
```bash 
cp .env.example .env
```
Fill in your values for the Discord token, staff channel, staff role, and optional Plex probe settings.

### 3. Run with Docker
```bash 
docker compose up -d --build
```
## Notes
- Do **not** commit your `.env`
- Runtime data is stored in `./data` via Docker volume
