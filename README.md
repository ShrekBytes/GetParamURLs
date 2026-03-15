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
- **JavaScript endpoint extraction** — fetches all linked `.js` files and applies regex patterns for `fetch()`, `axios`, `$.ajax`, XHR `.open()`, and embedded API paths
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
Collects all `.js` file URLs found during the previous phases, fetches each one, and applies regex patterns to extract API paths, route definitions, and endpoint strings embedded in the code.

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

- **gospider** — [github.com/jaeles-project/gospider](https://github.com/jaeles-project/gospider)
  Adds sitemap and robots.txt coverage.
- **subjs** — [github.com/lc/subjs](https://github.com/lc/subjs)
  Discovers additional JS files for endpoint extraction.
- **waymore** — [github.com/xnl-h4ck3r/waymore](https://github.com/xnl-h4ck3r/waymore)
  More thorough archive coverage than gau alone.

The script checks all tools on startup and tells you exactly what is missing and how to install it. Missing optional tools are skipped gracefully — the pipeline runs with whatever is available.

---

## Installation

### 1. Install Go

All the external tools are written in Go. If you don't have Go installed:

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
go install github.com/lc/subjs@latest
```

Verify each one works:

```sh
gau --version
waybackurls --version
katana -version
gospider --version
subjs --version
```

---

### 3. Install the optional Python tool

```sh
pip install waymore
```

---

### 4. Clone this repository

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
[+] subjs           found
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
[+] Found 310 JS files to analyse
[+] JS extraction: 620 endpoints found

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
  --no-js            Skip JavaScript endpoint extraction
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
