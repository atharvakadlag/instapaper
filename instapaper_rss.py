#!/usr/bin/env python3
"""Push new items from a handful of RSS feeds into Instapaper.

Usage:
    python instapaper_rss.py           # save new items
    python instapaper_rss.py --seed    # mark everything current as seen, save nothing

Env:
    INSTAPAPER_USER  your Instapaper login email
    INSTAPAPER_PASS  your Instapaper password (empty string if account has none)
"""
import json
import os
import pathlib
import sys

import feedparser
import requests

FEEDS = [
    "https://aeon.co/feed.rss",
    "https://api.quantamagazine.org/feed/",
    "https://restofworld.org/feed/latest",
]

API = "https://www.instapaper.com/api/add"
STATE = pathlib.Path(__file__).with_name("seen.json")
MAX_PER_FEED = 20  # don't flood on the first run or after a long gap

USER = os.environ["INSTAPAPER_USER"]
PASSWORD = os.environ.get("INSTAPAPER_PASS", "")


def load_seen() -> set:
    if STATE.exists():
        return set(json.loads(STATE.read_text()))
    return set()


def save_seen(seen: set) -> None:
    STATE.write_text(json.dumps(sorted(seen), indent=0))


def send_to_instapaper(url: str, title: str) -> None:
    resp = requests.post(
        API,
        auth=(USER, PASSWORD),
        data={"url": url, "title": title},
        timeout=30,
    )
    # 201 = created. 403 = bad credentials. 400 = bad/unparseable URL.
    if resp.status_code != 201:
        raise RuntimeError(f"instapaper {resp.status_code} for {url}: {resp.text[:200]}")


def main() -> int:
    seed_only = "--seed" in sys.argv
    seen = load_seen()
    added = 0

    for feed_url in FEEDS:
        parsed = feedparser.parse(feed_url)
        if not parsed.entries:
            print(f"WARN: no entries from {feed_url} — check the feed URL", file=sys.stderr)
            continue

        for entry in parsed.entries[:MAX_PER_FEED]:
            link = getattr(entry, "link", None)
            if not link:
                continue
            key = getattr(entry, "id", None) or link
            if key in seen:
                continue

            if not seed_only:
                send_to_instapaper(link, getattr(entry, "title", ""))
                print("saved:", link)
                added += 1
            seen.add(key)

    save_seen(seen)
    print(f"{'seeded' if seed_only else 'added'}: {added if not seed_only else len(seen)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
