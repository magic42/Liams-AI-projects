#!/usr/bin/env python3
"""
eBay Store Scraper → Shopify Product Import CSV

Uses Playwright (headless browser) to scrape an eBay store, extract product
data including compatibility information (car make/year), and generate a
Shopify-ready CSV with metafield columns.

Usage:
    source ~/.scrapy-crawler-venv/bin/activate

    # Full scrape
    python ebay_store_scraper.py --store argocityltd

    # Test with 20 products
    python ebay_store_scraper.py --store argocityltd --max-products 20

    # Resume from saved product URLs
    python ebay_store_scraper.py --store argocityltd --resume

    # Skip compatibility (faster)
    python ebay_store_scraper.py --store argocityltd --skip-compat

    # Full compat extraction (click through ALL pagination pages - slow)
    python ebay_store_scraper.py --store argocityltd --full-compat
"""

import argparse
import csv
import json
import re
import sys
import time
from datetime import datetime
from pathlib import Path

from playwright.sync_api import sync_playwright
from playwright_stealth import Stealth


# =============================================================================
# CONSTANTS
# =============================================================================

EBAY_BASE = "https://www.ebay.co.uk"
ITEMS_PER_PAGE = 72
DELAY_BETWEEN_PAGES = 3.0
DELAY_BETWEEN_PRODUCTS = 3.0

# JavaScript: extract product data from JSON-LD + page
JS_EXTRACT_PRODUCT = """() => {
    const result = {
        title: '', price: '', currency: 'GBP', images: [],
        condition: '', brand: '', item_specifics: {}, description_html: '',
    };

    // JSON-LD
    const ldScripts = document.querySelectorAll('script[type="application/ld+json"]');
    for (const script of ldScripts) {
        try {
            let data = JSON.parse(script.textContent);
            if (Array.isArray(data)) data = data.find(d => d['@type'] === 'Product') || data[0];
            if (data && data['@type'] === 'Product') {
                result.title = data.name || '';
                result.images = Array.isArray(data.image) ? data.image : (data.image ? [data.image] : []);
                if (data.brand) result.brand = typeof data.brand === 'object' ? (data.brand.name || '') : String(data.brand);
                let offers = data.offers || {};
                if (Array.isArray(offers)) offers = offers[0] || {};
                result.price = String(offers.price || '');
                result.currency = offers.priceCurrency || 'GBP';
                const cond = offers.itemCondition || '';
                result.condition = cond.replace('https://schema.org/', '').replace('http://schema.org/', '');
                break;
            }
            if (data && data['@graph']) {
                const product = data['@graph'].find(g => g['@type'] === 'Product');
                if (product) {
                    result.title = product.name || '';
                    result.images = Array.isArray(product.image) ? product.image : (product.image ? [product.image] : []);
                    if (product.brand) result.brand = typeof product.brand === 'object' ? (product.brand.name || '') : String(product.brand);
                    let offers = product.offers || {};
                    if (Array.isArray(offers)) offers = offers[0] || {};
                    result.price = String(offers.price || '');
                    result.currency = offers.priceCurrency || 'GBP';
                    break;
                }
            }
        } catch(e) {}
    }

    // Fallback title
    if (!result.title) { const h1 = document.querySelector('h1'); if (h1) result.title = h1.textContent.trim(); }

    // Item specifics
    const rows = document.querySelectorAll('.ux-labels-values');
    rows.forEach(row => {
        const labelEl = row.querySelector('.ux-labels-values__labels');
        const valueEl = row.querySelector('.ux-labels-values__values');
        if (labelEl && valueEl) {
            const key = labelEl.textContent.trim().replace(/:$/, '');
            const val = valueEl.textContent.trim();
            if (key && val && key.length < 80) result.item_specifics[key] = val;
        }
    });
    if (!result.brand) result.brand = result.item_specifics['Brand'] || '';

    return result;
}"""

