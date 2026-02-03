---
name: scraper
description: Website image extraction skill - scrape category, product, or blog pages for images. Use when the user wants to extract images from a website.
allowed-tools: Bash
argument-hint: "[start | URL]"
---

# Scraper: Website Image Extraction Skill

Extract images from any website by category pages, product pages, or the entire site.

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

### Step 3: Ask Target Area

Ask the user what they want to scrape:

```
**What would you like to scrape?**

1. **Categories only** - Category/collection pages (excludes homepage & CMS pages)
2. **Products only** - Product detail pages (excludes homepage & CMS pages)
3. **Full site** - All pages including homepage and CMS pages

Which option: 1, 2, or 3?
```

**IMPORTANT:**
- If user selects **Categories only** or **Products only**, the scraper must EXCLUDE:
  - Homepage images
  - CMS/content pages (about, contact, terms, etc.)
  - Only scrape pages matching the specific URL patterns for that type

### Step 4: Ask About Sitemap

Ask the user:

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

**Run the full scrape with output to the domain folder:**

```bash
cd /Users/liam.miner/Documents/Liams-AI-projects/crawlers
python scraper.py --url "DOMAIN" --type TYPE
```

**Then move the output files to the domain folder:**

```bash
mv {domain}-{type}.csv scraped-sites/{clean-domain}/
mv {domain}-{type}_unique.csv scraped-sites/{clean-domain}/
```

### Step 6: Report Final Results

After scrape completes, report:

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
- `{domain}-{type}.csv` - Page-by-page results
- `{domain}-{type}_unique.csv` - All unique images
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
    │   ├── example-com-category.csv
    │   ├── example-com-category_unique.csv
    │   ├── sitemap.xml (formatted, if requested)
    │   └── sitemap-urls.txt (one URL per line)
    ├── part-on-co-uk/
    │   ├── part-on-co-uk-product.csv
    │   ├── part-on-co-uk-product_unique.csv
    │   ├── sitemap.xml
    │   └── sitemap-urls.txt
    └── another-site-com/
        └── ...
```

### Naming Conventions

| File | Naming Pattern | Description |
|------|----------------|-------------|
| Page results | `{domain}-{type}.csv` | All pages with image counts |
| Unique images | `{domain}-{type}_unique.csv` | Deduplicated image list |
| Sitemap (formatted) | `sitemap.xml` | Formatted XML with line breaks |
| Sitemap URLs | `sitemap-urls.txt` | Plain text, one URL per line |
| Sitemap index files | `sitemap-{name}.xml` | Additional sitemaps if indexed |

---

## Scrape Types

| Type | What It Scrapes | URL Patterns |
|------|-----------------|--------------|
| `category` | Category/collection pages | `/category/`, `/shop/`, `/collections/` |
| `product` | Product detail pages | `/product/`, `/p/`, `/item/` |
| `blog` | Blog/news pages | `/blog/`, `/news/`, `/articles/` |
| `all` | Entire website | All internal links |

## Command Options

| Option | Default | Description |
|--------|---------|-------------|
| `--max-pages` | 0 (unlimited) | Limit pages to crawl |
| `--delay` | 1.0 | Seconds between requests |
| `--concurrent` | 2 | Simultaneous requests |

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
Try `--type all` to find pages with static images. Some sites load category listings via JavaScript but have static images on product/article pages.

### Timeouts
The script has a 30-second per-request timeout. For very slow sites, the user may need to modify `DOWNLOAD_TIMEOUT` in the script.

## File Locations

- **Script**: `/Users/liam.miner/Documents/Liams-AI-projects/crawlers/scraper.py`
- **Output base**: `/Users/liam.miner/Documents/Liams-AI-projects/crawlers/scraped-sites/`
- **Virtual env**: `~/.scrapy-crawler-venv`
