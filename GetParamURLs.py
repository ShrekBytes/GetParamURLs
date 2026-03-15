#!/usr/bin/env python3
"""
URL Collection & Filtering Pipeline
Gathers URLs from historical archives, active crawling, and JS analysis.
Produces a clean GET URL list for the scanner and a separate POST endpoints file.
"""

import os
import re
import sys
import json
import shutil
import subprocess
import argparse
from urllib.parse import urlparse, parse_qs
from pathlib import Path

# ─────────────────────────────────────────────
#  MIME EXTENSIONS TO FILTER OUT
# ─────────────────────────────────────────────
MIME_EXTENSIONS = {
    "jpg", "jpeg", "png", "gif", "webp", "svg", "ico", "bmp", "tiff",
    "mp4", "mov", "avi", "mkv", "webm", "flv",
    "mp3", "m4a", "wav", "ogg", "aac",
    "pdf", "pptx", "ppt", "docx", "doc", "xls", "xlsx", "key",
    "css", "woff", "woff2", "ttf", "eot", "otf",
    "js", "json", "xml",
    "zip", "tar", "gz", "rar", "7z",
    "heic", "eof",
}

MIME_PATTERN = re.compile(
    r"\/([^\/?#]+)\.(%s)(\?[^\/]*$|\/[^\/]*$|#.*$|$)" % "|".join(MIME_EXTENSIONS),
    re.IGNORECASE,
)

# ─────────────────────────────────────────────
#  COLOURS
# ─────────────────────────────────────────────
R = "\033[91m"
G = "\033[92m"
Y = "\033[93m"
C = "\033[96m"
B = "\033[1m"
X = "\033[0m"

def info(msg):  print(f"{C}[*]{X} {msg}")
def ok(msg):    print(f"{G}[+]{X} {msg}")
def warn(msg):  print(f"{Y}[!]{X} {msg}")
def err(msg):   print(f"{R}[-]{X} {msg}")
def head(msg):  print(f"\n{B}{C}{'─'*55}\n  {msg}\n{'─'*55}{X}")


# ─────────────────────────────────────────────
#  TOOL AVAILABILITY CHECK
# ─────────────────────────────────────────────
TOOLS = {
    "gau":          ("required",    "go install github.com/lc/gau/v2/cmd/gau@latest"),
    "waybackurls":  ("required",    "go install github.com/tomnomnom/waybackurls@latest"),
    "katana":       ("recommended", "go install github.com/projectdiscovery/katana/cmd/katana@latest"),
    "gospider":     ("optional",    "go install github.com/jaeles-project/gospider@latest"),
    "subjs":        ("optional",    "go install github.com/lc/subjs@latest"),
    "waymore":      ("optional",    "pip install waymore"),
}

def check_tools() -> dict:
    """Check which tools are available. Returns {tool: bool}."""
    head("Tool Availability Check")
    status = {}
    for tool, (level, install_cmd) in TOOLS.items():
        found = shutil.which(tool) is not None
        status[tool] = found
        if found:
            ok(f"{tool:15} found")
        elif level == "required":
            err(f"{tool:15} NOT FOUND [{level}]  →  {install_cmd}")
        else:
            warn(f"{tool:15} not found [{level}]  →  {install_cmd}")
    return status


# ─────────────────────────────────────────────
#  COMMAND RUNNER
# ─────────────────────────────────────────────
def run(cmd: str, output_file: str = None, timeout: int = 1800) -> bool:
    """
    Run a shell command. If output_file given, redirect stdout there.
    Returns True on success.
    """
    try:
        if output_file:
            with open(output_file, "w") as f:
                result = subprocess.run(
                    cmd, shell=True, stdout=f, stderr=subprocess.DEVNULL,
                    timeout=timeout
                )
        else:
            result = subprocess.run(
                cmd, shell=True, stderr=subprocess.DEVNULL, timeout=timeout
            )
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        warn(f"Command timed out after {timeout}s: {cmd[:60]}")
        return False
    except Exception as e:
        warn(f"Command failed: {e}")
        return False


