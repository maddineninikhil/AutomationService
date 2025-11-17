"""
Robust, SOLID-compliant, Object-Oriented I-765 Monitor
----------------------------------------------------
This version restructures the system into well-defined classes following:
- **Single Responsibility Principle** (each class does one thing)
- **Open/Closed Principle** (easy to extend behaviors without modifying core classes)
- **Liskov Substitution Principle** (strategy interfaces for fetchers, extractors, diff engines)
- **Interface Segregation Principle** (small, purpose-specific interfaces)
- **Dependency Inversion Principle** (high-level code depends on abstractions, not concretions)

The architecture is broken into:

FETCHING LAYER
  - HttpFetcher
  - PlaywrightFetcher (fallback)
  - PdfLocator (uses multiple strategies)

EXTRACTION LAYER
  - PdfMetadataExtractor
  - PdfTextExtractor
  - PdfFieldExtractor

DIFF LAYER
  - MetadataDiff
  - HashDiff
  - TextDiff
  - FieldDiff

STORAGE LAYER
  - SnapshotRepository
  - StateRepository

APPLICATION LAYER
  - ChangeDetector (multi-signal detection logic)
  - MonitorOrchestrator (ties everything together)

NOTIFICATION LAYER
  - Notifier (Slack/email/webhook)

"""

import os
import io
import json
import time
import difflib
import hashlib
import logging
import requests
import datetime
from typing import Optional, Dict, Tuple
from bs4 import BeautifulSoup
from urllib.parse import urljoin

import pikepdf
import pdfplumber

# Optional dependencies
try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except Exception:
    PLAYWRIGHT_AVAILABLE = False

# ----------------------------------------------------
# CONFIG
# ----------------------------------------------------
class Config:
    FORM_URL = "https://www.uscis.gov/i-765"
    BASE_DIR = "./i765_monitor"
    SNAPSHOT_DIR = "snapshots"
    STATE_FILE = "state.json"
    USER_AGENT = "i765-monitor/2.0 (+https://example.com)"
    RETRIES = 3
    BACKOFF = 2
    TIMEOUT = 30
    PLAYWRIGHT = True
    PLAYWRIGHT_TIMEOUT_MS = 45000
    WEBHOOK_URL = os.getenv("WEBHOOK_URL", "")


# ----------------------------------------------------
# FETCHING LAYER
# ----------------------------------------------------
class IFetcher:
    def fetch(self, url: str) -> Optional[str]:
        raise NotImplementedError


class HttpFetcher(IFetcher):
    def fetch(self, url: str) -> Optional[str]:
        headers = {"User-Agent": Config.USER_AGENT}
        for attempt in range(1, Config.RETRIES + 1):
            try:
                r = requests.get(url, headers=headers, timeout=Config.TIMEOUT)
                r.raise_for_status()
                return r.text
            except Exception as e:
                if attempt == Config.RETRIES:
                    raise
                time.sleep(Config.BACKOFF ** attempt)
        return None


class PlaywrightFetcher(IFetcher):
    def fetch(self, url: str) -> Optional[str]:
        if not PLAYWRIGHT_AVAILABLE or not Config.PLAYWRIGHT:
            return None
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch()
                page = browser.new_page(user_agent=Config.USER_AGENT)
                page.goto(url, timeout=Config.PLAYWRIGHT_TIMEOUT_MS)
                content = page.content()
                browser.close()
                return content
        except Exception:
            return None


class PdfLocator:
    """Uses multiple strategies to discover the PDF URL."""
    def __init__(self, fetchers):
        self.fetchers = fetchers

    def find_pdf_url(self, url: str) -> Optional[str]:
        for fetcher in self.fetchers:
            html = fetcher.fetch(url)
            if html:
                pdf_url = self._extract_pdf_from_html(html, url)
                if pdf_url:
                    return pdf_url
        return None

    @staticmethod
    def _extract_pdf_from_html(html: str, base_url: str) -> Optional[str]:
        soup = BeautifulSoup(html, "html.parser")

        # direct selector
        a = soup.select_one('a[href$=".pdf"]')
        if a:
            return urljoin(base_url, a["href"])

        # heuristic scan
        for link in soup.find_all("a", href=True):
            href = link["href"]
            if ".pdf" in href.lower():
                return urljoin(base_url, href)

        return None


# ----------------------------------------------------
# EXTRACTION LAYER
# ----------------------------------------------------
class PdfMetadataExtractor:
    def extract(self, pdf_bytes: bytes) -> Dict:
        out = {}
        try:
            pdf = pikepdf.open(io.BytesIO(pdf_bytes))
            for k, v in pdf.docinfo.items():
                out[str(k)] = str(v)
        except Exception:
            pass
        return out


class PdfTextExtractor:
    def extract(self, pdf_bytes: bytes) -> str:
        try:
            with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
                pages = []
                for page in pdf.pages:
                    pages.append(page.extract_text() or "")
                return "".join(pages)
        except Exception:
            return ""


class PdfFieldExtractor:
    def extract(self, pdf_bytes: bytes) -> Dict:
        fields = {}
        try:
            pdf = pikepdf.open(io.BytesIO(pdf_bytes))
            if "/AcroForm" in pdf.root:
                for f in pdf.root.AcroForm.get("/Fields", []):
                    obj = f.get_object()
                    name = obj.get("/T")
                    if name:
                        fields[str(name)] = {
                            "raw": {k: str(v) for k, v in obj.items()}
                        }
        except Exception:
            pass
        return fields


