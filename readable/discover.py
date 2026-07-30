"""
discover.py - URL Discovery Crawler

Crawls seed URLs to discover new target sites.
"""

import requests
from bs4 import BeautifulSoup
import os
import sys


def fetch_new_urls(seed_url):
    """
    Crawl a seed URL and extract links.

    Filters out common non-target sites (social media, tech companies).

    Args:
        seed_url: URL to crawl

    Returns:
        set: Set of discovered URLs
    """
    print(f"Crawling {seed_url}...")
    try:
        response = requests.get(seed_url, timeout=15)
        soup = BeautifulSoup(response.text, 'html.parser')
        links = soup.find_all('a', href=True)

        found = set()
        for link in links:
            url = link['href']

            # Filter out common non-target sites
            excluded = [
                'facebook', 'twitter', 'instagram',
                'google', 'apple', 'microsoft'
            ]
            if any(site in url for site in excluded):
                continue

            # Only keep absolute URLs of reasonable length
            if url.startswith('http') and len(url) > 15:
                found.add(url.strip())

        return found

    except Exception as e:
        print(f"Discovery error: {e}")
        return set()


def run_discovery(seed_urls):
    """
    Run discovery on multiple seed URLs.

    Compares discovered URLs against existing list and saves new ones.

    Args:
        seed_urls: List of URLs to crawl
    """
    # Load existing URLs
    existing = set()
    if os.path.exists('in/urls.txt'):
        with open('in/urls.txt', 'r') as f:
            existing.update([line.strip() for line in f if line.strip()])

    # Crawl all seed URLs
    discovered = set()
    for seed in seed_urls:
        discovered.update(fetch_new_urls(seed))

    # Find truly new URLs
    new_urls = discovered - existing

    if new_urls:
        os.makedirs('data', exist_ok=True)
        with open('data/staging_urls.txt', 'a') as f:
            for url in new_urls:
                f.write(f"{url}\n")
        print(f"Found {len(new_urls)} new URLs. Saved to data/staging_urls.txt")
    else:
        print("No new URLs found.")


if __name__ == "__main__":
    if "-h" in sys.argv or "--help" in sys.argv:
        print("Usage: python discover.py")
        print()
        print("Crawls seed URLs to find new sites and saves them to data/staging_urls.txt.")
        sys.exit(0)

    # Default seed URLs (placeholders)
    seeds = [
        "https://www.casino.org/",
        "https://www.askgamblers.com/"
    ]
    run_discovery(seeds)
