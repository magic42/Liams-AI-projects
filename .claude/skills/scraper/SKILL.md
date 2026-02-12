---
name: scraper
description: Website scraping skill - extract images, product data, SEO data, and full site audits. Use when the user wants to extract data from a website.
allowed-tools: Bash, mcp__Claude_in_Chrome__tabs_context_mcp, mcp__Claude_in_Chrome__tabs_create_mcp, mcp__Claude_in_Chrome__navigate, mcp__Claude_in_Chrome__read_page, mcp__Claude_in_Chrome__find, mcp__Claude_in_Chrome__computer, mcp__Claude_in_Chrome__javascript_tool, mcp__Claude_in_Chrome__get_page_text
argument-hint: "[start | URL]"
---

# Scraper: Website Data Extraction Skill

Extract images, product data, SEO data, and more from any website. Supports category pages, product pages, full site, or "The Full Monty" audit.

## How to Handle Arguments

- If `$ARGUMENTS` is `start` → Follow the **Guided User Journey** below
- If `$ARGUMENTS` is a URL → Skip to Step 2 with that URL
- If `$ARGUMENTS` is empty → Follow the **Guided User Journey** below

---

## Guided User Journey

### Step 1: Ask for URL

Prompt the user:

```
**Website Image Scraper**

Please enter the URL of the website you'd like to scrape:

Example: `www.example.com` or `https://example.com`
```

Wait for the user to provide a URL. Clean it up (remove http/https, trailing slashes).

### Step 2: Run Connection Test

Run the dual test scrape (5 category + 5 product pages) to verify connectivity and discover what's available.

```bash
source ~/.scrapy-crawler-venv/bin/activate
cd /Users/liam.miner/Documents/Liams-AI-projects/crawlers

# Test category pages (5 pages)
python scraper.py --url "DOMAIN" --type category --max-pages 5 2>&1

# Test product pages (5 pages)
python scraper.py --url "DOMAIN" --type product --max-pages 5 2>&1
```

**IMPORTANT:**
- Use a 2-minute timeout per test
- If a test takes longer, ask the user if they want to wait or cancel

Present results:

```
**Connection Test Results for {domain}**

### Category Pages (5 tested)
| Page | Images Found |
|------|--------------|
| /category/example-1/ | X images |
| ... | ... |

### Product Pages (5 tested)
| Page | Images Found |
|------|--------------|
| /product/example-1/ | X images |
| ... | ... |

**Summary:**
- Category pages: X total images from Y pages
- Product pages: X total images from Y pages
- Errors: X
```

If **both tests fail**, explain the issue and offer troubleshooting options. Do not proceed.

If **at least one test succeeds**, proceed to Step 3.

**If the crawler only found the homepage** (no category or product pages discovered), this likely means the site renders its navigation via JavaScript. Proceed to **Step 2b: Browser Navigation Fallback** before continuing.

### Step 2b: Browser Navigation Fallback (JS-rendered sites)

When the connection test only finds the homepage (0 category pages and 0 product pages beyond the homepage), use Chrome browser automation to extract navigation URLs.

**Tell the user:**
```
The crawler couldn't find internal pages — this site likely loads navigation via JavaScript.
I'll open the site in Chrome to extract the navigation links.
```

**Procedure:**

1. Get browser context and create a new tab:
   - Use `tabs_context_mcp` to get available tabs
   - Use `tabs_create_mcp` to create a fresh tab

2. Navigate to the site:
   - Use `navigate` to go to `https://DOMAIN/`
   - Wait for the page to load

