"""Lead Finder command-line interface."""

import argparse
import json
import logging
from lead_finder.database import DEFAULT_DB, add_lead, get_stats, init_db, list_leads
from lead_finder.scoring import score_lead

logging.basicConfig(
    filename="lead-finder.log",
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)


def main():
    parser = argparse.ArgumentParser(description="Lead Finder — client discovery MVP")
    parser.add_argument("--db", default=DEFAULT_DB, help="SQLite database path")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("init", help="Initialize the database")
    add = sub.add_parser("add", help="Add and score a lead")
    add.add_argument("--title", required=True)
    add.add_argument("--description", default="")
    add.add_argument("--source", default="manual")
    add.add_argument("--source-name", default="Manual")
    add.add_argument("--url")
    add.add_argument("--contact")
    add.add_argument("--budget")
    add.add_argument("--published-at", help="ISO date, e.g. 2026-11-07T08:30:00+05:00")

    leads = sub.add_parser("leads", help="List saved leads")
    leads.add_argument("--hot", action="store_true")
    leads.add_argument("--limit", type=int, default=30)
    sub.add_parser("stats", help="Show lead statistics")

    args = parser.parse_args()
    if args.command == "init":
        init_db(args.db)
        print(f"Database initialized: {args.db}")
    elif args.command == "add":
        init_db(args.db)
        analysis = score_lead(args.title, args.description, args.budget, args.contact, args.published_at)
        data = {
            "title": args.title, "description": args.description,
            "source": args.source, "source_name": args.source_name,
            "url": args.url, "contact": args.contact, "budget": args.budget,
            "published_at": args.published_at, **analysis,
        }
        created, lead_id = add_lead(data, args.db)
        if created:
            print(f"Saved lead #{lead_id}: {analysis['status']} {analysis['score']}/100")
            print("Scoring:", json.dumps(analysis["score_breakdown"], ensure_ascii=False))
        else:
            print("Duplicate skipped: this URL or content already exists.")
    elif args.command == "leads":
        init_db(args.db)
        rows = list_leads(args.hot, args.limit, args.db)
        if not rows:
            print("No leads found.")
        for row in rows:
            print(f"\\n[{row['status']}] {row['score']}/100 — {row['title']}")
            print(f"Category: {row['category']} | Intent: {row['intent']} | Language: {row['language']}")
            print(f"Source: {row['source_name']} ({row['source']})")
            print(f"Budget: {row['budget'] or 'Unknown'} | Contact: {row['contact'] or 'Not provided'}")
            print(f"URL: {row['url'] or 'Not provided'}")
    elif args.command == "stats":
        init_db(args.db)
        print(json.dumps(get_stats(args.db), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