# JavaScript: extract compatibility table from current page view
JS_EXTRACT_COMPAT = """() => {
    const result = { exists: false, makes: [], years: [], totalPages: 0, hasTable: false };

    const wrapper = document.getElementById("d-motors-compatibility-table");
    if (!wrapper) return result;
    result.exists = true;

    // Count pagination buttons to get total pages
    const pagBtns = wrapper.querySelectorAll("button.pagination__item");
    if (pagBtns.length > 0) {
        const lastBtn = pagBtns[pagBtns.length - 1];
        result.totalPages = parseInt(lastBtn.textContent.trim()) || pagBtns.length;
    }

    const table = wrapper.querySelector("table");
    if (!table) return result;
    result.hasTable = true;

    // Get header indices
    const headers = [];
    table.querySelectorAll("thead th, thead td").forEach(th => headers.push(th.textContent.trim().toLowerCase()));
    const makeIdx = headers.indexOf("make");
    const yearIdx = headers.indexOf("year");

    // Parse rows
    const tbody = table.querySelector("tbody") || table;
    tbody.querySelectorAll("tr").forEach(tr => {
        const cells = tr.querySelectorAll("td");
        if (makeIdx >= 0 && makeIdx < cells.length) {
            const t = cells[makeIdx].textContent.trim();
            if (t && t.toLowerCase() !== "make") result.makes.push(t);
        }
        if (yearIdx >= 0 && yearIdx < cells.length) {
            const t = cells[yearIdx].textContent.trim();
            if (t && t.toLowerCase() !== "year") result.years.push(t);
        }
    });

    return result;
}"""


# =============================================================================
# PHASE 1: COLLECT PRODUCT URLs FROM STORE
# =============================================================================


def collect_product_urls(page, store_name):
    """Navigate through the eBay store pages and collect all item IDs."""
    all_item_ids = set()
    page_num = 1

    while True:
        url = f"{EBAY_BASE}/str/{store_name}?_pgn={page_num}&_ipg={ITEMS_PER_PAGE}"
        print(f"  [Page {page_num}] {url}", flush=True)

        page.goto(url, wait_until="load", timeout=30000)
        page.wait_for_timeout(3000)

        item_ids = page.evaluate("""() => {
            const ids = new Set();
            document.querySelectorAll('a[href]').forEach(a => {
                const m = a.href.match(/\\/itm\\/(\\d{9,15})/);
                if (m) ids.add(m[1]);
            });
            return [...ids];
        }""")

        if not item_ids:
            print(f"  [Page {page_num}] No items - end of store", flush=True)
            break

        new_ids = set(item_ids) - all_item_ids
        all_item_ids.update(item_ids)
        print(f"  [Page {page_num}] {len(item_ids)} items ({len(new_ids)} new, {len(all_item_ids)} total)", flush=True)

        if len(new_ids) == 0:
            break

        page_num += 1
        time.sleep(DELAY_BETWEEN_PAGES)

    return sorted(all_item_ids)


# =============================================================================
# PHASE 2 & 3: SCRAPE PRODUCT + COMPATIBILITY
# =============================================================================


def _expand_year(year_text):
    """Expand year ranges like '2009-2015' into individual years."""
    year_text = year_text.strip()
    match = re.match(r"(\d{4})\s*[-\u2013]\s*(\d{4})", year_text)
    if match:
        return [str(yr) for yr in range(int(match.group(1)), int(match.group(2)) + 1)]
    elif re.match(r"\d{4}", year_text):
        return [year_text[:4]]
    return [year_text] if year_text else []