def run_append(cmd: str, output_file: str, timeout: int = 1800) -> bool:
    """Run command and APPEND stdout to output_file."""
    try:
        with open(output_file, "a") as f:
            result = subprocess.run(
                cmd, shell=True, stdout=f, stderr=subprocess.DEVNULL,
                timeout=timeout
            )
        return result.returncode == 0
    except Exception as e:
        warn(f"Command failed: {e}")
        return False


# ─────────────────────────────────────────────
#  COLLECTION PHASE — HISTORICAL SOURCES
# ─────────────────────────────────────────────
def collect_historical(domain: str, tmpdir: str, tools: dict,
                        include_subs: bool) -> str:
    """
    Collect URLs from gau, waybackurls, waymore.
    Returns path to merged raw file.
    """
    head("Phase 1 — Historical URL Collection")
    merged = f"{tmpdir}/historical_merged.txt"

    # gau — hits Wayback, CommonCrawl, OTX, URLScan
    if tools.get("gau"):
        gau_out = f"{tmpdir}/gau.txt"
        subs_flag = "--subs" if include_subs else ""
        info(f"Running gau {subs_flag}...")
        run(f"gau {subs_flag} --o {gau_out} {domain}")
        count = _count_lines(gau_out)
        ok(f"gau: {count} URLs")

    # waybackurls — dedicated Wayback Machine client
    if tools.get("waybackurls"):
        wb_out = f"{tmpdir}/waybackurls.txt"
        info("Running waybackurls...")
        run(f"waybackurls {domain}", output_file=wb_out)
        count = _count_lines(wb_out)
        ok(f"waybackurls: {count} URLs")

    # waymore — more comprehensive archive source
    if tools.get("waymore"):
        wm_out = f"{tmpdir}/waymore.txt"
        info("Running waymore (this can take a while)...")
        run(f"waymore -i {domain} -mode U -oU {wm_out}")
        count = _count_lines(wm_out)
        ok(f"waymore: {count} URLs")

    # Merge all historical sources
    run(f"cat {tmpdir}/gau.txt {tmpdir}/waybackurls.txt {tmpdir}/waymore.txt 2>/dev/null | sort -u > {merged}")
    ok(f"Historical merged: {_count_lines(merged)} unique URLs")
    return merged


