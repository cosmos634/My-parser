# Lead Finder

A lightweight client-discovery tool for collecting, scoring, and reviewing public freelance leads.

## Current phase

The first milestone provides:
- SQLite storage
- deterministic lead scoring (no paid AI API)
- URL and text-fingerprint duplicate detection
- CLI commands for adding, listing, and viewing statistics
- a safe foundation for later Telegram and website source adapters

Telegram and web collection adapters are intentionally not enabled yet. Add only sources you are permitted to access and respect each platform's terms and rate limits.

## Requirements

- Python 3.10+
- No third-party packages for the core MVP

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

On Windows, activate the environment with `.venv\\Scripts\\activate`.

## Usage

```bash
python main.py init
python main.py add --title "Нужен Telegram бот" --description "Нужен бот для автоматизации заказов" --source manual --source-name "Manual entry" --url "https://example.com/order"
python main.py leads
python main.py leads --hot
python main.py stats
```

The database is created at `data/leads.db` by default. Set `LEAD_FINDER_DB` to change its location.

## Lead scoring

Scoring is rule-based and explainable. It considers buyer intent, service relevance, budget, recency, and whether a public contact path is present. Scores are heuristic—not guarantees that a lead will convert.

## Safety and privacy

- No automatic outreach or messaging.
- Store only public, relevant contact details and use them for the stated purpose.
- Do not bypass logins, CAPTCHAs, access controls, or rate limits.
- Telegram monitoring should be limited to groups you joined legitimately and are allowed to monitor.
- Keep `.env`, Telegram session files, and database files out of Git.