def scrape_product(page, item_id, skip_compat=False, full_compat=False):
    """Scrape a single eBay product page."""
    url = f"{EBAY_BASE}/itm/{item_id}"

    try:
        page.goto(url, wait_until="load", timeout=30000)
        page.wait_for_timeout(4000)
    except Exception as e:
        return {"error": str(e), "item_id": item_id, "url": url}

    # Check for security/captcha page
    if "security" in page.title().lower():
        page.wait_for_timeout(5000)
        if "security" in page.title().lower():
            return {"error": "Security/CAPTCHA page", "item_id": item_id, "url": url}

    # Extract product data
    product_data = page.evaluate(JS_EXTRACT_PRODUCT)

    product = {
        "item_id": item_id,
        "url": url,
        **product_data,
        "mpn": product_data.get("item_specifics", {}).get("Manufacturer Part Number", ""),
        "compatibility_makes": [],
        "compatibility_years": [],
    }

    # Compatibility
    if not skip_compat:
        makes, years = extract_compatibility(page, full_compat)
        product["compatibility_makes"] = sorted(set(makes))
        product["compatibility_years"] = sorted(set(years))

    return product


def extract_compatibility(page, full_compat=False):
    """Extract compatibility makes/years from current product page."""
    all_makes = []
    all_years = []

    # Extract first page of compat data
    compat = page.evaluate(JS_EXTRACT_COMPAT)

    if not compat["exists"] or not compat["hasTable"]:
        return all_makes, all_years

    total_pages = compat["totalPages"]
    print(f"    Compat: {total_pages} pages, {len(compat['makes'])} rows on page 1", flush=True)

    # Process page 1
    all_makes.extend(compat["makes"])
    for yr in compat["years"]:
        all_years.extend(_expand_year(yr))

    # For full compat: click through remaining pages
    if full_compat and total_pages > 1:
        for pg in range(2, total_pages + 1):
            try:
                # Click the page button
                btn = page.locator(f"#d-motors-compatibility-table button.pagination__item:text-is('{pg}')")
                if btn.is_visible(timeout=2000):
                    btn.click()
                    page.wait_for_timeout(1500)

                    page_compat = page.evaluate(JS_EXTRACT_COMPAT)
                    if not page_compat["makes"]:
                        break

                    all_makes.extend(page_compat["makes"])
                    for yr in page_compat["years"]:
                        all_years.extend(_expand_year(yr))

                    if pg % 20 == 0:
                        print(f"    Compat page {pg}/{total_pages} - {len(set(all_makes))} makes, {len(set(all_years))} years", flush=True)
                else:
                    break
            except Exception as e:
                print(f"    Compat page {pg} error: {e}", flush=True)
                break
    elif total_pages > 1:
        print(f"    (Sampled page 1 only — use --full-compat for all {total_pages} pages)", flush=True)

    um = len(set(all_makes))
    uy = len(set(all_years))
    print(f"    Compat result: {um} unique makes, {uy} unique years", flush=True)
    return all_makes, all_years


# =============================================================================
# PHASE 4: GENERATE SHOPIFY CSV
# =============================================================================


def slugify(text):
    """Convert text to URL-friendly slug."""
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[-\s]+', '-', text)
    return text.strip('-')[:200]


