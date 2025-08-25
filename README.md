# Overseerr Discord Bot

A lightweight Discord bot that talks to your Overseerr server and lets users search and request media—**gated by Plex account linking** (device code flow). Tokens are stored locally in **SQLite**, encrypted with **Fernet**.

## Features

- `!link` — user links their Plex account via a short code (`plex.tv/link`)
- `!search "<query>"` — search movies & TV in Overseerr
- `!request <tmdb_id>` — request a title (only works for linked users)
- `!unlink` — remove your Plex link
- Local encrypted token store (`tokens.db`) using `cryptography.Fernet`

## Requirements

- Python 3.11+
- A Discord bot token
- An Overseerr instance + API key

## Quick Start

1) **Clone**
```bash
git clone https://github.com/darklink701/overseerr-bot.git
cd overseerr-bot
```

2) **Virtual env + deps**
```bash
python -m venv venv
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate

pip install -r requirements.txt
```

3) **Environment variables** (create a `.env` file in the repo root):
```env
DISCORD_BOT_TOKEN=your_discord_bot_token
OVERSEERR_URL=http://your-overseerr-host:5055
OVERSEERR_API_KEY=your_overseerr_api_key
# Optional: PLEX_CLIENT_ID (defaults to "johnny-cage-bot")
# PLEX_CLIENT_ID=my-bot-id
# Required for encryption (generate once: `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`)
CRYPTO_KEY=your_fernet_key_here
```

4) **Run**
```bash
python bot.py
```

You should see logs like:
```
Logged in as <botname> (ID: ...)
JOHNNY CAGE IS READY TO ROCK!
```

## Commands

- `!link`  
  DMs you a short Plex code (e.g. `ABCD`). Go to https://plex.tv/link and enter it. The bot polls Plex and stores your Plex token encrypted in `tokens.db`.

- `!search <query>`  
  Shows the top Overseerr results (movies/TV).

- `!request <tmdb_id>`  
  Requests the item by TMDb ID. The bot auto-detects `movie` vs `tv` by probing Overseerr’s `/movie/{id}` and `/tv/{id}`. **Requires** you to be linked (`!link`) first.

- `!unlink`  
  Deletes your stored Plex token.

## How It Works

- **Plex link (device code)**  
  The bot uses the Plex **v1 PIN XML** endpoints:
  - `POST https://plex.tv/pins.xml` → returns a short code + pin id  
  - `GET  https://plex.tv/pins/{pin_id}.xml` until `authToken` appears  
  That token is saved (encrypted) per Discord user.

- **Requests to Overseerr**  
  The bot uses your **Overseerr API key**. To request:
  ```json
  { "mediaType": "movie" | "tv", "mediaId": <tmdb_id> }
  ```
  (We auto-detect `mediaType` by probing `/api/v1/movie/{id}` then `/api/v1/tv/{id}`.)

- **Token store**  
  SQLite file `tokens.db`, with encrypted Plex tokens using `cryptography.Fernet` + `CRYPTO_KEY`. One row per Discord user.

## Security Notes

- **Never commit `.env`** or `tokens.db`. (Both are in `.gitignore`.)
- Generate and keep your `CRYPTO_KEY` secret. Changing it later will invalidate old encrypted tokens.

## Troubleshooting

- **Bot DMs aren’t received**: The user’s DMs might be closed. They need to allow DMs from server members (or you can handle it in-channel).
- **Heartbeat blocked / lag**: Make sure you’re not using `time.sleep()` in async code. This bot uses `await asyncio.sleep(...)` and runs blocking `requests` calls in a thread with `asyncio.to_thread(...)`.
- **“Already requested”**: Overseerr returns HTTP 409 if the item is already requested.
- **Pylance “Optional” warnings**: In `on_ready`, cast `bot.user` to `discord.ClientUser` or assert it’s not `None`.

## Project Structure

```
overseerr-bot/
├─ bot.py             # Discord bot: commands + Plex link flow
├─ token_store.py     # SQLite + Fernet token storage
├─ requirements.txt   # Python deps
├─ .gitignore
└─ LICENSE
```

## Roadmap (nice-to-haves)

- Per-user quotas / rate limits
- Rich embeds for requests (title, poster, status)
- Admin-only commands (approve/deny)
- Switch `requests` → `aiohttp` for fully async HTTP
- CI linting & tests

---

PRs welcome. If you break it, Johnny Cage will break you. 🥊