3. Extract all navigation links from the header/main menu:
   - Use `javascript_tool` to extract all `<a>` href values from the site's main navigation (`<nav>`, `<header>`, or common menu selectors). Example JS:
     ```javascript
     (() => {
       const links = new Set();
       // Try common nav selectors
       const selectors = [
         'nav a[href]',
         'header a[href]',
         '.nav a[href]',
         '.menu a[href]',
         '.navigation a[href]',
         '#nav a[href]',
         '#menu a[href]',
         '.main-menu a[href]',
         '.mega-menu a[href]',
         '.nav-sections a[href]',
         '.level0 a[href]'
       ];
       for (const selector of selectors) {
         document.querySelectorAll(selector).forEach(a => {
           const href = a.href;
           if (href && href.startsWith('http') && !href.includes('#') && !href.includes('javascript:')) {
             links.add(href);
           }
         });
       }
       return [...links].sort();
     })()
     ```
   - If the above returns no results, try `read_page` with `filter: "interactive"` to find navigation links, or use `find` to locate menu elements

4. If the site uses hover/mega-menus that need interaction to reveal sub-links:
   - Use `computer` with `action: "hover"` over top-level menu items to expand dropdowns
   - Then re-extract links after each hover
   - Focus on category and product listing links

5. Filter the extracted URLs:
   - Keep only URLs belonging to the same domain
   - Remove duplicates, anchors, query strings for login/account pages
   - Remove obvious non-content URLs (login, cart, account, checkout, contact, etc.)

6. Save the URLs to a seed file:
   ```bash
   # Save extracted URLs to a seed file (one per line)
   cat > "scraped-sites/{clean-domain}/seed-urls.txt" << 'URLS'
   https://domain.com/category-1/
   https://domain.com/category-2/
   https://domain.com/product-1/
   ...
   URLS
   ```

7. Present the discovered URLs to the user:
   ```
   **Browser Navigation Discovery for {domain}**

   I found {X} navigation links by rendering the site in Chrome:

   **Category-like URLs ({Y}):**
   - /shop/category-1/
   - /shop/category-2/
   ...

   **Product-like URLs ({Z}):**
   - /product/item-1/
   - /product/item-2/
   ...

   **Other URLs ({W}):**
   - /about/
   - /blog/
   ...

   These will be used as seed URLs for the scraper.
   ```

8. Proceed to Step 3 as normal. When running the scrape in Step 5, include the `--urls` flag:
   ```bash
   python scraper.py --url "DOMAIN" --type TYPE --urls "scraped-sites/{clean-domain}/seed-urls.txt"
   ```

### Step 3: Ask Target Area

Ask the user what they want to scrape:

```
**What would you like to scrape?**

1. **Categories only** - Category/collection pages (images only)
2. **Products only** - Product detail pages (images only)
3. **Full site** - All pages (images only)
4. **The Full Monty** - Categories + Products with FULL data extraction:
   - All images
   - Product data (name, price, SKU, brand, availability)
   - SEO data (meta title, meta description, H1, canonical URL)
   - Content metrics (word count, image count, link counts)
   - Schema.org structured data analysis
   - Sitemap (auto-included)
   - Output as formatted Excel workbook (.xlsx) with separate sheets

Which option: 1, 2, 3, or 4?
```

**IMPORTANT:**
- If user selects **Categories only** or **Products only**, the scraper must EXCLUDE:
  - Homepage images
  - CMS/content pages (about, contact, terms, etc.)
  - Only scrape pages matching the specific URL patterns for that type
- If user selects **The Full Monty**, skip Step 4 (sitemap is auto-included) and go straight to Step 5

### Step 4: Ask About Sitemap

**If the user selected "The Full Monty" (option 4), SKIP this step entirely.** The sitemap is automatically included with The Full Monty. Proceed directly to Step 5.

For all other options, ask the user:

```
**Would you like me to also scrape the sitemap?**

This will extract all URLs from the website's sitemap.xml and save them to a separate file.

Yes or No?
```

If **Yes**, download and format the sitemap:

