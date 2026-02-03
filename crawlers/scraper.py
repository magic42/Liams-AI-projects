#!/usr/bin/env python3
"""
Universal Website Scraper Agent

A configurable scraper that can be called with simple parameters to crawl
any website and extract images from categories, products, or the entire site.

Usage:
    source ~/.scrapy-crawler-venv/bin/activate

    # Scrape category pages
    python scraper.py --url "www.example.com" --type category

    # Scrape product pages
    python scraper.py --url "www.example.com" --type product

    # Scrape entire site
    python scraper.py --url "www.example.com" --type all

    # With options
    python scraper.py --url "www.example.com" --type category --max-pages 50 --delay 0.5

Output files are named: {domain}-{type}.csv and {domain}-{type}_unique.csv
"""

import argparse
import csv
import json
import re
import sys
from datetime import datetime
from urllib.parse import urljoin, urlparse

from scrapy import Spider, signals
from scrapy.crawler import CrawlerProcess
from scrapy.linkextractors import LinkExtractor
from scrapy.spidermiddlewares.httperror import HttpError
from twisted.internet.error import DNSLookupError, TCPTimedOutError, TimeoutError


# =============================================================================
# SCRAPE TYPE CONFIGURATIONS
# =============================================================================

SCRAPE_CONFIGS = {
    "category": {
        "url_patterns": [
            r'/category/',
            r'/categories/',
            r'/cat/',
            r'/c/',
            r'/collections/',
            r'/shop/',
            r'/browse/',
        ],
        "description": "Category/collection pages",
    },
    "product": {
        "url_patterns": [
            r'/product/',
            r'/products/',
            r'/p/',
            r'/item/',
            r'/items/',
            r'/dp/',  # Amazon style
            r'/pd/',
        ],
        "description": "Product detail pages",
    },
    "blog": {
        "url_patterns": [
            r'/blog/',
            r'/news/',
            r'/articles/',
            r'/posts/',
            r'/journal/',
        ],
        "description": "Blog/news pages",
    },
    "all": {
        "url_patterns": [],  # Empty = follow all internal links
        "description": "Entire website",
    },
}

# Common URL patterns to always exclude
DEFAULT_DENY_PATTERNS = [
    r'/cart/',
    r'/checkout/',
    r'/account/',
    r'/login/',
    r'/register/',
    r'/my-account/',
    r'/admin/',
    r'/wp-admin/',
    r'/wp-login/',
    r'\?add-to-cart=',
    r'\?remove_item=',
    r'/wishlist/',
    r'/compare/',
]

# Image patterns to exclude (icons, placeholders, etc.)
IMAGE_EXCLUDE_PATTERNS = [
    r'placeholder',
    r'loading',
    r'spinner',
    r'icon',
    r'pixel',
    r'tracking',
    r'spacer',
    r'blank',
    r'1x1',
    r'transparent',
    r'/wp-includes/',
    r'/wp-content/plugins/',
    r'gravatar\.com',
]


# =============================================================================
# SPIDER IMPLEMENTATION
# =============================================================================


