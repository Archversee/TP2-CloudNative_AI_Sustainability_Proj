from playwright.sync_api import sync_playwright
import requests
import os
import re
from urllib.parse import urljoin

OUTPUT_DIR = "/data/raw_pdfs"

PDFS = [
    {
        "company": "SGX Group",
        "year": 2025,
        "url": "https://links.sgx.com/1.0.0/corporate-announcements/2J4PCEOQYA3WTBWP/859055_2025_SGX_Sustainability_Report.pdf"
    },
    {
        "company": "CLCT",
        "year": 2024,
        "url": "https://investor.clct.com.sg/isr.html"
    },
    {
        "company": "Singapore Shipping Corp",
        "year": 2025,
        "url": "https://singaporeshipping.listedcompany.com/sr.html"
    },
    {
        "company": "Genting Singapore",
        "year": 2025,
        "url": "https://gentingsingapore.listedcompany.com/sustainability-reports.html"
    },
    {
        "company": "Yokogawa",
        "year": 2025,
        "url": "https://www.yokogawa.com/sg/about/sustainability/report/"
    }
]


def safe_filename(company, year):
    return f"{company.replace(' ', '_')}_{year}.pdf"


def download_direct_pdf(url, path):
    r = requests.get(
        url,
        timeout=30,
        allow_redirects=True,
        headers={
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/pdf"
        }
    )
    r.raise_for_status()

    content_type = r.headers.get("Content-Type", "")
    if "pdf" not in content_type.lower():
        raise ValueError("URL did not resolve to a PDF")

    with open(path, "wb") as f:
        f.write(r.content)



def scrape_pdf_from_page(page, base_url):
    links = page.query_selector_all("a[href]")
    pdf_links = []

    for link in links:
        href = link.get_attribute("href")
        if href and ".pdf" in href.lower():
            pdf_links.append(urljoin(base_url, href))

    return pdf_links[0] if pdf_links else None


def is_pdf_url(url: str) -> bool:
    return ".pdf" in url.lower()

def run():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        )
        page = context.new_page()

        for pdf in PDFS:
            filename = safe_filename(pdf["company"], pdf["year"])
            path = os.path.join(OUTPUT_DIR, filename)

            try:
                print(f"Processing {pdf['company']}...")

                # Case 1: Direct PDF
                if pdf["url"].lower().endswith(".pdf"):
                    download_direct_pdf(pdf["url"], path)
                    print(f"Downloaded {path}")
                    continue

                # Case 2: Page → Playwright
                page.goto(pdf["url"], wait_until="networkidle", timeout=60000)

                pdf_link = scrape_pdf_from_page(page, pdf["url"])
                if not pdf_link:
                    print(f"No PDF found for {pdf['company']}")
                    continue

                if is_pdf_url(pdf_link):
                    download_direct_pdf(pdf_link, path)
                else:
                    page.goto(pdf_link, wait_until="networkidle")

                print(f"Downloaded {path}")

            except Exception as e:
                print(f"Failed for {pdf['company']}: {e}")

        browser.close()


if __name__ == "__main__":
    run()
