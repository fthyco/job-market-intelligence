"""
Upwork Data Jobs Scraper
========================
Scrapes Upwork job search results for data-related positions.
Exports results to CSV and JSON.

Usage:
    python upwork_scraper.py
    python upwork_scraper.py --keywords "data analyst" "machine learning"
    python upwork_scraper.py --max-pages 5
    python upwork_scraper.py --output results
    python upwork_scraper.py --headless          # run headless (less reliable)
"""

import argparse
import csv
import json
import logging
import os
import random
import re
import sys
import time
from datetime import datetime
from typing import Optional
from urllib.parse import quote_plus

from bs4 import BeautifulSoup

# Use undetected-chromedriver to bypass Cloudflare bot detection
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

# ──────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────

DEFAULT_KEYWORDS = [
    "data analyst",
    "data scientist",
    "data engineer",
    "data entry",
    "machine learning",
    "python data",
    "sql data",
    "power bi",
    "tableau",
    "ETL",
    "big data",
    "data visualization",
    "data pipeline",
    "data warehouse",
]

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Safari/605.1.15",
]

DELAY_MIN = 3  # seconds
DELAY_MAX = 7  # seconds

# ──────────────────────────────────────────────
# Logging
# ──────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("upwork_scraper")

# ──────────────────────────────────────────────
# Scraper
# ──────────────────────────────────────────────


