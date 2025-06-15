import requests
import time
import os
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

SITEMAP_INDEX = "https://example.com/sitemap_index.xml"
OUTPUT_FILE = "broken_links_report.txt"
PROGRESS_FILE = "progress.txt"
WAIT_BETWEEN_PAGES = 10
CHECK_INTERNAL_LINKS = False
CHECK_EXTERNAL_LINKS = True

INTERNAL_DELAY = 5
EXTERNAL_DELAY = 0

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; LinkChecker/1.0; +https://theanxietyguy.com)"
}

EXCLUDED_SCHEMES = ("mailto:", "tel:", "javascript:")
EXCLUDED_EXTENSIONS = (".jpg", ".jpeg", ".png", ".gif", ".svg", ".webp", ".pdf", ".css", ".js", ".ico")
DOMAIN = "theanxietyguy.com"

def get_sitemaps(index_url):
    print("[*] Fetching sitemap index...")
    try:
        response = requests.get(index_url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, "xml")
        return [tag.text for tag in soup.find_all("loc")]
    except Exception as e:
        print(f"[!] Failed to fetch sitemap index: {e}")
        return []

def get_urls_from_sitemap(sitemap_url):
    try:
        response = requests.get(sitemap_url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, "xml")
        return [tag.text for tag in soup.find_all("loc")]
    except Exception as e:
        print(f"[!] Failed to fetch sitemap {sitemap_url}: {e}")
        return []

def extract_links_from_entry_container(page_url):
    try:
        response = requests.get(page_url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        entry_div = soup.find("div", class_="entry-container content")
        if not entry_div:
            return []

        links = []
        for a in entry_div.find_all("a", href=True):
            href = a["href"].strip()

            if href.lower().startswith(EXCLUDED_SCHEMES):
                continue
            if "?share=x" in href:
                continue
            if any(href.lower().endswith(ext) for ext in EXCLUDED_EXTENSIONS):
                continue

            full_url = urljoin(page_url, href)
            links.append(full_url)

        return links

    except Exception as e:
        print(f"[!] Failed to load page {page_url}: {e}")
        return []

def is_internal(url):
    parsed = urlparse(url)
    return DOMAIN in parsed.netloc

def check_link(url):
    try:
        response = requests.head(url, allow_redirects=True, timeout=10, headers=HEADERS)
        return response.status_code
    except Exception:
        try:
            response = requests.get(url, allow_redirects=True, timeout=10, headers=HEADERS)
            return response.status_code
        except Exception:
            return None

def log_broken_link(page_url, link, status, source):
    with open(OUTPUT_FILE, "a", encoding="utf-8") as report:
        report.write(f"\n[!] Broken Link Found\n")
        report.write(f"    Page     : {page_url}\n")
        report.write(f"    Link     : {link}\n")
        report.write(f"    Type     : {source}\n")
        report.write(f"    Status   : {status}\n")

def save_progress(url):
    with open(PROGRESS_FILE, "a", encoding="utf-8") as f:
        f.write(url + "\n")

def load_progress():
    if not os.path.exists(PROGRESS_FILE):
        return set()
    with open(PROGRESS_FILE, "r", encoding="utf-8") as f:
        return set(line.strip() for line in f.readlines())

def clear_progress():
    if os.path.exists(PROGRESS_FILE):
        os.remove(PROGRESS_FILE)
    if os.path.exists(OUTPUT_FILE):
        os.remove(OUTPUT_FILE)

def main():
    print("[*] Starting Broken Link Checker with Resume Support...\n")

    resume = input("Do you want to continue from where you left off? (y/n): ").strip().lower()
    if resume != "y":
        clear_progress()
        print("Progress and broken link report cleared. Starting fresh...\n")
        scanned_urls = set()
    else:
        scanned_urls = load_progress()
        print(f"Resuming. Already scanned: {len(scanned_urls)} URLs\n")

    sitemaps = get_sitemaps(SITEMAP_INDEX)
    if not sitemaps:
        print("[X] No sitemaps found.")
        input("\nPress Enter to exit...")
        return

    all_page_urls = []
    for sitemap in sitemaps:
        urls = get_urls_from_sitemap(sitemap)
        all_page_urls.extend(urls)

    print(f"[+] Total pages to scan: {len(all_page_urls)}")

    for page_url in all_page_urls:
        if page_url in scanned_urls:
            print(f"[✓] Skipping already scanned: {page_url}")
            continue

        print(f"\n[>] Scanning page: {page_url}")
        links = extract_links_from_entry_container(page_url)
        print(f"    → Found {len(links)} links in .entry-container content.")

        for link in links:
            source = "Internal" if is_internal(link) else "External"

            if (source == "Internal" and not CHECK_INTERNAL_LINKS) or (source == "External" and not CHECK_EXTERNAL_LINKS):
                print(f"     ↳ Skipping {source} link → {link}")
                continue

            print(f"     ↳ Checking {source} link → {link}")
            status = check_link(link)


            if status == 200:
                print(f"        ✓ {status} OK")
            elif status:
                print(f"        ✗ {status} Issue")
                log_broken_link(page_url, link, status, source)
            else:
                print(f"        ✗ No response")
                log_broken_link(page_url, link, "No response", source)

            delay = INTERNAL_DELAY if source == "Internal" else EXTERNAL_DELAY
            time.sleep(delay)

        save_progress(page_url)
        print(f"    ✔ Done scanning page. Waiting {WAIT_BETWEEN_PAGES} seconds...\n")
        time.sleep(WAIT_BETWEEN_PAGES)

    print("\n[✔] All done! Broken links saved to broken_links_report.txt")
    input("\nPress Enter to exit...")

if __name__ == "__main__":
    main()