class ScraperSpider(Spider):
    """Universal scraper spider with configurable URL patterns."""

    name = "scraper"

    def __init__(self, config, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.config = config
        self.results = []
        self.errors = []
        self.pages_crawled = 0
        self.all_images = {}

        # Compile image exclusion patterns
        self.image_exclude_patterns = [
            re.compile(p, re.IGNORECASE) for p in IMAGE_EXCLUDE_PATTERNS
        ]

        # Set up allowed domains
        domain = config["domain"]
        self.allowed_domains = [domain, domain.replace("www.", "")]

        # Set start URLs
        self.start_urls = [f"https://{domain}/"]

        # Configure link extractor based on scrape type
        scrape_type = config["scrape_type"]
        url_patterns = SCRAPE_CONFIGS[scrape_type]["url_patterns"]

        self.link_extractor = LinkExtractor(
            allow_domains=self.allowed_domains,
            allow=url_patterns if url_patterns else (),
            deny=DEFAULT_DENY_PATTERNS,
            deny_extensions=[
                "jpg", "jpeg", "png", "gif", "svg", "webp", "ico", "bmp",
                "pdf", "doc", "docx", "xls", "xlsx", "ppt", "pptx",
                "mp3", "mp4", "avi", "mov", "wmv", "flv",
                "zip", "rar", "tar", "gz", "7z",
                "css", "js", "woff", "woff2", "ttf", "eot",
            ],
        )

    @classmethod
    def create_settings(cls, config):
        """Create Scrapy settings from config."""
        return {
            "DOWNLOAD_DELAY": config.get("delay", 1.0),
            "CONCURRENT_REQUESTS": config.get("concurrent", 2),
            "CONCURRENT_REQUESTS_PER_DOMAIN": config.get("concurrent", 2),
            "ROBOTSTXT_OBEY": True,
            "USER_AGENT": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36 "
                "(Magic42Scraper/1.0)"
            ),
            "LOG_LEVEL": config.get("log_level", "INFO"),
            "DOWNLOAD_TIMEOUT": 30,
            "RETRY_TIMES": 2,
            "RETRY_HTTP_CODES": [500, 502, 503, 504, 408, 429],
            "HTTPERROR_ALLOW_ALL": True,
        }

    def parse(self, response):
        """Parse a page and extract images."""
        max_pages = self.config.get("max_pages", 0)
        if max_pages > 0 and self.pages_crawled >= max_pages:
            self.crawler.engine.close_spider(self, "max_pages_reached")
            return

        if response.status != 200:
            self._handle_http_error(response)
            if response.status >= 400:
                return

        self.pages_crawled += 1

        # Extract page metadata
        page_title = (
            response.xpath("//title/text()").get() or
            response.xpath("//meta[@property='og:title']/@content").get() or
            ""
        ).strip()

        # Extract images
        images = self._extract_images(response)

        if images:
            result = {
                "page_url": response.url,
                "page_title": page_title,
                "image_count": len(images),
                "images": json.dumps(images),
            }
            self.results.append(result)

            # Track unique images
            for img in images:
                img_url = img["src"]
                if img_url not in self.all_images:
                    self.all_images[img_url] = {
                        "src": img_url,
                        "alt": img.get("alt", ""),
                        "found_on": [response.url],
                    }
                else:
                    self.all_images[img_url]["found_on"].append(response.url)

            self.logger.info(
                f"Crawled: {response.url} - Found {len(images)} images"
            )
        else:
            self.logger.info(f"Crawled: {response.url} - No images found")

        # Follow links
        for link in self.link_extractor.extract_links(response):
            if max_pages > 0 and self.pages_crawled >= max_pages:
                break
            yield response.follow(
                link.url,
                callback=self.parse,
                errback=self._handle_error,
            )

    def _extract_images(self, response):
        """Extract and filter images from the page."""
        images = []
        seen_urls = set()
        min_width = self.config.get("min_image_width", 50)
        min_height = self.config.get("min_image_height", 50)

        for img in response.xpath("//img"):
            src = (
                img.xpath("@src").get() or
                img.xpath("@data-src").get() or
                img.xpath("@data-lazy-src").get() or
                img.xpath("@data-original").get() or
                ""
            )

            if not src or src.startswith("data:"):
                continue

            src = urljoin(response.url, src)

            if src in seen_urls:
                continue
            seen_urls.add(src)

            if self._should_exclude_image(src):
                continue

            alt = img.xpath("@alt").get() or ""
            width = img.xpath("@width").get()
            height = img.xpath("@height").get()

            try:
                w = int(width) if width else 0
                h = int(height) if height else 0
                if min_width > 0 and w > 0 and w < min_width:
                    continue
                if min_height > 0 and h > 0 and h < min_height:
                    continue
            except (ValueError, TypeError):
                pass

            images.append({
                "src": src,
                "alt": alt.strip(),
                "width": width,
                "height": height,
            })

        # Check for background images
        for element in response.xpath("//*[@style]"):
            style = element.xpath("@style").get() or ""
            bg_match = re.search(r'url\(["\']?([^"\')\s]+)["\']?\)', style)
            if bg_match:
                src = urljoin(response.url, bg_match.group(1))
                if src not in seen_urls and not self._should_exclude_image(src):
                    seen_urls.add(src)
                    images.append({
                        "src": src,
                        "alt": "(background image)",
                        "width": None,
                        "height": None,
                    })

        return images

    def _should_exclude_image(self, url):
        """Check if image URL matches exclusion patterns."""
        return any(p.search(url) for p in self.image_exclude_patterns)

    def _handle_http_error(self, response):
        """Handle HTTP errors."""
        self.errors.append({
            "url": response.url,
            "status": response.status,
            "error_type": "http_error",
            "timestamp": datetime.now().isoformat(),
        })
        if response.status == 429:
            self.logger.error(f"Rate limited (429): {response.url}")
        elif response.status >= 500:
            self.logger.error(f"Server error ({response.status}): {response.url}")
        else:
            self.logger.warning(f"HTTP error ({response.status}): {response.url}")

    def _handle_error(self, failure):
        """Handle request failures."""
        request = failure.request
        error_info = {
            "url": request.url,
            "error_type": "request_failure",
            "timestamp": datetime.now().isoformat(),
        }

        if failure.check(HttpError):
            response = failure.value.response
            error_info["status"] = response.status
        elif failure.check(DNSLookupError):
            error_info["error_message"] = "DNS lookup failed"
        elif failure.check(TimeoutError, TCPTimedOutError):
            error_info["error_message"] = "Request timed out"
        else:
            error_info["error_message"] = str(failure.value)

        self.errors.append(error_info)
        self.logger.error(f"Error on {request.url}: {error_info}")