```bash
# Download the raw sitemap
curl -s "https://DOMAIN/sitemap.xml" -o "OUTPUT_FOLDER/sitemap-raw.xml"

# Format it with proper line breaks (one element per line)
xmllint --format "OUTPUT_FOLDER/sitemap-raw.xml" > "OUTPUT_FOLDER/sitemap.xml" 2>/dev/null || cat "OUTPUT_FOLDER/sitemap-raw.xml" | sed 's/></>\n</g' > "OUTPUT_FOLDER/sitemap.xml"

# Also extract just the URLs to a plain text file (one URL per line)
cat "OUTPUT_FOLDER/sitemap.xml" | tr '>' '\n' | grep -o 'https://[^<]*' > "OUTPUT_FOLDER/sitemap-urls.txt"

# Remove the raw file
rm "OUTPUT_FOLDER/sitemap-raw.xml" 2>/dev/null
```

If the sitemap is an index pointing to other sitemaps, fetch those too and format them the same way.

### Step 5: Create Output Folder & Run Full Scrape

**Create the domain's output folder:**

```bash
mkdir -p /Users/liam.miner/Documents/Liams-AI-projects/crawlers/scraped-sites/{clean-domain}
```

Where `{clean-domain}` is the domain with dots replaced by hyphens (e.g., `www-example-com` or `example-com`).

**If The Full Monty was selected (option 4):**

```bash
source ~/.scrapy-crawler-venv/bin/activate
cd /Users/liam.miner/Documents/Liams-AI-projects/crawlers

# Run the Full Monty scrape (outputs .xlsx automatically)
# If seed URLs were discovered in Step 2b, include --urls flag
python scraper.py --url "DOMAIN" --type fullmonty [--urls "scraped-sites/{clean-domain}/seed-urls.txt"]

# Fetch the sitemap (auto-included with Full Monty)
curl -s "https://DOMAIN/sitemap.xml" -o "scraped-sites/{clean-domain}/sitemap-raw.xml"
xmllint --format "scraped-sites/{clean-domain}/sitemap-raw.xml" > "scraped-sites/{clean-domain}/sitemap.xml" 2>/dev/null || cat "scraped-sites/{clean-domain}/sitemap-raw.xml" | sed 's/></>\n</g' > "scraped-sites/{clean-domain}/sitemap.xml"
cat "scraped-sites/{clean-domain}/sitemap.xml" | tr '>' '\n' | grep -o 'https://[^<]*' > "scraped-sites/{clean-domain}/sitemap-urls.txt"
rm "scraped-sites/{clean-domain}/sitemap-raw.xml" 2>/dev/null
```

If the sitemap is an index pointing to other sitemaps, fetch those too and format them the same way.

**For all other scrape types (options 1, 2, 3):**

```bash
source ~/.scrapy-crawler-venv/bin/activate
cd /Users/liam.miner/Documents/Liams-AI-projects/crawlers
# If seed URLs were discovered in Step 2b, include --urls flag
python scraper.py --url "DOMAIN" --type TYPE [--urls "scraped-sites/{clean-domain}/seed-urls.txt"]
```

### Step 6: Report Final Results

**If The Full Monty was selected:**

```
**The Full Monty - Scrape Complete!**

**Domain:** {domain}
**Pages crawled:** X
**Category pages:** X
**Product pages:** X
**Other pages:** X
**Unique images found:** X
**Errors:** X

**Output files saved to:**
`/Users/liam.miner/Documents/Liams-AI-projects/crawlers/scraped-sites/{clean-domain}/`

Files:
- `{clean-domain}-fullmonty-{timestamp}.xlsx` - Full audit report
  - Sheet: "Categories" - Category pages with SEO & content metrics
  - Sheet: "Products" - Product data (name, price, SKU, brand, availability) + SEO
  - Sheet: "Other Pages" - Non-category/product pages (if any)
  - Sheet: "Summary" - Scrape overview and statistics
- `sitemap.xml` - Website sitemap, formatted
- `sitemap-urls.txt` - All URLs, one per line

Would you like me to open the results?
```

**For all other scrape types:**