class UpworkScraper:
    """Selenium-based scraper for Upwork job listings."""

    BASE_URL = "https://www.upwork.com"
    SEARCH_URL = BASE_URL + "/nx/search/jobs/?q={query}&page={page}&per_page=20"

    def __init__(self, headless: bool = False):
        self.headless = headless
        self.driver: Optional[uc.Chrome] = None
        self.jobs: list[dict] = []

    # ── Driver lifecycle ──────────────────────

    def _build_driver(self) -> uc.Chrome:
        """Create an undetected Chrome WebDriver that bypasses Cloudflare."""
        opts = uc.ChromeOptions()

        if self.headless:
            opts.add_argument("--headless=new")

        # Standard browser options
        opts.add_argument("--no-sandbox")
        opts.add_argument("--disable-dev-shm-usage")
        opts.add_argument("--window-size=1920,1080")
        opts.add_argument("--disable-gpu")
        opts.add_argument("--lang=en-US")

        # undetected-chromedriver handles:
        #  - driver patching to avoid detection
        #  - webdriver flag removal
        #  - automation extension suppression
        # Pin to installed Chrome major version to avoid mismatch
        driver = uc.Chrome(options=opts, version_main=145)

        return driver

    def start(self):
        """Start the browser."""
        log.info("Starting Chrome browser (undetected mode) …")
        self.driver = self._build_driver()
        log.info("Browser started ✓")

    def stop(self):
        """Close the browser."""
        if self.driver:
            try:
                self.driver.quit()
            except Exception:
                pass
            self.driver = None
            log.info("Browser closed ✓")

    # ── Random delay ──────────────────────────

    @staticmethod
    def _delay(label: str = "", min_s: float = DELAY_MIN, max_s: float = DELAY_MAX):
        seconds = round(random.uniform(min_s, max_s), 1)
        if label:
            log.info(f"  ⏳ Waiting {seconds}s ({label}) …")
        time.sleep(seconds)

    # ── Page navigation ───────────────────────

    def _load_page(self, url: str, wait_selector: str = "body", timeout: int = 30):
        """Navigate to a URL and wait for a CSS selector to appear."""
        self.driver.get(url)
        try:
            WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, wait_selector))
            )
        except Exception:
            log.warning(f"  ⚠ Timed out waiting for '{wait_selector}' on {url}")

    def _wait_for_cloudflare(self, max_wait: int = 15):
        """Wait for Cloudflare challenge to resolve (if any).
        
        undetected-chromedriver usually passes Cloudflare automatically,
        but sometimes the Turnstile challenge needs a few seconds.
        """
        log.info("  🛡️ Checking for Cloudflare challenge …")
        start = time.time()
        while time.time() - start < max_wait:
            title = self.driver.title.lower()
            page_src = self.driver.page_source[:2000].lower()

            # If we see signs of Cloudflare challenge page, keep waiting
            if "just a moment" in title or "challenge" in title or "cloudflare" in page_src[:500]:
                time.sleep(2)
                continue
            else:
                log.info("  🛡️ Cloudflare check passed ✓")
                return True

        log.warning("  ⚠ Cloudflare challenge may not have resolved in time")
        return False

    # ── Debug helpers ─────────────────────────

    def _dump_debug_html(self, keyword: str, page: int):
        """Save the raw page HTML for debugging when no jobs are found."""
        debug_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "debug")
        os.makedirs(debug_dir, exist_ok=True)

        safe_kw = re.sub(r'[^\w\-]', '_', keyword)
        filename = f"debug_{safe_kw}_p{page}_{datetime.now().strftime('%H%M%S')}.html"
        filepath = os.path.join(debug_dir, filename)

        try:
            html = self.driver.page_source
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(html)
            log.info(f"  📋 Debug HTML saved → {filepath}")
        except Exception as e:
            log.warning(f"  ⚠ Could not save debug HTML: {e}")

    # ── Parsing ───────────────────────────────

    def _parse_job_cards(self, html: str) -> list[dict]:
        """Extract job data from the search results page HTML."""
        soup = BeautifulSoup(html, "lxml")
        jobs = []

        # Upwork uses various selectors for job tiles — try them all
        card_selectors = [
            "article.job-tile",
            "[data-test='job-tile-list'] > div",
            "[data-test='JobTile']",
            "section.air3-card-section",
            "div.job-tile",
            ".up-card-section",
            # Newer Upwork markup patterns
            "[data-ev-label='search_results_impression']",
            "[data-test='UpCRelativeTime']",  # time elements inside job cards
            "article[data-ev-label]",
            "div[data-test='slider-content'] > div",
            ".job-tile-list > div",
        ]

        cards = []
        for sel in card_selectors:
            cards = soup.select(sel)
            if cards:
                log.info(f"  Found {len(cards)} job cards with selector: {sel}")
                break

        if not cards:
            # Fallback 1: find any <a> tags linking to /jobs/~
            all_links = soup.find_all("a", href=re.compile(r"/jobs/~"))
            if all_links:
                log.info(
                    f"  Fallback: found {len(all_links)} job links via href pattern"
                )
                seen_parents = set()
                for link in all_links:
                    # Walk up to find the containing card-like element
                    parent = link.find_parent(
                        ["article", "section", "div"],
                    )
                    if parent and id(parent) not in seen_parents:
                        seen_parents.add(id(parent))
                        cards.append(parent)

        if not cards:
            # Fallback 2: look for any h2/h3/h4 that contain job-like links
            headings_with_links = soup.select("h2 a[href*='/jobs/'], h3 a[href*='/jobs/'], h4 a[href*='/jobs/']")
            if headings_with_links:
                log.info(f"  Fallback 2: found {len(headings_with_links)} heading links to jobs")
                seen_parents = set()
                for link in headings_with_links:
                    # Go up a few levels to find the card container
                    parent = link
                    for _ in range(5):
                        if parent.parent:
                            parent = parent.parent
                        if parent.name in ("article", "section") or (
                            parent.get("class") and any("card" in c.lower() or "tile" in c.lower() for c in parent.get("class", []))
                        ):
                            break
                    if id(parent) not in seen_parents:
                        seen_parents.add(id(parent))
                        cards.append(parent)

        for card in cards:
            job = self._parse_single_card(card)
            if job and job.get("title"):
                jobs.append(job)

        return jobs

    def _parse_single_card(self, card) -> dict:
        """Parse a single job card element into a dict."""
        job: dict = {}

        # ── Title ──
        title_el = (
            card.select_one("a.job-title-link")
            or card.select_one("[data-test='job-tile-title-link'] a")
            or card.select_one("a[href*='/jobs/~']")
            or card.select_one("h2 a")
            or card.select_one("h3 a")
        )
        if title_el:
            job["title"] = title_el.get_text(strip=True)
            href = title_el.get("href", "")
            if href.startswith("/"):
                href = self.BASE_URL + href
            job["url"] = href
        else:
            job["title"] = ""
            job["url"] = ""

        # ── Description ──
        desc_el = (
            card.select_one("[data-test='UpCLineClamp JobDescription'] span")
            or card.select_one("[data-test='job-description-text']")
            or card.select_one(".job-description")
            or card.select_one("[data-test='UpCLineClamp'] span")
            or card.select_one("p")
        )
        job["description"] = desc_el.get_text(strip=True) if desc_el else ""

        # ── Job type & budget ──
        budget_el = (
            card.select_one("[data-test='job-type-label']")
            or card.select_one("[data-test='is-fixed-price']")
            or card.select_one(".js-type")
        )
        job["job_type"] = budget_el.get_text(strip=True) if budget_el else ""

        budget_amount = (
            card.select_one("[data-test='budget']")
            or card.select_one("[data-test='hourly-rate']")
            or card.select_one(".js-budget")
        )
        job["budget"] = budget_amount.get_text(strip=True) if budget_amount else ""

        # Try to find any money-like text if budget not found
        if not job["budget"]:
            money_pattern = re.compile(r"\$[\d,]+(?:\.\d+)?(?:\s*[-–]\s*\$[\d,]+(?:\.\d+)?)?")
            text = card.get_text()
            match = money_pattern.search(text)
            if match:
                job["budget"] = match.group(0).strip()

        # ── Skills / Tags ──
        skill_els = card.select(
            "[data-test='token'] span, "
            "[data-test='attr-item'] span, "
            ".up-skill-badge, "
            ".air3-token, "
            "a[data-test='attr-item']"
        )
        job["skills"] = list(
            {el.get_text(strip=True) for el in skill_els if el.get_text(strip=True)}
        )

        # ── Posted date ──
        date_el = (
            card.select_one("[data-test='posted-on']")
            or card.select_one("[data-test='job-pubDate']")
            or card.select_one("[data-test='UpCRelativeTime']")
            or card.select_one("time")
            or card.select_one("small[data-test='posted-on']")
        )
        job["posted"] = date_el.get_text(strip=True) if date_el else ""

        # ── Client info ──
        client_country_el = (
            card.select_one("[data-test='client-country']")
            or card.select_one("[data-test='location']")
            or card.select_one(".client-location")
        )
        job["client_country"] = (
            client_country_el.get_text(strip=True) if client_country_el else ""
        )

        client_spend_el = card.select_one(
            "[data-test='total-spent'], [data-test='client-spendings']"
        )
        job["client_total_spent"] = (
            client_spend_el.get_text(strip=True) if client_spend_el else ""
        )

        client_rating_el = card.select_one(
            "[data-test='client-rating'] .up-rating-stars, "
            "[data-test='client-rating']"
        )
        job["client_rating"] = (
            client_rating_el.get_text(strip=True) if client_rating_el else ""
        )

        # ── Experience level ──
        exp_el = card.select_one(
            "[data-test='experience-level'], "
            "[data-test='contractor-tier']"
        )
        job["experience_level"] = exp_el.get_text(strip=True) if exp_el else ""

        # ── Proposals ──
        proposals_el = card.select_one(
            "[data-test='proposals'], "
            "[data-test='proposals-tier']"
        )
        job["proposals"] = proposals_el.get_text(strip=True) if proposals_el else ""

        # Timestamp
        job["scraped_at"] = datetime.now().isoformat()

        return job

    # ── Main scraping flow ────────────────────

    def scrape_keyword(self, keyword: str, max_pages: int = 3):
        """Scrape all pages for a given keyword."""
        log.info(f'🔍 Searching for: "{keyword}"')

        for page in range(1, max_pages + 1):
            url = self.SEARCH_URL.format(query=quote_plus(keyword), page=page)
            log.info(f"  📄 Page {page}/{max_pages}  →  {url}")

            self._load_page(url, wait_selector="body", timeout=30)

            # On the first request, wait for Cloudflare to clear
            if page == 1:
                self._wait_for_cloudflare(max_wait=15)

            self._delay("page load cooldown", min_s=5, max_s=10)

            # Scroll down to trigger lazy-loaded content
            self._scroll_page()

            html = self.driver.page_source
            page_jobs = self._parse_job_cards(html)

            if not page_jobs:
                log.info("  ⛔ No jobs found on this page — stopping pagination.")
                # Dump HTML for debugging
                self._dump_debug_html(keyword, page)
                break

            # Tag each job with the search keyword
            for j in page_jobs:
                j["search_keyword"] = keyword

            self.jobs.extend(page_jobs)
            log.info(f"  ✅ Scraped {len(page_jobs)} jobs (total so far: {len(self.jobs)})")

            if page < max_pages:
                self._delay("between pages")

    def _scroll_page(self):
        """Scroll down in steps to trigger lazy loading."""
        try:
            total_height = self.driver.execute_script("return document.body.scrollHeight")
            step = total_height // 4
            for i in range(1, 5):
                self.driver.execute_script(f"window.scrollTo(0, {step * i});")
                time.sleep(0.5)
            # Scroll back up slightly to ensure top content is rendered
            self.driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(0.5)
        except Exception:
            pass

    def scrape_all(self, keywords: list[str], max_pages: int = 3):
        """Scrape multiple keywords."""
        log.info(f"Starting scrape — {len(keywords)} keywords, up to {max_pages} pages each\n")

        # Visit the main page first to establish a session / pass initial Cloudflare
        log.info("Visiting Upwork homepage to establish session …")
        self._load_page(self.BASE_URL, wait_selector="body", timeout=30)
        self._wait_for_cloudflare(max_wait=20)
        self._delay("initial session setup", min_s=5, max_s=8)

        for i, kw in enumerate(keywords, 1):
            log.info(f"━━━ Keyword {i}/{len(keywords)} ━━━")
            self.scrape_keyword(kw, max_pages)
            if i < len(keywords):
                self._delay("between keywords")

        self._deduplicate()
        log.info(f"\n🏁 Done! Total unique jobs collected: {len(self.jobs)}")

    def _deduplicate(self):
        """Remove duplicate jobs by URL."""
        seen = set()
        unique = []
        for job in self.jobs:
            key = job.get("url", "")
            if key and key not in seen:
                seen.add(key)
                unique.append(job)
            elif not key:
                unique.append(job)
        removed = len(self.jobs) - len(unique)
        self.jobs = unique
        if removed:
            log.info(f"  🗑️ Removed {removed} duplicate jobs")

    # ── Export ─────────────────────────────────

    def export_csv(self, filepath: str):
        """Export jobs to CSV."""
        if not self.jobs:
            log.warning("No jobs to export.")
            return

        fieldnames = [
            "title",
            "url",
            "description",
            "job_type",
            "budget",
            "experience_level",
            "skills",
            "posted",
            "proposals",
            "client_country",
            "client_total_spent",
            "client_rating",
            "search_keyword",
            "scraped_at",
        ]

        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            for job in self.jobs:
                row = dict(job)
                # Convert skills list to semicolon-separated string
                if isinstance(row.get("skills"), list):
                    row["skills"] = "; ".join(row["skills"])
                writer.writerow(row)

        log.info(f"📁 CSV saved  → {os.path.abspath(filepath)}")

    def export_json(self, filepath: str):
        """Export jobs to JSON."""
        if not self.jobs:
            log.warning("No jobs to export.")
            return

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(self.jobs, f, indent=2, ensure_ascii=False)

        log.info(f"📁 JSON saved → {os.path.abspath(filepath)}")

    def print_summary(self):
        """Print a quick summary table to the console."""
        if not self.jobs:
            print("\nNo jobs were scraped.")
            return

        print(f"\n{'='*80}")
        print(f" SCRAPE SUMMARY — {len(self.jobs)} unique jobs")
        print(f"{'='*80}")

        # Count by keyword
        keyword_counts: dict[str, int] = {}
        for job in self.jobs:
            kw = job.get("search_keyword", "unknown")
            keyword_counts[kw] = keyword_counts.get(kw, 0) + 1

        print(f"\n{'Keyword':<30} {'Count':>6}")
        print(f"{'-'*30} {'-'*6}")
        for kw, count in sorted(keyword_counts.items(), key=lambda x: -x[1]):
            print(f"{kw:<30} {count:>6}")

        print(f"\nSample jobs:")
        for job in self.jobs[:5]:
            title = job.get("title", "N/A")[:60]
            budget = job.get("budget", "N/A")
            print(f"  • {title:<60}  {budget}")

        print()


