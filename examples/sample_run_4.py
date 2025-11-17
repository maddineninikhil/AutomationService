from urllib.parse import urljoin
from playwright.sync_api import sync_playwright
import requests
import json
import re

def clean_ollama_response(text):
    # Try to extract URL inside markdown link [text](url)
    match = re.search(r'\((https?://[^\s]+)\)', text)
    if match:
        return match.group(1)
    # Otherwise, extract any URL in the text
    match = re.search(r'(https?://[^\s]+)', text)
    if match:
        return match.group(1)
    # Fallback, return original cleaned string
    return text.strip()


URL = "https://www.uscis.gov/i-765"
OLLAMA_URL = "http://localhost:11434/api/generate"

def ask_ollama(links):
    prompt = (
        "Here is a list of PDF URLs found on the page:\n\n"
        + "\n".join(f"- {link}" for link in links) +
        "\n\nWhich ONE link should I click to download the main form PDF? Respond ONLY with the URL."
    )

    response = requests.post(
        OLLAMA_URL,
        json={"model": "llama3", "prompt": prompt},
        stream=True,
    )

    full_text = ""

    for line in response.iter_lines():
        if not line:
            continue
        try:
            data = json.loads(line.decode("utf-8"))
        except json.JSONDecodeError:
            continue
        if "response" in data:
            full_text += data["response"]

    return full_text.strip()

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    context = browser.new_context(accept_downloads=True)
    page = context.new_page()

    page.goto(URL)

    anchors = page.query_selector_all('a[href*=".pdf"]')
    if not anchors:
        raise RuntimeError("No PDF links found on the page")

    pdf_links = [urljoin(URL, a.get_attribute("href")) for a in anchors if a.get_attribute("href")]
    print("\nPDF LINKS FOUND:")
    for link in pdf_links:
        print(" -", link)

    chosen_link_raw = ask_ollama(pdf_links)
    chosen_link = clean_ollama_response(chosen_link_raw)
    print("\nOllama chose:", chosen_link)

    target_anchor = None
    for a in anchors:
        href = urljoin(URL, a.get_attribute("href"))
        if href == chosen_link:
            target_anchor = a
            break

    if not target_anchor:
        raise RuntimeError("Ollama returned a link that was not found on the page")

    # Add download attribute to force download
    page.eval_on_selector(f'a[href="{chosen_link}"]', "el => el.setAttribute('download', '')")

    with page.expect_download() as dl:
        target_anchor.click()

    download = dl.value
    print(f"Downloaded file saved to: {download.path()}")

    browser.close()