```
**Scrape Complete!**

**Domain:** {domain}
**Type:** {type}
**Pages crawled:** X
**Unique images found:** X
**Errors:** X

**Output files saved to:**
`/Users/liam.miner/Documents/Liams-AI-projects/crawlers/scraped-sites/{clean-domain}/`

Files:
- `{domain}-{type}-{timestamp}.csv` - Page-by-page results
- `{domain}-{type}-{timestamp}_unique.csv` - All unique images
- `sitemap.xml` - Website sitemap, formatted (if requested)
- `sitemap-urls.txt` - All URLs, one per line (if requested)

Would you like me to open the results?
```

---

## Output Structure

All scrape outputs are organized by domain:

```
crawlers/
└── scraped-sites/
    ├── example-com/
    │   ├── example-com-category-20260209-143022.csv
    │   ├── example-com-category-20260209-143022_unique.csv
    │   ├── sitemap.xml (formatted, if requested)
    │   └── sitemap-urls.txt (one URL per line)
    ├── client-site-com/
    │   ├── client-site-com-fullmonty-20260209-150000.xlsx  (Full Monty output)
    │   ├── sitemap.xml
    │   └── sitemap-urls.txt
    └── another-site-com/
        └── ...
```

### Naming Conventions

| File | Naming Pattern | Description |
|------|----------------|-------------|
| Page results | `{domain}-{type}-{timestamp}.csv` | All pages with image counts |
| Unique images | `{domain}-{type}-{timestamp}_unique.csv` | Deduplicated image list |
| Full Monty report | `{domain}-fullmonty-{timestamp}.xlsx` | Multi-sheet Excel audit |
| Sitemap (formatted) | `sitemap.xml` | Formatted XML with line breaks |
| Sitemap URLs | `sitemap-urls.txt` | Plain text, one URL per line |
| Sitemap index files | `sitemap-{name}.xml` | Additional sitemaps if indexed |

---

## Scrape Types

| Type | What It Scrapes | URL Patterns | Output |
|------|-----------------|--------------|--------|
| `category` | Category/collection pages | `/category/`, `/shop/`, `/collections/` | CSV |
| `product` | Product detail pages | `/product/`, `/p/`, `/item/` | CSV |
| `blog` | Blog/news pages | `/blog/`, `/news/`, `/articles/` | CSV |
| `all` | Entire website | All internal links | CSV |
| `fullmonty` | Categories + Products (full data) | Combined category + product patterns | Excel (.xlsx) |

## Command Options

| Option | Default | Description |
|--------|---------|-------------|
| `--max-pages` | 0 (unlimited) | Limit pages to crawl |
| `--delay` | 1.0 | Seconds between requests |
| `--concurrent` | 2 | Simultaneous requests |
| `--urls` | None | Path to text file with seed URLs (one per line) |

---

## Crawl Speed Guidelines

| Site Type | Delay | Concurrent | Notes |
|-----------|-------|------------|-------|
| Client production | 1.0-2.0s | 1-2 | Be gentle |
| Staging/dev | 0.25-0.5s | 4-8 | Faster OK |
| Own site | 0.1s | 8-16 | Go fast |

## Troubleshooting

### Rate Limited (429 errors)
Reduce speed:
```bash
python scraper.py --url "DOMAIN" --type TYPE --delay 2.0 --concurrent 1
```

### Site Blocked by robots.txt
Inform the user - they need to contact the site owner for permission.

### No Images Found (JavaScript sites)
The scraper will automatically use the **Browser Navigation Fallback** (Step 2b) when the connection test only finds the homepage. This opens the site in Chrome to extract navigation links rendered by JavaScript, then feeds them as seed URLs to the crawler. If the fallback is not triggered automatically, try `--type all` to find pages with static images.

### Timeouts
The script has a 30-second per-request timeout. For very slow sites, the user may need to modify `DOWNLOAD_TIMEOUT` in the script.

## File Locations

- **Script**: `/Users/liam.miner/Documents/Liams-AI-projects/crawlers/scraper.py`
- **Output base**: `/Users/liam.miner/Documents/Liams-AI-projects/crawlers/scraped-sites/`
- **Virtual env**: `~/.scrapy-crawler-venv`