def generate_shopify_csv(products, output_path):
    """Generate a Shopify-ready product import CSV."""
    fieldnames = [
        "Handle", "Title", "Body (HTML)", "Vendor", "Type", "Tags", "Published",
        "Option1 Name", "Option1 Value", "Option2 Name", "Option2 Value",
        "Option3 Name", "Option3 Value",
        "Variant SKU", "Variant Grams", "Variant Inventory Tracker",
        "Variant Inventory Qty", "Variant Inventory Policy",
        "Variant Fulfillment Service", "Variant Price", "Variant Compare At Price",
        "Variant Requires Shipping", "Variant Taxable", "Variant Barcode",
        "Image Src", "Image Position", "Image Alt Text",
        "Gift Card", "SEO Title", "SEO Description",
        "Variant Image", "Variant Weight Unit", "Cost per item", "Status",
        "Metafield: custom.car_make [list.single_line_text_field]",
        "Metafield: custom.car_year [list.single_line_text_field]",
    ]

    total_rows = 0
    valid = 0

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()

        for product in products:
            if product.get("error"):
                continue
            valid += 1

            item_id = product.get("item_id", "")
            title = product.get("title", "")
            handle = slugify(title) if title else f"item-{item_id}"
            handle = f"{handle}-{item_id[-4:]}" if item_id else handle

            specs = product.get("item_specifics", {})
            product_type = specs.get("Type", "") or specs.get("Bulb Type", "")
            tag_fields = ["Brand", "Technology", "Lighting Technology", "Bulb Type",
                          "Light Colour", "Placement on Vehicle", "Voltage"]
            tags = [specs[f] for f in tag_fields if specs.get(f)]

            compat_makes = product.get("compatibility_makes", [])
            compat_years = product.get("compatibility_years", [])
            images = product.get("images", [])

            row = {
                "Handle": handle,
                "Title": title,
                "Body (HTML)": product.get("description_html", ""),
                "Vendor": "Argo City Ltd",
                "Type": product_type,
                "Tags": ", ".join(tags),
                "Published": "TRUE",
                "Option1 Name": "Title",
                "Option1 Value": "Default Title",
                "Variant SKU": item_id,
                "Variant Grams": "0",
                "Variant Inventory Policy": "deny",
                "Variant Fulfillment Service": "manual",
                "Variant Price": product.get("price", ""),
                "Variant Requires Shipping": "TRUE",
                "Variant Taxable": "TRUE",
                "Image Src": images[0] if images else "",
                "Image Position": "1" if images else "",
                "Image Alt Text": title,
                "Status": "active",
                "Metafield: custom.car_make [list.single_line_text_field]": ", ".join(compat_makes),
                "Metafield: custom.car_year [list.single_line_text_field]": ", ".join(compat_years),
            }
            writer.writerow(row)
            total_rows += 1

            for idx, img_url in enumerate(images[1:], start=2):
                writer.writerow({
                    "Handle": handle,
                    "Image Src": img_url,
                    "Image Position": str(idx),
                    "Image Alt Text": title,
                })
                total_rows += 1

    print(f"\nShopify CSV: {output_path}", flush=True)
    print(f"Products: {valid} | CSV rows: {total_rows}", flush=True)


# =============================================================================
# MAIN
# =============================================================================