# ─────────────────────────────────────────────
#  COLLECTION PHASE — ACTIVE CRAWLING
# ─────────────────────────────────────────────
def collect_active(domain: str, tmpdir: str, tools: dict,
                   depth: int, cookie: str) -> tuple[str, str]:
    """
    Active crawl with katana and gospider.
    Returns (get_urls_file, post_endpoints_file).
    """
    head("Phase 2 — Active Crawling")

    active_get  = f"{tmpdir}/active_get.txt"
    active_post = f"{tmpdir}/active_post.jsonl"
    target_url  = f"https://{domain}"

    # ── Katana ────────────────────────────────────────────────────
    # Best tool: crawls actively, parses JS, extracts forms
    if tools.get("katana"):
        katana_out = f"{tmpdir}/katana_raw.jsonl"
        cookie_flag = f"-H 'Cookie: {cookie}'" if cookie else ""
        info(f"Running katana (depth={depth}, JS parsing enabled)...")

        # -jc = JS crawling, -kf all = known files, -fx = form extraction
        # -jsonl = structured output for form parsing
        run(
            f"katana -u {target_url} -d {depth} -jc -kf all -fx "
            f"-jsonl -silent {cookie_flag} -o {katana_out}"
        )

        # Parse katana output: separate GET URLs from POST forms
        get_count  = 0
        post_count = 0
        with open(active_get, "a") as get_f, \
             open(active_post, "a") as post_f:
            for line in _read_lines(katana_out):
                try:
                    entry = json.loads(line)
                    req = entry.get("request", {})
                    method = req.get("method", "GET").upper()
                    url    = req.get("endpoint") or entry.get("endpoint", "")

                    if not url:
                        continue

                    if method == "GET":
                        get_f.write(url + "\n")
                        get_count += 1
                    elif method == "POST":
                        # Extract form field names from katana's form data
                        body   = req.get("body", "")
                        params = _extract_post_params(body, entry)
                        post_entry = {
                            "url":    url,
                            "method": "POST",
                            "params": params,
                            "source": "katana_form",
                        }
                        post_f.write(json.dumps(post_entry) + "\n")
                        post_count += 1
                except (json.JSONDecodeError, KeyError):
                    # Plain URL line (non-JSON output)
                    if line.startswith("http"):
                        with open(active_get, "a") as gf:
                            gf.write(line + "\n")
                        get_count += 1

        ok(f"katana: {get_count} GET URLs, {post_count} POST endpoints")

    # ── Gospider ──────────────────────────────────────────────────
    # Good complement: follows sitemaps, robots.txt, collects more links
    if tools.get("gospider"):
        gospider_out = f"{tmpdir}/gospider_raw.txt"
        cookie_flag  = f"--cookie '{cookie}'" if cookie else ""
        info("Running gospider (follows sitemap + robots.txt)...")
        run(
            f"gospider -s {target_url} -d {depth} -t 10 "
            f"--sitemap --robots {cookie_flag} -q -o {tmpdir}/gospider_dir"
        )
        # gospider writes one file per domain in output dir
        run(f"cat {tmpdir}/gospider_dir/* 2>/dev/null > {gospider_out}")

        # Extract URLs from gospider's "[url]" format
        gs_count = 0
        with open(active_get, "a") as get_f:
            for line in _read_lines(gospider_out):
                match = re.search(r'\[url\]\s*-\s*\[.*?\]\s*-\s*(https?://\S+)', line)
                if match:
                    get_f.write(match.group(1) + "\n")
                    gs_count += 1
                elif line.startswith("http"):
                    get_f.write(line + "\n")
                    gs_count += 1

        ok(f"gospider: {gs_count} additional URLs")

    return active_get, active_post


