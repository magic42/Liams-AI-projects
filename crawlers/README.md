# Website Image Scraper

A Scrapy-based tool for extracting images from websites. Alternative to Screaming Frog for image auditing.

## Quick Start

```bash
# 1. Activate the virtual environment
source ~/.scrapy-crawler-venv/bin/activate

# 2. Navigate to the crawlers folder
cd /Users/liam.miner/Documents/Liams-AI-projects/crawlers

# 3. Run the scraper
python scraper.py --url "www.example.com" --type category
```

---

## Using with Claude Code (`/scraper`)

The easiest way to use this tool is via the `/scraper` skill in Claude Code:

```
/scraper www.part-on.co.uk
/scraper start
```

### User Journey

The `/scraper` skill guides you through a structured workflow with built-in safety nets at every step:

```
┌─────────────────────────────────────────────────────────────┐
│  Step 1: URL Input                                          │
│  ─────────────────                                          │
│  Enter your target website URL                              │
│  → Cleaned automatically (removes http/https, trailing /)   │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  Step 2: Connection Test (Safety Net #1)                    │
│  ────────────────────────────────────────                   │
│  Runs a dual test: 5 category + 5 product pages             │
│  → Shows results table so you can verify it's working       │
│  → 2-minute timeout prevents getting stuck                  │
│  → If both fail, stops and offers troubleshooting           │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  Step 3: Target Selection (Safety Net #2)                   │
│  ─────────────────────────────────────────                  │
│  You choose what to scrape:                                 │
│    1. Categories only - excludes homepage/CMS pages         │
│    2. Products only - excludes homepage/CMS pages           │
│    3. Full site - everything                                │
│  → No scrape runs until you explicitly choose               │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  Step 4: Sitemap Option                                     │
│  ─────────────────────                                      │
│  Optionally download and format the sitemap.xml             │
│  → Saved as formatted XML + plain URL list                  │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  Step 5: Full Scrape                                        │
│  ─────────────────────                                      │
│  Only runs after you've approved the test results           │
│  → Outputs to organized folder structure                    │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  Step 6: Results Report                                     │
│  ─────────────────────                                      │
│  Summary of what was found + file locations                 │
│  → Offers to open results for you                           │
└─────────────────────────────────────────────────────────────┘
```

### Safety Nets & Guardrails

| Safety Net | What It Protects Against |
|------------|-------------------------|
| **Connection Test** | Wasting time on sites that block crawlers or use JavaScript rendering |
| **2-Minute Timeout** | Getting stuck on slow/unresponsive sites |
| **User Confirmation** | Running full scrapes without understanding the results |
| **robots.txt Compliance** | Scraping content the site owner has blocked |
| **Rate Limiting Defaults** | Overloading servers (1s delay, 2 concurrent by default) |
| **Image Filtering** | Cluttering results with icons, placeholders, and tracking pixels |

### Example Interaction

```
User: /scraper www.part-on.co.uk

Agent: Running test scrapes (5 category + 5 product pages)...

**Connection Test Results for www.part-on.co.uk**

### Category Pages (5 tested)
| Page | Images Found |
|------|--------------|
| /category/rivet-tools/ | 8 images |
| /category/offers/ | 27 images |
| /category/rivetnuts/ | 9 images |
| /category/fasteners/ | 12 images |
| /category/air-tools/ | 15 images |

### Product Pages (5 tested)
| Page | Images Found |
|------|--------------|
| /product/rivet-gun-pro/ | 6 images |
| /product/steel-rivets-pack/ | 4 images |
| /product/air-compressor/ | 8 images |
| /product/rivet-nut-tool/ | 5 images |
| /product/fastener-kit/ | 7 images |

**Summary:**
- Category pages: 71 images from 5 pages
- Product pages: 30 images from 5 pages

What would you like to scrape?
1. Categories only
2. Products only
3. Full site

User: Just categories please

Agent: [asks about sitemap, then runs full scrape, reports results]
```

---

## Manual Usage

### Usage Examples

#### Scrape Category Pages
```bash
python scraper.py --url "www.part-on.co.uk" --type category
```

#### Scrape Product Pages
```bash
python scraper.py --url "www.example.com" --type product
```

#### Scrape Entire Site
```bash
python scraper.py --url "www.example.com" --type all
```

#### Limit Pages (for testing)
```bash
python scraper.py --url "www.example.com" --type category --max-pages 20
```

#### Faster Crawl (staging/dev sites)
```bash
python scraper.py --url "staging.example.com" --type all --delay 0.25 --concurrent 8
```

## Scrape Types