def main():
    parser = argparse.ArgumentParser(description="eBay store → Shopify CSV with compatibility metafields")
    parser.add_argument("--store", "-s", required=True, help="eBay store name")
    parser.add_argument("--max-products", "-m", type=int, default=0, help="Max products (0=all)")
    parser.add_argument("--resume", "-r", action="store_true", help="Resume from saved item IDs")
    parser.add_argument("--skip-compat", action="store_true", help="Skip compatibility extraction")
    parser.add_argument("--full-compat", action="store_true", help="Click through ALL compat pages (slow)")
    parser.add_argument("--headed", action="store_true", help="Show browser window")
    args = parser.parse_args()

    script_dir = Path(__file__).parent
    output_dir = script_dir / "scraped-sites" / f"ebay-co-uk-str-{args.store}"
    output_dir.mkdir(parents=True, exist_ok=True)

    ids_file = output_dir / "product-item-ids.txt"
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    csv_output = output_dir / f"shopify-product-import-{timestamp}.csv"
    json_output = output_dir / f"products-{timestamp}.json"
    progress_file = output_dir / "scrape-progress.json"

    print("=" * 60, flush=True)
    print("eBay Store → Shopify Product Import", flush=True)
    print("=" * 60, flush=True)
    print(f"Store:       {args.store}", flush=True)
    print(f"Output:      {output_dir}", flush=True)
    if args.max_products: print(f"Max items:   {args.max_products}", flush=True)
    if args.skip_compat: print(f"Compat:      SKIPPED", flush=True)
    if args.full_compat: print(f"Compat:      FULL (all pages)", flush=True)
    print("=" * 60, flush=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=not args.headed,
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox"],
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080},
            locale="en-GB",
        )
        Stealth().apply_stealth_sync(context)
        pg = context.new_page()

        # Warmup: establish eBay session
        print("\nWarming up session...", flush=True)
        pg.goto(EBAY_BASE, wait_until="load", timeout=30000)
        pg.wait_for_timeout(3000)
        try:
            btn = pg.locator("#gdpr-banner-accept")
            if btn.is_visible(timeout=3000):
                btn.click()
                print("Accepted cookies", flush=True)
                pg.wait_for_timeout(2000)
        except Exception:
            pass

        # PHASE 1: Collect item IDs
        if args.resume and ids_file.exists():
            with open(ids_file) as f:
                item_ids = [line.strip() for line in f if line.strip()]
            print(f"\nResumed {len(item_ids)} item IDs from {ids_file}", flush=True)
        else:
            print("\n--- Phase 1: Collecting product URLs ---", flush=True)
            item_ids = collect_product_urls(pg, args.store)
            with open(ids_file, "w") as f:
                for iid in item_ids:
                    f.write(iid + "\n")
            print(f"Saved {len(item_ids)} item IDs", flush=True)

        if args.max_products > 0:
            item_ids = item_ids[:args.max_products]
        print(f"\nProducts to scrape: {len(item_ids)}", flush=True)

        # PHASE 2-3: Scrape each product
        print("\n--- Phase 2-3: Scraping products ---", flush=True)
        products = []
        errors = []
        scraped_ids = set()

        if args.resume and progress_file.exists():
            with open(progress_file) as f:
                progress = json.load(f)
                products = progress.get("products", [])
                errors = progress.get("errors", [])
                scraped_ids = {p.get("item_id") for p in products} | {e.get("item_id") for e in errors}
                print(f"Resuming: {len(products)} done, {len(errors)} errors", flush=True)

        for i, item_id in enumerate(item_ids):
            if item_id in scraped_ids:
                continue

            print(f"\n[{i+1}/{len(item_ids)}] {item_id}...", flush=True)
            product = scrape_product(pg, item_id, skip_compat=args.skip_compat, full_compat=args.full_compat)

            if product.get("error"):
                print(f"  ERROR: {product['error']}", flush=True)
                errors.append(product)
            else:
                cm = len(product.get("compatibility_makes", []))
                cy = len(product.get("compatibility_years", []))
                compat = f" | Compat: {cm} makes, {cy} years" if cm else ""
                print(f"  {product.get('title', '')[:55]}", flush=True)
                print(f"  {product.get('currency','GBP')} {product.get('price','?')} | {len(product.get('images',[]))} imgs{compat}", flush=True)
                products.append(product)

            if (i + 1) % 5 == 0:
                with open(progress_file, "w") as f:
                    json.dump({"products": products, "errors": errors}, f)

            time.sleep(DELAY_BETWEEN_PRODUCTS)

        browser.close()

    # Save JSON
    with open(json_output, "w") as f:
        json.dump(products, f, indent=2)

    # Save final progress
    with open(progress_file, "w") as f:
        json.dump({"products": products, "errors": errors}, f)

    # PHASE 4: Generate CSV
    print("\n--- Phase 4: Generating Shopify CSV ---", flush=True)
    generate_shopify_csv(products, csv_output)

    # Report
    with_compat = len([p for p in products if p.get("compatibility_makes")])
    print(f"\n{'='*60}", flush=True)
    print(f"SCRAPE COMPLETE", flush=True)
    print(f"{'='*60}", flush=True)
    print(f"Products:        {len(products)}", flush=True)
    print(f"With compat:     {with_compat}", flush=True)
    print(f"Errors:          {len(errors)}", flush=True)
    print(f"JSON:            {json_output}", flush=True)
    print(f"Shopify CSV:     {csv_output}", flush=True)
    print(f"{'='*60}", flush=True)

    if errors:
        print("\nErrors:", flush=True)
        for e in errors[:10]:
            print(f"  {e.get('item_id','?')}: {e.get('error','?')}", flush=True)


if __name__ == "__main__":
    main()