# ──────────────────────────────────────────────
# CLI
# ──────────────────────────────────────────────


def parse_args():
    parser = argparse.ArgumentParser(
        description="Scrape Upwork for data-related job postings."
    )
    parser.add_argument(
        "--keywords",
        nargs="+",
        default=None,
        help="Search keywords (default: built-in data job keywords)",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=3,
        help="Max pages to scrape per keyword (default: 3)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="data_jobs",
        help="Output filename without extension (default: data_jobs)",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run browser in headless mode (less reliable with Cloudflare)",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    keywords = args.keywords if args.keywords else DEFAULT_KEYWORDS
    csv_path = f"{args.output}.csv"
    json_path = f"{args.output}.json"

    # Default to visible mode (more reliable with Cloudflare)
    scraper = UpworkScraper(headless=args.headless)

    try:
        scraper.start()
        scraper.scrape_all(keywords, max_pages=args.max_pages)
        scraper.export_csv(csv_path)
        scraper.export_json(json_path)
        scraper.print_summary()
    except KeyboardInterrupt:
        log.info("\n⚠ Interrupted by user — saving partial results …")
        scraper.export_csv(csv_path)
        scraper.export_json(json_path)
        scraper.print_summary()
    except Exception as e:
        log.error(f"Fatal error: {e}", exc_info=True)
        if scraper.jobs:
            log.info("Saving partial results …")
            scraper.export_csv(csv_path)
            scraper.export_json(json_path)
    finally:
        scraper.stop()


if __name__ == "__main__":
    main()
