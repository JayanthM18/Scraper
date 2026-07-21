"""
Flexible X (Twitter) scraper.

Scrapes either:
  - a user's profile timeline
  - search results for a query

Approach: uses Playwright to drive a real browser session (authenticated via
your exported cookies), and intercepts the site's own internal GraphQL
network responses (UserTweets / SearchTimeline / TweetDetail) rather than
parsing the rendered DOM. The DOM's CSS classes are obfuscated and change
often; the GraphQL JSON payloads are much more stable.

Usage:
    Edit the config block below (MODE, TARGET, LIMIT, etc.) to whatever you
    want to scrape, then run:
        python main.py

Getting cookies.json:
    Log in to x.com in your normal browser, then export cookies with an
    extension like "Cookie-Editor" (Export -> JSON), and save that file as cookies.json

NOTE: This is for personal / research use.
DO NOT scrape at high volume, and DO NOT redistribute or resell scraped data.
"""

import csv
import json
import sys
import time
from pathlib import Path
from urllib.parse import quote

from playwright.sync_api import sync_playwright



# ---------------------------------------------------------------------------
# EDIT THESE to change what gets scraped. No command-line flags needed.
# ---------------------------------------------------------------------------
MODE = "profile"          # "profile" (a user's timeline) or "search" (a query)
TARGET = "sandlogictech"       # username for profile mode, or search text for search mode
LIMIT = 50                # how many tweets to collect
COOKIES_PATH = "cookies.json"
OUT_PATH = "tweets.csv"
HEADFUL = False           # True = show the browser window while it runs
# ---------------------------------------------------------------------------




GRAPHQL_MARKERS = ("UserTweets", "SearchTimeline", "UserByScreenName", "TweetDetail")
CSV_FIELDS = ["id", "screen_name", "created_at", "text", "reply_count", "retweet_count", "like_count", "quote_count"]

# Fields Playwright's context.add_cookies() accepts. Browser export tools
# (Cookie-Editor, Chrome devtools, etc.) include extra fields like
# "partitionKey" or "hostOnly" that Playwright rejects, so we filter to these.
PLAYWRIGHT_COOKIE_FIELDS = {"name", "value", "domain", "path", "expires", "httpOnly", "secure", "sameSite"}


def load_cookies(path: str) -> list[dict]:
    with open(path, "r", encoding="utf-8") as f:
        raw_cookies = json.load(f)

    cookies = []
    for c in raw_cookies:
        clean = {k: v for k, v in c.items() if k in PLAYWRIGHT_COOKIE_FIELDS}
        if clean.get("sameSite") not in ("Strict", "Lax", "None"):
            clean["sameSite"] = "Lax"
        clean.setdefault("domain", ".x.com")
        clean.setdefault("path", "/")
        if "expires" not in clean and "expirationDate" in c:
            clean["expires"] = c["expirationDate"]  # Cookie-Editor's name for the field
        cookies.append(clean)
    return cookies


def extract_tweets_from_json(data) -> list[dict]:
    """Walk a GraphQL JSON blob and pull out tweet objects, tracking the
    nearest enclosing author (from a "core" -> user_results block) as we go."""
    results = []

    def walk(node, author=None):
        if isinstance(node, dict):
            core = node.get("core")
            if isinstance(core, dict):
                try:
                    author = core["user_results"]["result"]["legacy"]["screen_name"]
                except (KeyError, TypeError):
                    pass

            if "full_text" in node and "created_at" in node:
                results.append({
                    "id": node.get("id_str"),
                    "screen_name": author,
                    "created_at": node.get("created_at"),
                    "text": node.get("full_text", "").replace("\n", " ").strip(),
                    "reply_count": node.get("reply_count"),
                    "retweet_count": node.get("retweet_count"),
                    "like_count": node.get("favorite_count"),
                    "quote_count": node.get("quote_count"),
                })

            for v in node.values():
                walk(v, author)
        elif isinstance(node, list):
            for item in node:
                walk(item, author)

    walk(data)
    return results


def scrape(mode: str, target: str, limit: int, cookies_path: str, headless: bool = True) -> list[dict]:
    collected: dict[str, dict] = {}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                       "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
        )
        context.add_cookies(load_cookies(cookies_path))
        page = context.new_page()

        def on_response(response):
            if not any(marker in response.url for marker in GRAPHQL_MARKERS):
                return
            try:
                data = response.json()
            except Exception:
                return
            for tweet in extract_tweets_from_json(data):
                if tweet["id"] and tweet["id"] not in collected:
                    collected[tweet["id"]] = tweet

        page.on("response", on_response)

        if mode == "profile":
            page.goto(f"https://x.com/{target}", wait_until="domcontentloaded")
        else:
            page.goto(f"https://x.com/search?q={quote(target)}&src=typed_query&f=live", wait_until="domcontentloaded")

        time.sleep(3)  # let the first batch of GraphQL calls land

        # Scroll to trigger pagination until we hit the limit or stop seeing new tweets.
        stagnant_rounds, last_count = 0, 0
        while len(collected) < limit and stagnant_rounds < 6:
            page.mouse.wheel(0, 3000)
            time.sleep(2)
            stagnant_rounds = stagnant_rounds + 1 if len(collected) == last_count else 0
            last_count = len(collected)

        browser.close()

    return list(collected.values())[:limit]


def save_csv(tweets: list[dict], out_path: str):
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(tweets)


def main():
    if not Path(COOKIES_PATH).exists():
        print(f"Cookie file not found: {COOKIES_PATH}")
        print("Export your x.com cookies as JSON (e.g. with the 'Cookie-Editor' browser extension)")
        sys.exit(1)

    print(f"Scraping {MODE} target={TARGET!r} limit={LIMIT} ...")
    tweets = scrape(MODE, TARGET, LIMIT, COOKIES_PATH, headless=not HEADFUL)
    save_csv(tweets, OUT_PATH)
    print(f"Saved {len(tweets)} tweets to {OUT_PATH}")


if __name__ == "__main__":
    main()