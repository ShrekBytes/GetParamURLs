# GetParamURLs

GetParamURLs is a Python-based URL collection and filtering pipeline for bug bounty hunters. It gathers endpoints from historical archives, actively crawls the live target, extracts hidden endpoints from JavaScript files, and outputs a clean, deduplicated list of GET URLs with query parameters — plus a separate file of POST form endpoints — ready to feed directly into a scanner.

![screenshot](screenshot.png)

## Table of Contents

- [Features](#features)
- [How It Works](#how-it-works)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Usage](#usage)
- [Output Files](#output-files)
- [Contributing](#contributing)
- [License](#license)

---

## Features

- **Historical collection** via `gau` (Wayback, CommonCrawl, OTX, URLScan), `waybackurls`, and `waymore`
- **Active crawling** via `katana` (JS-rendered, follows `fetch()`/XHR calls) and `gospider` (follows `robots.txt` + `sitemap.xml`)
- **JavaScript endpoint extraction** via `LinkFinder` — fetches every linked JS file and extracts API paths, route definitions, and endpoint strings using battle-tested regex patterns tuned for minified and bundled JS
- **POST form extraction** — katana detects HTML forms with `method="post"` and extracts field names into a separate structured file
- **Scope filtering** — removes URLs outside the target domain before any further processing
- **MIME type filtering** — strips URLs pointing to images, fonts, media, scripts, stylesheets, and other non-interesting static files
- **Smart deduplication** — removes duplicate URLs by endpoint + parameter signature, keeping one representative URL per unique combination regardless of different parameter values
- **Subdomain support** — optional flag to include subdomains in collection
- **Authenticated crawling** — pass a cookie string for scanning behind login walls
- **Configurable crawl depth** — control how deep active crawlers go
- **Intermediate file cleanup** — tmp files deleted automatically unless `--keep-tmp` is set

---

## How It Works

The pipeline runs in three sequential phases:

**Phase 1 — Historical collection**
Queries `gau`, `waybackurls`, and `waymore` for archived URLs. These sources cover Wayback Machine, CommonCrawl, OTX, and URLScan. Fast, no active requests to the target.

**Phase 2 — Active crawling**
`katana` actively spiders the live site, renders JavaScript, and parses `fetch()`/XHR calls to discover endpoints that were never archived. It also detects HTML forms and records their method and input field names. `gospider` adds coverage via `robots.txt` and `sitemap.xml`.

**Phase 3 — JavaScript endpoint extraction**
Runs `linkfinder` in two passes: first a full domain crawl (`-d` flag) where LinkFinder discovers and parses all JS files automatically, then a second pass against individual JS file URLs collected during phases 1 and 2 to catch files on CDN subdomains or paths the domain crawl missed. All extracted paths are converted to absolute URLs before entering the filtering pipeline.

After collection, all URLs pass through a filtering pipeline: scope check → query param filter → MIME filter → deduplication.

---

## Prerequisites

### Required

- **Python 3.10+**
- **gau** — [github.com/lc/gau](https://github.com/lc/gau)
- **waybackurls** — [github.com/tomnomnom/waybackurls](https://github.com/tomnomnom/waybackurls)

### Recommended

- **katana** — [github.com/projectdiscovery/katana](https://github.com/projectdiscovery/katana)
  Required for active crawling, JS parsing, and POST form extraction. Without it you only get historical URLs.

### Optional but valuable

- **LinkFinder** — [github.com/GerbenJavado/LinkFinder](https://github.com/GerbenJavado/LinkFinder)
  Required for Phase 3 JS endpoint extraction. Fetches JS files and extracts hidden API paths and endpoints using regex patterns specifically tuned for real-world minified JS. Without it the JS extraction phase is skipped entirely.
- **gospider** — [github.com/jaeles-project/gospider](https://github.com/jaeles-project/gospider)
  Adds sitemap and robots.txt coverage.
- **waymore** — [github.com/xnl-h4ck3r/waymore](https://github.com/xnl-h4ck3r/waymore)
  More thorough archive coverage than gau alone.

The script checks all tools on startup and tells you exactly what is missing and how to install it. Missing optional tools are skipped gracefully — the pipeline runs with whatever is available.

---

## Installation

### 1. Install Go

All the Go-based tools require Go. If you don't have it:

```sh
# Linux
wget https://go.dev/dl/go1.22.0.linux-amd64.tar.gz
sudo tar -C /usr/local -xzf go1.22.0.linux-amd64.tar.gz
export PATH=$PATH:/usr/local/go/bin
echo 'export PATH=$PATH:/usr/local/go/bin' >> ~/.bashrc

# macOS (with Homebrew)
brew install go
```

Verify Go is working:

```sh
go version
```

Make sure your Go bin directory is in PATH so installed tools are accessible:

```sh
export PATH=$PATH:$(go env GOPATH)/bin
echo 'export PATH=$PATH:$(go env GOPATH)/bin' >> ~/.bashrc
source ~/.bashrc
```

---

### 2. Install the Go tools

```sh
go install github.com/lc/gau/v2/cmd/gau@latest
go install github.com/tomnomnom/waybackurls@latest
go install github.com/projectdiscovery/katana/cmd/katana@latest
go install github.com/jaeles-project/gospider@latest
```

Verify each one works:

```sh
gau --version
waybackurls --version
katana -version
gospider --version
```

---

### 3. Install LinkFinder

LinkFinder is a Python tool installed from source:

```sh
git clone https://github.com/GerbenJavado/LinkFinder.git
cd LinkFinder
pip install -r requirements.txt
python3 setup.py install
cd ..
```

Verify it works:

```sh
linkfinder --help
```

---

### 4. Install optional Python tools

```sh
pip install waymore
```

---

### 5. Clone this repository

```sh
git clone https://github.com/ShrekBytes/GetParamURLs.git
cd GetParamURLs
```

---

## Usage

### Quickstart — run everything

This is the recommended command for most targets. Runs all three phases with subdomains included:

```sh
python3 collect.py example.com --subs
```

Expected output:

```
[*] Tool Availability Check
[+] gau             found
[+] waybackurls     found
[+] katana          found
[+] gospider        found
[+] linkfinder      found
[+] waymore         found

[*] Phase 1 — Historical URL Collection
[*] Running gau --subs...
[+] gau: 18400 URLs
[*] Running waybackurls...
[+] waybackurls: 12300 URLs
[*] Running waymore...
[+] waymore: 9800 URLs
[+] Historical merged: 24100 unique URLs

[*] Phase 2 — Active Crawling
[*] Running katana (depth=2, JS parsing enabled)...
[+] katana: 3200 GET URLs, 47 POST endpoints
[*] Running gospider (follows sitemap + robots.txt)...
[+] gospider: 840 additional URLs

[*] Phase 3 — JavaScript Endpoint Extraction
[*] Running linkfinder domain crawl on https://example.com...
[+] LinkFinder domain crawl: 480 endpoints
[*] Running linkfinder on 310 individual JS files...
[+] LinkFinder per-file: 290 additional endpoints
[+] JS extraction total: 620 unique endpoints found

[*] Filtering Pipeline
[+] After scope filter:      26800
[+] After param filter:      8400
[+] After MIME filter:       7100
[+] After deduplication:     3200  →  example.com.txt
[+] POST endpoints:          47    →  example.com_post.jsonl

  GET URLs        →  example.com.txt           (3200 URLs)
  POST endpoints  →  example.com_post.jsonl    (47 endpoints)

  Next step:
  python3 scanner.py example.com.txt
```

---

### Common scenarios

**Basic — no subdomains, default depth:**
```sh
python3 collect.py example.com
```

**Include subdomains (recommended for most bug bounty scopes):**
```sh
python3 collect.py example.com --subs
```

**Authenticated target:**

Log into the target in your browser, open DevTools → Application → Cookies, copy the relevant cookie values, then pass them in:

```sh
python3 collect.py example.com --subs --cookie "session=abc123; user=xyz"
```

**Deeper crawl — more coverage, takes longer:**
```sh
python3 collect.py example.com --subs --depth 4
```

**Historical only — fastest, zero active requests to the target:**
```sh
python3 collect.py example.com --no-active --no-js
```

**Debug mode — keep all intermediate files to inspect each phase:**
```sh
python3 collect.py example.com --keep-tmp
```

**Full command with all options:**
```sh
python3 collect.py example.com \
  --subs \
  --depth 3 \
  --cookie "session=abc123; csrf=xyz" \
  --keep-tmp
```

---

### All flags

```
positional arguments:
  domain             Target domain (e.g. example.com)

options:
  --subs             Include subdomains in collection
  --depth N          Crawl depth for active crawlers (default: 2)
  --cookie COOKIE    Cookie for authenticated crawling e.g. "session=abc"
  --no-active        Skip active crawling (katana, gospider)
  --no-js            Skip JavaScript endpoint extraction (LinkFinder)
  --no-historical    Skip historical sources (gau, waybackurls, waymore)
  --keep-tmp         Keep intermediate files for debugging
```

---

## Output Files

After running, you get two files:

| File | Contents | Use for |
|---|---|---|
| `example.com.txt` | Deduplicated GET URLs with query params, one per line | Feed into scanner |
| `example.com_post.jsonl` | POST endpoints with parameter names, one JSON object per line | Manual testing or scanner POST mode |

### GET URLs — `example.com.txt`

Plain text, one URL per line:

```
https://example.com/search?q=hello&page=1
https://example.com/api/user?id=42&format=json
https://example.com/filter?category=shoes&sort=price&order=asc
```

### POST endpoints — `example.com_post.jsonl`

One JSON object per line. Each entry contains the endpoint URL, method, and the form field names extracted from the HTML form:

```json
{"url": "https://example.com/login", "method": "POST", "params": ["username", "password", "csrf_token"], "source": "katana_form"}
{"url": "https://example.com/search", "method": "POST", "params": ["q", "filter", "page"], "source": "katana_form"}
{"url": "https://example.com/profile/update", "method": "POST", "params": ["name", "email", "bio"], "source": "katana_form"}
```

Use this file to manually craft POST requests in Burp Suite, injecting probe values into each listed parameter.

---

## Full workflow with the scanner

```sh
# Step 1 — collect and filter URLs
python3 collect.py example.com --subs

# Step 2 — scan GET URLs for reflection points and inject blind payloads
python3 scanner.py example.com.txt

# Step 3 — if any URLs failed due to network issues, re-run the failed list
python3 scanner.py example.com_failed.txt
```

---

## Contributing

Feel free to submit issues or pull requests for suggestions, improvements, or bug reports. Your contributions are appreciated!

---

## License

"License? Nah, who needs those bothersome regulations anyway? Feel free to do whatever you want with this code – use it as a doorstop, launch it into space, or frame it as a modern art masterpiece. Just don't blame me if things get a little wild!"
