#!/usr/bin/env python3
"""
Performance Monitor — nesto.ca
Samples 100 random URLs, measures response times, alerts Slack if avg >= 800ms.

SETUP:
  pip3 install requests

USAGE:
  python3 monitor.py

CRON (runs every hour):
  crontab -e
  0 * * * * /usr/bin/python3 /Users/YOUR_NAME/Downloads/monitor.py >> /Users/YOUR_NAME/Downloads/monitor.log 2>&1
"""

import random
import time
import sys
import json
import urllib.request
import urllib.error
from datetime import datetime

# ─── CONFIG ───────────────────────────────────────────────────────────────────
URLS_FILE       = "urls.txt"       # your full list of URLs
SAMPLE_SIZE     = 100              # how many URLs to check each run
THRESHOLD_MS    = 800              # alert if average response time >= this
SLACK_WEBHOOK   = "YOUR_SLACK_WEBHOOK_URL_HERE"  # paste your webhook here
TIMEOUT_SECONDS = 10               # per-request timeout
# ──────────────────────────────────────────────────────────────────────────────


def load_urls():
    try:
        with open(URLS_FILE, "r") as f:
            urls = [l.strip() for l in f if l.strip().startswith("http")]
        if not urls:
            print("❌  No valid URLs found in urls.txt")
            sys.exit(1)
        return urls
    except FileNotFoundError:
        print(f"❌  Could not find '{URLS_FILE}'")
        sys.exit(1)


def measure(url):
    try:
        start = time.time()
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as r:
            r.read()
        return round((time.time() - start) * 1000)
    except Exception as e:
        return None  # timeout or error


def send_slack(avg_ms, slow_urls, sample_size, error_count):
    if SLACK_WEBHOOK == "YOUR_SLACK_WEBHOOK_URL_HERE":
        print("⚠️   Slack webhook not set — skipping notification.")
        return

    top_slow = "\n".join(
        [f"  • {ms}ms — {url}" for url, ms in slow_urls[:5]]
    )

    message = {
        "text": (
            f":warning: *nesto.ca Performance Alert*\n"
            f"Average response time: *{avg_ms}ms* (threshold: {THRESHOLD_MS}ms)\n"
            f"Sample: {sample_size} URLs  |  Errors/timeouts: {error_count}\n\n"
            f"*Slowest pages:*\n{top_slow}"
        )
    }

    try:
        data = json.dumps(message).encode("utf-8")
        req = urllib.request.Request(
            SLACK_WEBHOOK,
            data=data,
            headers={"Content-Type": "application/json"}
        )
        urllib.request.urlopen(req, timeout=10)
        print("📣  Slack alert sent.")
    except Exception as e:
        print(f"❌  Slack send failed: {e}")


def main():
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n{'─'*50}")
    print(f"🕐  Monitor run: {now}")

    all_urls = load_urls()
    sample   = random.sample(all_urls, min(SAMPLE_SIZE, len(all_urls)))

    print(f"🔍  Sampling {len(sample)} random URLs from {len(all_urls)} total...\n")

    results     = []
    errors      = []
    slow_urls   = []

    for i, url in enumerate(sample, 1):
        ms = measure(url)
        short = url.replace("https://www.nesto.ca", "")
        if ms is None:
            errors.append(url)
            print(f"  [{i:>3}] ❌  TIMEOUT  {short}")
        else:
            results.append((url, ms))
            flag = " ⚠️" if ms >= THRESHOLD_MS else ""
            print(f"  [{i:>3}] {ms:>5}ms  {short}{flag}")

    print()

    if not results:
        print("❌  All requests failed — check your connection.")
        sys.exit(1)

    avg_ms      = round(sum(ms for _, ms in results) / len(results))
    max_ms      = max(ms for _, ms in results)
    min_ms      = min(ms for _, ms in results)
    slow_urls   = sorted(results, key=lambda x: x[1], reverse=True)

    print(f"📊  Results:")
    print(f"    Avg: {avg_ms}ms  |  Min: {min_ms}ms  |  Max: {max_ms}ms")
    print(f"    Errors/timeouts: {len(errors)}/{len(sample)}")

    if avg_ms >= THRESHOLD_MS:
        print(f"\n🚨  ALERT: Average {avg_ms}ms exceeds {THRESHOLD_MS}ms threshold!")
        send_slack(avg_ms, slow_urls, len(sample), len(errors))
    else:
        print(f"\n✅  All good — average {avg_ms}ms is under {THRESHOLD_MS}ms threshold.")

    print(f"{'─'*50}\n")


if __name__ == "__main__":
    main()
