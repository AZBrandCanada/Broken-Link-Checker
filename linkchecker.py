import requests
import time
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

SITEMAP_INDEX = "https://example.com/sitemap_index.xml"
OUTPUT_FILE = "broken_links_report.txt"
WAIT_BETWEEN_REQUESTS = 3

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


def main():
    print("[*] Starting Broken Link Checker (inside .entry-container content)...\n")

    sitemaps = get_sitemaps(SITEMAP_INDEX)
    if not sitemaps:
        print("[X] No sitemaps found.")
        input("\nPress Enter to exit...")
        return

    print(f"[+] Found {len(sitemaps)} sitemaps.")
    all_page_urls = []
    for sitemap in sitemaps:
        print(f"\n[-] Parsing sitemap: {sitemap}")
        urls = get_urls_from_sitemap(sitemap)
        print(f"    → Found {len(urls)} URLs in sitemap.")
        all_page_urls.extend(urls)

    print(f"\n[+] Total pages to scan: {len(all_page_urls)}")

    # clear output file at start
    open(OUTPUT_FILE, "w").close()

    for page_url in all_page_urls:
        print(f"\n[>] Scanning page: {page_url}")
        links = extract_links_from_entry_container(page_url)
        print(f"    → Found {len(links)} links in .entry-container content.")

        for link in links:
            source = "Internal" if is_internal(link) else "External"
            print(f"     ↳ Checking {source} link on {page_url} → {link}")

            status = check_link(link)

            if status == 200:
                print(f"        ✓ {status} OK")
            elif status:
                print(f"        ✗ {status} Issue")
                log_broken_link(page_url, link, status, source)
            else:
                print(f"        ✗ No response")
                log_broken_link(page_url, link, "No response", source)

        print(f"    ✔ Done scanning page. Waiting {WAIT_BETWEEN_REQUESTS} seconds...\n")
        time.sleep(WAIT_BETWEEN_REQUESTS)

    print("\n[✔] All done! Broken links saved to broken_links_report.txt")
    input("\nPress Enter to exit...")


if __name__ == "__main__":
    main()