# ----------------------------------------------------
# DIFF LAYER
# ----------------------------------------------------
class TextDiff:
    @staticmethod
    def diff(old: str, new: str) -> str:
        diff = difflib.unified_diff(old.splitlines(), new.splitlines(), lineterm="")
        return "".join(diff)


class FieldDiff:
    @staticmethod
    def diff(old: Dict, new: Dict) -> Dict:
        added = list(sorted(set(new) - set(old)))
        removed = list(sorted(set(old) - set(new)))
        modified = {}
        for key in set(old) & set(new):
            if json.dumps(old[key], sort_keys=True) != json.dumps(new[key], sort_keys=True):
                modified[key] = {"old": old[key], "new": new[key]}
        return {"added": added, "removed": removed, "modified": modified}


# ----------------------------------------------------
# STORAGE LAYER
# ----------------------------------------------------
class StateRepository:
    def __init__(self):
        self.path = os.path.join(Config.BASE_DIR, Config.STATE_FILE)
        os.makedirs(Config.BASE_DIR, exist_ok=True)

    def load(self) -> Dict:
        if os.path.exists(self.path):
            return json.load(open(self.path))
        return {}

    def save(self, state: Dict):
        json.dump(state, open(self.path, "w"), indent=2)


class SnapshotRepository:
    def __init__(self):
        self.root = os.path.join(Config.BASE_DIR, Config.SNAPSHOT_DIR)
        os.makedirs(self.root, exist_ok=True)

    def save_snapshot(self, name: str, pdf_bytes: bytes, text: str, fields: Dict, metadata: Dict):
        folder = os.path.join(self.root, name)
        os.makedirs(folder, exist_ok=True)
        open(os.path.join(folder, "pdf.bin"), "wb").write(pdf_bytes)
        open(os.path.join(folder, "text.txt"), "w", encoding="utf-8").write(text)
        json.dump(fields, open(os.path.join(folder, "fields.json"), "w"), indent=2)
        json.dump(metadata, open(os.path.join(folder, "metadata.json"), "w"), indent=2)


# ----------------------------------------------------
# NOTIFICATION LAYER
# ----------------------------------------------------
class Notifier:
    def notify(self, message: str):
        print(message)
        if not Config.WEBHOOK_URL:
            return
        try:
            requests.post(Config.WEBHOOK_URL, json={"text": message})
        except Exception:
            pass


# ----------------------------------------------------
# APPLICATION LAYER
# ----------------------------------------------------
class ChangeDetector:
    def __init__(self):
        self.metadata_extractor = PdfMetadataExtractor()
        self.text_extractor = PdfTextExtractor()
        self.field_extractor = PdfFieldExtractor()

    def detect(self, prev_state: Dict, pdf_bytes: bytes) -> Tuple[bool, Dict]:
        new_hash = hashlib.sha256(pdf_bytes).hexdigest()
        metadata = self.metadata_extractor.extract(pdf_bytes)
        text = self.text_extractor.extract(pdf_bytes)
        fields = self.field_extractor.extract(pdf_bytes)

        changed = False
        reasons = []

        # metadata first
        if prev_state.get("metadata", {}).get("/ModDate") != metadata.get("/ModDate"):
            changed = True
            reasons.append("ModDate change")

        # hash fallback
        if prev_state.get("hash") != new_hash:
            changed = True
            reasons.append("hash change")

        diff_data = {}
        if changed:
            old_text = prev_state.get("text", "")
            diff_data["text_diff"] = TextDiff.diff(old_text, text)
            old_fields = prev_state.get("fields", {})
            diff_data["field_diff"] = FieldDiff.diff(old_fields, fields)

        return changed, {
            "hash": new_hash,
            "metadata": metadata,
            "text": text,
            "fields": fields,
            "reasons": reasons,
            "diff": diff_data,
        }


class MonitorOrchestrator:
    def __init__(self):
        self.state_repo = StateRepository()
        self.snap_repo = SnapshotRepository()
        self.detector = ChangeDetector()
        self.locator = PdfLocator(fetchers=[HttpFetcher(), PlaywrightFetcher()])
        self.notifier = Notifier()

    def run(self):
        url = Config.FORM_URL
        pdf_url = self.locator.find_pdf_url(url)
        if not pdf_url:
            self.notifier.notify("PDF not found")
            return

        pdf_bytes = requests.get(pdf_url, headers={"User-Agent": Config.USER_AGENT}).content
        prev_state = self.state_repo.load()

        changed, data = self.detector.detect(prev_state, pdf_bytes)
        if not changed:
            print("No change detected")
            return

        # Save snapshot
        name = datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
        self.snap_repo.save_snapshot(name, pdf_bytes, data["text"], data["fields"], data["metadata"])

        # Save state
        self.state_repo.save(data)

        # notify
        summary = "I-765 Updated: " + ", ".join(data["reasons"])
        self.notifier.notify(summary)


# ----------------------------------------------------
if __name__ == "__main__":
    MonitorOrchestrator().run()
