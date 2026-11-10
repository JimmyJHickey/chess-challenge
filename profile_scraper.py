"""
Lichess Scraper
Saves current elo into CSV.
Intended to be run on a schedule via cron job.
"""

import csv
import logging
import os
import time
import requests
from datetime import datetime
from bs4 import BeautifulSoup

class ProfileScraper():
    def __init__(self, profile_url: str, user_name: str, csv_path: str):
        self.profile_url = profile_url
        self.user_name = user_name
        self.csv_path = csv_path
        
        self.csv_fields = [
            "user_name", "elo", "scraped_at"
        ]

        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s [%(levelname)s] %(message)s",
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler("scraper.log"),
            ],
        )
        self.log = logging.getLogger(__name__)


    def append_data(self, new_data):
        """Append new elo to the CSV, creating it with a header if needed."""
        write_header = not os.path.exists(self.csv_path)
        with open(self.csv_path, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=self.csv_fields)
            if write_header:
                writer.writeheader()
            writer.writerow(new_data)


    def get_blitz_rating(self) -> int:
        url = self.profile_url
        headers = {"User-Agent": "my-rating-tracker (contact: you@example.com)"}
        r = requests.get(url, headers=headers, timeout=15)
        r.raise_for_status()
        return r.json()["perfs"]["blitz"]["rating"]


    # ---------------------------------------------------------------------------
    # Run routine
    # ---------------------------------------------------------------------------

    def run(self) -> None:
        self.log.info("Starting data scraping...")

        scraped_data = {
            "user_name":    self.user_name,
            "elo":          self.get_blitz_rating(),
            "scraped_at":   datetime.utcnow().isoformat(),
        }

        self.append_data(scraped_data)
        return 1