| Type | What It Scrapes | URL Patterns Matched |
|------|-----------------|----------------------|
| `category` | Category/collection pages | `/category/`, `/categories/`, `/shop/`, `/collections/`, `/browse/` |
| `product` | Product detail pages | `/product/`, `/products/`, `/p/`, `/item/` |
| `blog` | Blog/news pages | `/blog/`, `/news/`, `/articles/` |
| `all` | Entire website | All internal links |

## Command Options

| Option | Default | Description |
|--------|---------|-------------|
| `--url`, `-u` | Required | Website domain (e.g., `www.example.com`) |
| `--type`, `-t` | Required | Scrape type: `category`, `product`, `blog`, or `all` |
| `--max-pages`, `-m` | 0 (unlimited) | Maximum pages to crawl |
| `--delay`, `-d` | 1.0 | Seconds between requests |
| `--concurrent`, `-c` | 2 | Simultaneous requests |

## Output Files

The scraper creates two CSV files in the `crawlers` folder:

### 1. Page Results: `{domain}-{type}.csv`

| Column | Description |
|--------|-------------|
| `page_url` | URL of the crawled page |
| `page_title` | Page title |
| `image_count` | Number of images found |
| `images` | JSON array of image data |

### 2. Unique Images: `{domain}-{type}_unique.csv`

| Column | Description |
|--------|-------------|
| `src` | Full image URL |
| `alt` | Image alt text |
| `pages_found_on` | JSON array of pages containing this image |
| `page_count` | Number of pages using this image |

**Example filenames:**
- `part-on-co-uk-category.csv`
- `part-on-co-uk-category_unique.csv`

## Crawl Speed Guidelines

| Scenario | Delay | Concurrent | Approx Speed |
|----------|-------|------------|--------------|
| Client production site | 1.0-2.0s | 1-2 | ~30-60 pages/min |
| Staging/dev site | 0.25-0.5s | 4-8 | ~120-240 pages/min |
| Your own site | 0.1s | 8-16 | ~400+ pages/min |

**Rule of thumb:** Start conservative, increase speed if the server handles it well.

## How It Works

1. **Starts from homepage** - The crawler begins at the domain's root URL
2. **Follows links** - Discovers internal links matching the scrape type patterns
3. **Extracts images** - For each page, finds all `<img>` tags and background images
4. **Filters junk** - Excludes icons, placeholders, tracking pixels, etc.
5. **Deduplicates** - Tracks unique images across all pages
6. **Saves results** - Outputs CSV files when complete

### What Gets Filtered Out

The scraper automatically excludes:
- Images smaller than 50x50 pixels (when dimensions are in HTML)
- Placeholder/loading images
- Icons and logos
- Tracking pixels
- WordPress plugin assets
- Gravatar images

## Troubleshooting

### "Forbidden by robots.txt"

The website has blocked crawling of certain paths. Options:
1. Use `--type all` to try other accessible pages
2. Contact the site owner for permission
3. Check the site's `/robots.txt` to see what's allowed

### No Images Found on Pages

The site likely uses JavaScript to load images dynamically. Scrapy only sees the initial HTML. Options:
1. Try `--type all` to find pages with static images
2. Check if product pages have static images (even if categories don't)
3. The @scraper agent tests both types automatically to identify this

### Rate Limited (429 Errors)

Slow down the crawl:
```bash
python scraper.py --url "www.example.com" --type all --delay 2.0 --concurrent 1
```

### Timeouts

The site is slow to respond. The default timeout is 30 seconds. For very slow sites, you may need to modify `DOWNLOAD_TIMEOUT` in the script.

### "ReactorNotRestartable" Error

This happens if you try to run the spider twice in the same Python session. Restart your terminal or use a fresh Python session.

## First-Time Setup

If you haven't set up the environment yet:

```bash
# Install uv package manager (if not installed)
brew install uv

# Create virtual environment
python3 -m venv ~/.scrapy-crawler-venv

# Activate and install Scrapy
source ~/.scrapy-crawler-venv/bin/activate
uv pip install scrapy
```

## File Locations

| File | Location |
|------|----------|
| Scraper script | `crawlers/scraper.py` |
| Output CSVs | `crawlers/` |
| Virtual environment | `~/.scrapy-crawler-venv` |
| Skill definition | `.claude/skills/scraper.md` |

## Tips

1. **Use the @scraper agent** - It runs tests automatically and handles errors gracefully

2. **Check both page types** - Some sites load category images via JavaScript but have static product images

3. **Be polite** - Use appropriate delays for production sites to avoid overloading them

4. **Open results in Excel** - The CSV files work well in Excel/Google Sheets for filtering and analysis

5. **Test first manually** - Use `--max-pages 5` to verify the scraper finds what you need before a full crawl
