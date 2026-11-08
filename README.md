# Lead Finder

A lightweight client-discovery tool for collecting, scoring, and reviewing public freelance leads.

## Features

- SQLite storage and duplicate detection
- Explainable lead scoring (no paid AI API)
- Telethon user-session monitor for public groups/channels you can legitimately access
- Public-source discovery suggestions by keyword (sources are not auto-joined)
- Telegram bot notifications, hourly scans, and admin commands
- No automatic outreach to lead authors

## Requirements

- Python 3.10+
- Telegram API credentials from your own Telegram developer account
- A Telegram bot token
- A user account that is already a member of any private groups you choose to monitor

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Fill in `.env`:

- `TELEGRAM_API_ID` and `TELEGRAM_API_HASH`: Telegram client credentials
- `TELEGRAM_PHONE`: phone number for the Telethon user session
- `BOT_TOKEN`: token for the notification bot
- `ADMIN_ID`: your numeric Telegram user ID
- `SEARCH_KEYWORDS`: semicolon-separated phrases used to discover public sources
- `SCAN_INTERVAL_MINUTES`: scan interval (default 60)
- `MAX_MESSAGES_PER_SOURCE`: maximum recent messages read per source and scan

## First run

Authorize the Telethon user session once:

```bash
python telegram_monitor.py login
```

Then start the bot and monitor:

```bash
python telegram_monitor.py
```

Bot commands (admin only):

- `/discover` — find public source suggestions by keyword; does not join them
- `/addsource username` — add a public group/channel you can access
- `/sources` — list configured sources
- `/scan` — run a scan now
- `/status` — show lead statistics

The first monitoring cycle starts immediately; subsequent cycles run at the configured interval.

## CLI

```bash
python main.py init
python main.py add --title "Нужен Telegram бот" --description "Нужен бот для автоматизации заказов" --source manual --source-name "Manual entry" --url "https://example.com/order"
python main.py leads
python main.py leads --hot
python main.py stats
```

The database is created at `data/leads.db` by default. Set `LEAD_FINDER_DB` to change its location.

## Important limits and privacy

- Telegram does not provide a way to enumerate every group and channel on the platform. Discovery results are suggestions, not a complete directory.
- Monitor only public sources and groups/channels you have legitimately joined and are permitted to monitor.
- The parser reads recent messages only; it does not scrape member lists, harvest phone numbers, bypass access controls, or send unsolicited messages.
- Only a message author's public username is shown as a contact path. If none is public, the report says so.
- Telegram may enforce flood waits. The client observes Telegram's wait responses; do not increase scan frequency to evade limits.
- Keep `.env`, Telethon session files, and database files private and out of Git.
- Scores are heuristic and do not guarantee that a lead will convert.