# ─────────────────────────────────────────────
#  COLLECTION PHASE — JS ENDPOINT EXTRACTION
# ─────────────────────────────────────────────
def collect_js_endpoints(domain: str, tmpdir: str, tools: dict,
                          all_urls_so_far: str) -> str:
    """
    Extract endpoints from JavaScript files found during crawling.
    Uses subjs to collect JS URLs, then parses them for hidden API paths.
    Returns path to file containing extracted endpoints.
    """
    head("Phase 3 — JavaScript Endpoint Extraction")

    js_endpoints = f"{tmpdir}/js_endpoints.txt"

    if not tools.get("subjs"):
        warn("subjs not available — skipping JS extraction")
        return js_endpoints

    # Step 1: Collect JS file URLs from all gathered URLs
    js_urls_file = f"{tmpdir}/js_urls.txt"
    info("Extracting JS file URLs from collected URLs...")
    run(f"grep -iE '\\.js(\\?|$)' {all_urls_so_far} > {js_urls_file} 2>/dev/null")

    # Also discover JS files via subjs (feeds domain URLs in)
    subjs_out = f"{tmpdir}/subjs_raw.txt"
    info("Running subjs to discover additional JS files...")
    run(f"echo 'https://{domain}' | subjs -s > {subjs_out}")

    # Merge JS URL sources
    run(f"cat {js_urls_file} {subjs_out} 2>/dev/null | sort -u > {tmpdir}/js_all_urls.txt")
    js_url_count = _count_lines(f"{tmpdir}/js_all_urls.txt")
    info(f"Found {js_url_count} JS files to analyse")

    # Step 2: Parse JS files for endpoints using regex patterns
    # These patterns catch fetch(), axios, $.ajax, href assignments, etc.
    endpoint_patterns = [
        # fetch("...") / fetch('...')
        r'''fetch\s*\(\s*['"`]([^'"`\s]+)['"`]''',
        # axios.get/post/put/delete("...")
        r'''axios\.[a-z]+\s*\(\s*['"`]([^'"`\s]+)['"`]''',
        # $.ajax({url: "..."})
        r'''url\s*:\s*['"`]([/][^'"`\s]+)['"`]''',
        # XMLHttpRequest .open("GET", "...")
        r'''\.open\s*\(\s*['"`][A-Z]+['"`]\s*,\s*['"`]([^'"`\s]+)['"`]''',
        # href="/api/..." or action="/submit"
        r'''(?:href|action|src)\s*=\s*['"`]([/][^'"`\s]+)['"`]''',
        # "/api/v1/something" — API path patterns
        r'''['"`](/(?:api|v\d|rest|graphql|internal|admin)[^'"`\s]*)['"`]''',
    ]
    combined_pattern = re.compile("|".join(f"(?:{p})" for p in endpoint_patterns))

    extracted = set()
    import urllib.request

    for js_url in _read_lines(f"{tmpdir}/js_all_urls.txt"):
        if not js_url.startswith("http"):
            continue
        try:
            req = urllib.request.Request(
                js_url,
                headers={"User-Agent": "Mozilla/5.0"}
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                js_content = resp.read().decode("utf-8", errors="ignore")
            for match in combined_pattern.finditer(js_content):
                for group in match.groups():
                    if group:
                        # Convert relative paths to absolute URLs
                        if group.startswith("/"):
                            parsed = urlparse(js_url)
                            full = f"{parsed.scheme}://{parsed.netloc}{group}"
                        elif group.startswith("http"):
                            full = group
                        else:
                            continue
                        extracted.add(full)
        except Exception:
            continue

    with open(js_endpoints, "w") as f:
        for ep in sorted(extracted):
            f.write(ep + "\n")

    ok(f"JS extraction: {len(extracted)} endpoints found")
    return js_endpoints


# ─────────────────────────────────────────────
#  FILTERING PIPELINE
# ─────────────────────────────────────────────
def filter_urls_with_params(input_file: str, output_file: str) -> int:
    """Keep only URLs that have at least one query parameter."""
    count = 0
    with open(output_file, "w") as out:
        for url in _read_lines(input_file):
            if urlparse(url).query:
                out.write(url + "\n")
                count += 1
    return count


def remove_mime_files(input_file: str, output_file: str) -> int:
    """Remove URLs pointing to static/media files."""
    count = 0
    with open(input_file, "r") as inp, open(output_file, "w") as out:
        for url in inp:
            url = url.strip()
            if url and not MIME_PATTERN.search(url):
                out.write(url + "\n")
                count += 1
    return count


def remove_duplicates(input_file: str, output_file: str) -> int:
    """
    Deduplicate by (endpoint, sorted param keys).
    Keeps one representative URL per unique endpoint+param combination.
    """
    seen   = set()
    unique = []
    for url in _read_lines(input_file):
        parsed   = urlparse(url)
        endpoint = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
        params   = tuple(sorted(parse_qs(parsed.query).keys()))
        key      = (endpoint, params)
        if key not in seen:
            seen.add(key)
            unique.append(url)
    with open(output_file, "w") as out:
        for url in unique:
            out.write(url + "\n")
    return len(unique)


def filter_scope(input_file: str, output_file: str, domain: str) -> int:
    """Remove URLs that don't belong to the target domain."""
    count = 0
    with open(input_file, "r") as inp, open(output_file, "w") as out:
        for url in inp:
            url = url.strip()
            if not url:
                continue
            try:
                netloc = urlparse(url).netloc
                # Match exact domain or subdomains
                if netloc == domain or netloc.endswith(f".{domain}"):
                    out.write(url + "\n")
                    count += 1
            except Exception:
                continue
    return count


# ─────────────────────────────────────────────
#  POST ENDPOINT DEDUPLICATION
# ─────────────────────────────────────────────
def dedup_post_endpoints(raw_post_file: str, output_file: str) -> int:
    """Deduplicate POST endpoints by (url, sorted param keys)."""
    seen    = set()
    entries = []

    for line in _read_lines(raw_post_file):
        try:
            entry  = json.loads(line)
            url    = entry.get("url", "")
            params = tuple(sorted(entry.get("params", [])))
            key    = (url, params)
            if key not in seen:
                seen.add(key)
                entries.append(entry)
        except json.JSONDecodeError:
            continue

    with open(output_file, "w") as out:
        for entry in entries:
            out.write(json.dumps(entry) + "\n")

    return len(entries)


# ─────────────────────────────────────────────
#  HELPERS
# ─────────────────────────────────────────────
def _read_lines(path: str):
    """Yield stripped non-empty lines from a file, silently skip if missing."""
    try:
        with open(path, "r", errors="ignore") as f:
            for line in f:
                line = line.strip()
                if line:
                    yield line
    except FileNotFoundError:
        return


def _count_lines(path: str) -> int:
    try:
        with open(path, "r", errors="ignore") as f:
            return sum(1 for l in f if l.strip())
    except FileNotFoundError:
        return 0


def _extract_post_params(body: str, entry: dict) -> list:
    """
    Extract POST parameter names from katana form body or entry metadata.
    """
    params = []
    # Try katana's form_data field
    form_data = entry.get("request", {}).get("form_data", {})
    if isinstance(form_data, dict) and form_data:
        params = list(form_data.keys())
    elif body:
        # Parse application/x-www-form-urlencoded body
        for pair in body.split("&"):
            if "=" in pair:
                params.append(pair.split("=")[0])
    return params


def _merge_files(*paths: str, output: str):
    """Merge multiple files into one."""
    with open(output, "w") as out:
        for path in paths:
            for line in _read_lines(path):
                out.write(line + "\n")


def _cleanup(*paths: str):
    for path in paths:
        try:
            if os.path.isdir(path):
                import shutil
                shutil.rmtree(path)
            elif os.path.exists(path):
                os.remove(path)
        except Exception:
            pass


# ─────────────────────────────────────────────
#  ARGUMENT PARSER
# ─────────────────────────────────────────────
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="URL Collection & Filtering Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 collect.py example.com
  python3 collect.py example.com --subs --depth 3
  python3 collect.py example.com --cookie "session=abc123" --no-active
  python3 collect.py example.com --no-js --keep-tmp
        """
    )
    p.add_argument("domain",
                   help="Target domain (e.g. example.com)")
    p.add_argument("--subs", action="store_true",
                   help="Include subdomains in collection")
    p.add_argument("--depth", type=int, default=2,
                   help="Crawl depth for active crawlers (default: 2)")
    p.add_argument("--cookie",
                   help='Cookie for authenticated crawling e.g. "session=abc"')
    p.add_argument("--no-active", action="store_true",
                   help="Skip active crawling (katana, gospider)")
    p.add_argument("--no-js", action="store_true",
                   help="Skip JS endpoint extraction")
    p.add_argument("--no-historical", action="store_true",
                   help="Skip historical sources (gau, waybackurls, waymore)")
    p.add_argument("--keep-tmp", action="store_true",
                   help="Keep intermediate tmp files for debugging")
    return p


# ─────────────────────────────────────────────
#  MAIN
# ─────────────────────────────────────────────
def main():
    parser = build_parser()
    args   = parser.parse_args()
    domain = args.domain

    print(f"\n{B}{'═'*55}")
    print(f"  URL Collection Pipeline  →  {domain}")
    print(f"{'═'*55}{X}\n")

    # Check tools
    tools = check_tools()

    # Bail if required tools missing
    if not tools.get("gau") and not tools.get("waybackurls") and args.no_active:
        err("No collection tools available and --no-active set. Nothing to do.")
        sys.exit(1)

    # Working directory for intermediate files
    tmpdir = f"{domain}_tmp"
    os.makedirs(tmpdir, exist_ok=True)

    # Output file paths
    get_output  = f"{domain}.txt"         # → feed into scanner.py
    post_output = f"{domain}_post.jsonl"  # → POST endpoints for manual/scanner use

    all_raw = f"{tmpdir}/all_raw.txt"     # staging merge file

    # ── Phase 1: Historical ────────────────────────────────────
    if not args.no_historical:
        hist_merged = collect_historical(domain, tmpdir, tools, args.subs)
        _merge_files(hist_merged, output=all_raw)
    else:
        info("Skipping historical collection (--no-historical)")
        open(all_raw, "a").close()

    # ── Phase 2: Active Crawling ───────────────────────────────
    if not args.no_active:
        if tools.get("katana") or tools.get("gospider"):
            active_get, active_post = collect_active(
                domain, tmpdir, tools, args.depth, args.cookie
            )
            _merge_files(all_raw, active_get, output=all_raw + ".tmp")
            os.replace(all_raw + ".tmp", all_raw)
        else:
            warn("Neither katana nor gospider available — skipping active crawl")
            active_post = f"{tmpdir}/active_post.jsonl"
    else:
        info("Skipping active crawling (--no-active)")
        active_post = f"{tmpdir}/active_post.jsonl"
        open(active_post, "a").close()

    # ── Phase 3: JS Extraction ─────────────────────────────────
    if not args.no_js:
        js_eps = collect_js_endpoints(domain, tmpdir, tools, all_raw)
        _merge_files(all_raw, js_eps, output=all_raw + ".tmp")
        os.replace(all_raw + ".tmp", all_raw)
    else:
        info("Skipping JS extraction (--no-js)")

    # ── Filtering Pipeline (GET URLs) ──────────────────────────
    head("Filtering Pipeline")

    raw_count = _count_lines(all_raw)
    info(f"Total raw URLs collected: {raw_count}")

    # 1. Scope filter — keep only target domain (and subs if requested)
    scoped = f"{tmpdir}/scoped.txt"
    count = filter_scope(all_raw, scoped, domain)
    ok(f"After scope filter:      {count}")

    # 2. Keep only URLs with query parameters
    has_params = f"{tmpdir}/has_params.txt"
    count = filter_urls_with_params(scoped, has_params)
    ok(f"After param filter:      {count}")

    # 3. Remove static/media file URLs
    no_mimes = f"{tmpdir}/no_mimes.txt"
    count = remove_mime_files(has_params, no_mimes)
    ok(f"After MIME filter:       {count}")

    # 4. Deduplicate by endpoint+param signature
    count = remove_duplicates(no_mimes, get_output)
    ok(f"After deduplication:     {count}  →  {get_output}")

    # ── POST Endpoint Processing ───────────────────────────────
    post_count = dedup_post_endpoints(active_post, post_output)
    if post_count > 0:
        ok(f"POST endpoints:          {post_count}  →  {post_output}")
    else:
        info("No POST endpoints found (active crawl may not have run)")

    # ── Cleanup ────────────────────────────────────────────────
    if not args.keep_tmp:
        info("Cleaning up intermediate files...")
        _cleanup(tmpdir)

    # ── Summary ────────────────────────────────────────────────
    head("Done")
    print(f"  {G}GET URLs (scanner input){X}  →  {B}{get_output}{X}  ({_count_lines(get_output)} URLs)")
    if post_count > 0:
        print(f"  {G}POST endpoints{X}           →  {B}{post_output}{X}  ({post_count} endpoints)")
    print()
    print(f"  Next step:")
    print(f"  {C}python3 scanner.py {get_output}{X}")
    if post_count > 0:
        print(f"  {C}python3 scanner.py {post_output} --post-mode{X}  (after adding POST support)")
    print()


if __name__ == "__main__":
    main()
