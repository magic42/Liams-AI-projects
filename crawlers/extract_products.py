"""
Quick script to fetch each category URL and extract product links from the page HTML.
Uses requests + BeautifulSoup to parse without needing a full browser.
"""
import requests
from bs4 import BeautifulSoup
import time
import sys

DOMAIN = "https://www.argocityltd.com"
SEED_FILE = "scraped-sites/argocityltd-com/seed-urls.txt"
OUTPUT_FILE = "scraped-sites/argocityltd-com/product-urls.txt"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def extract_products_from_category(url, session):
    """Fetch a category page and extract product links."""
    try:
        resp = session.get(url, headers=HEADERS, timeout=15)
        if resp.status_code != 200:
            return [], resp.status_code
        soup = BeautifulSoup(resp.text, "html.parser")
        products = set()
        for a in soup.select("a.product-item-link"):
            href = a.get("href", "")
            if href and "argocityltd.com" in href and "#" not in href:
                products.add(href.strip())
        return list(products), 200
    except Exception as e:
        return [], str(e)

def main():
    # Read category URLs
    with open(SEED_FILE) as f:
        category_urls = [line.strip() for line in f if line.strip()]

    print(f"Loaded {len(category_urls)} category URLs")

    all_products = set()
    session = requests.Session()

    working_categories = 0
    error_categories = 0
    categories_with_products = 0

    for i, url in enumerate(category_urls):
        products, status = extract_products_from_category(url, session)
        if status == 200:
            working_categories += 1
            if products:
                categories_with_products += 1
                new_products = [p for p in products if p not in all_products]
                all_products.update(products)
                if new_products:
                    print(f"  [{i+1}/{len(category_urls)}] {url} -> {len(products)} products ({len(new_products)} new)")
                else:
                    print(f"  [{i+1}/{len(category_urls)}] {url} -> {len(products)} products (all duplicates)")
            else:
                print(f"  [{i+1}/{len(category_urls)}] {url} -> 0 products")
        else:
            error_categories += 1
            print(f"  [{i+1}/{len(category_urls)}] {url} -> ERROR {status}")

        # Small delay to be polite
        time.sleep(0.3)

    # Write product URLs
    with open(OUTPUT_FILE, "w") as f:
        for url in sorted(all_products):
            f.write(url + "\n")

    print(f"\n{'='*60}")
    print(f"PRODUCT EXTRACTION COMPLETE")
    print(f"{'='*60}")
    print(f"Category URLs processed: {len(category_urls)}")
    print(f"Working categories:      {working_categories}")
    print(f"Error categories:        {error_categories}")
    print(f"Categories with products:{categories_with_products}")
    print(f"Unique products found:   {len(all_products)}")
    print(f"Output: {OUTPUT_FILE}")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
