# Twitter/X Scraper

A lightweight scraper for X (Twitter) built with [Playwright](https://playwright.dev/). Instead of parsing the rendered page (whose CSS classes are obfuscated and change constantly), it intercepts X's own internal GraphQL API responses as the page loads and scrolls, and extracts tweet data directly from that JSON.

Supports two modes:
- **Profile** — scrape a user's timeline
- **Search** — scrape results for a search query

## Features

- Authenticated scraping via exported browser cookies (no official API key needed)
- Pulls tweet text, author, timestamp, and engagement counts (likes, retweets, replies, quotes)
- Auto-scrolls to paginate through results up to a configurable limit
- Exports results to CSV

## Requirements

- Python 3.10+
- A logged-in X/Twitter account (cookies exported from your browser)

## Setup

```bash
git clone https://github.com/JayanthM18/Twitter_scraper
cd twitter-scraping
python3 -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium
```

## Getting your cookies

1. Log in to x.com in your normal browser.
2. Export your cookies as JSON using a browser extension such as [Cookie-Editor](https://cookie-editor.com/).
3. Save the exported file as `cookies.json` in the project root.

See `cookies.example.json` for the expected format. **Never share your real `cookies.json` — it contains live authentication tokens for your account.**

## Usage

Open `main.py` and edit the config block near the top:

```python
MODE = "profile"          # "profile" (a user's timeline) or "search" (a query)
TARGET = "elonmusk"       # username for profile mode, or search text for search mode
LIMIT = 50                # how many tweets to collect
COOKIES_PATH = "cookies.json"
OUT_PATH = "tweets.csv"
HEADFUL = False            # True = show the browser window while it runs (useful for debugging)
```

Then run:

```bash
python main.py
```

Output is written as a CSV with columns: `id, screen_name, created_at, text, reply_count, retweet_count, like_count, quote_count`.


## Project structure

```
main.py             # everything: cookie loading, GraphQL interception, scraping, CSV export
requirements.txt    # dependencies (just Playwright)
cookies.example.json  # template showing the expected cookie format
```

## Notes and limitations

- X's internal API structure can change without notice; if scraping stops working, the GraphQL response shape may have shifted and the parser may need updating.
- This project is intended for personal use, research, and experimentation. Scraping X/Twitter is subject to their [Terms of Service](https://x.com/en/tos) — use reasonable request rates, don't redistribute scraped data, and don't use this for high-volume or commercial data collection.
- Your cookies grant full access to your account. Treat `cookies.json` like a password — never share it or commit it to version control.

## License

MIT — see [LICENSE](LICENSE).