# =============================================================================
# OUTPUT HANDLING
# =============================================================================


def generate_output_filename(domain, scrape_type):
    """Generate output filename based on domain and scrape type."""
    # Clean domain for filename
    clean_domain = domain.replace("www.", "").replace(".", "-")
    return f"{clean_domain}-{scrape_type}"


def save_results(spider, output_base):
    """Save crawl results to CSV files."""
    page_file = f"{output_base}.csv"
    unique_file = f"{output_base}_unique.csv"

    # Save page-level results
    if spider.results:
        fieldnames = ["page_url", "page_title", "image_count", "images"]
        with open(page_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(spider.results)

    # Save unique images
    if spider.all_images:
        with open(unique_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f, fieldnames=["src", "alt", "pages_found_on", "page_count"]
            )
            writer.writeheader()
            for img_url, img_data in sorted(spider.all_images.items()):
                writer.writerow({
                    "src": img_url,
                    "alt": img_data["alt"],
                    "pages_found_on": json.dumps(img_data["found_on"]),
                    "page_count": len(img_data["found_on"]),
                })

    # Print summary
    print("\n" + "=" * 60)
    print("SCRAPE COMPLETE")
    print("=" * 60)
    print(f"Domain:            {spider.config['domain']}")
    print(f"Scrape type:       {spider.config['scrape_type']}")
    print(f"Pages crawled:     {spider.pages_crawled}")
    print(f"Pages with images: {len(spider.results)}")
    print(f"Unique images:     {len(spider.all_images)}")
    print(f"Errors:            {len(spider.errors)}")
    print("-" * 60)
    print(f"Output files:")
    print(f"  Page results:    {page_file}")
    print(f"  Unique images:   {unique_file}")
    print("=" * 60)

    if spider.errors:
        print("\nErrors encountered (first 5):")
        for error in spider.errors[:5]:
            print(f"  - {error.get('url', 'Unknown')}: {error.get('status', error.get('error_message', 'Unknown'))}")


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================


def run_scraper(domain, scrape_type, max_pages=0, delay=1.0, concurrent=2):
    """
    Run the scraper with given parameters.

    Args:
        domain: Website domain (e.g., "www.example.com")
        scrape_type: Type of pages to scrape ("category", "product", "blog", "all")
        max_pages: Maximum pages to crawl (0 = unlimited)
        delay: Delay between requests in seconds
        concurrent: Number of concurrent requests

    Returns:
        Tuple of (output_base_filename, pages_crawled, unique_images_count)
    """
    if scrape_type not in SCRAPE_CONFIGS:
        print(f"Error: Invalid scrape type '{scrape_type}'")
        print(f"Valid types: {', '.join(SCRAPE_CONFIGS.keys())}")
        sys.exit(1)

    # Prepare config
    config = {
        "domain": domain,
        "scrape_type": scrape_type,
        "max_pages": max_pages,
        "delay": delay,
        "concurrent": concurrent,
        "min_image_width": 50,
        "min_image_height": 50,
    }

    output_base = generate_output_filename(domain, scrape_type)

    print("=" * 60)
    print("Website Scraper")
    print("=" * 60)
    print(f"Domain:            {domain}")
    print(f"Scrape type:       {scrape_type} ({SCRAPE_CONFIGS[scrape_type]['description']})")
    print(f"Download delay:    {delay}s")
    print(f"Concurrent:        {concurrent}")
    if max_pages > 0:
        print(f"Max pages:         {max_pages}")
    print(f"Output prefix:     {output_base}")
    print("=" * 60 + "\n")

    # Create and run crawler
    process = CrawlerProcess(settings=ScraperSpider.create_settings(config))

    # Create spider instance
    spider = ScraperSpider(config=config)

    # Create crawler
    crawler = process.create_crawler(ScraperSpider)

    # Connect save handler
    def on_spider_closed(spider):
        save_results(spider, output_base)

    crawler.signals.connect(on_spider_closed, signal=signals.spider_closed)

    # Run the crawl
    process.crawl(crawler, config=config)
    process.start()

    return output_base


def main():
    """Parse arguments and run scraper."""
    parser = argparse.ArgumentParser(
        description="Universal Website Scraper - Extract images from websites",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scraper.py --url "www.example.com" --type category
  python scraper.py --url "www.example.com" --type product --max-pages 100
  python scraper.py --url "www.example.com" --type all --delay 0.5

Scrape types:
  category  - Category/collection pages (/category/, /shop/, /collections/)
  product   - Product detail pages (/product/, /p/, /item/)
  blog      - Blog/news pages (/blog/, /news/, /articles/)
  all       - Entire website (follows all internal links)
        """
    )

    parser.add_argument(
        "--url", "-u",
        required=True,
        help="Website domain to scrape (e.g., www.example.com)"
    )
    parser.add_argument(
        "--type", "-t",
        required=True,
        choices=list(SCRAPE_CONFIGS.keys()),
        help="Type of pages to scrape"
    )
    parser.add_argument(
        "--max-pages", "-m",
        type=int,
        default=0,
        help="Maximum pages to crawl (0 = unlimited)"
    )
    parser.add_argument(
        "--delay", "-d",
        type=float,
        default=1.0,
        help="Delay between requests in seconds (default: 1.0)"
    )
    parser.add_argument(
        "--concurrent", "-c",
        type=int,
        default=2,
        help="Number of concurrent requests (default: 2)"
    )

    args = parser.parse_args()

    # Clean up URL (remove protocol if provided)
    domain = args.url.replace("https://", "").replace("http://", "").rstrip("/")

    run_scraper(
        domain=domain,
        scrape_type=args.type,
        max_pages=args.max_pages,
        delay=args.delay,
        concurrent=args.concurrent,
    )


if __name__ == "__main__":
    main()
