import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import hashlib
import os
import json
import io
import pikepdf   # <-- added

FORM_URL = "https://www.uscis.gov/i-765"
HASH_FILE = "i-765-hash.json"
PDF_FILE = "i-765-latest.pdf"

# --- Step 1: Fetch canonical USCIS page ---
page = requests.get(FORM_URL)
soup = BeautifulSoup(page.text, "html.parser")

# --- Step 2: Extract PDF link ---
pdf_link = soup.select_one('a[href$=".pdf"]')["href"]
pdf_url = urljoin(FORM_URL, pdf_link)

# --- Step 3: Download current PDF ---
pdf_data = requests.get(pdf_url).content

# --- NEW: Metadata extraction with pikepdf ---
print("\nPDF Metadata:")
try:
    pdf = pikepdf.open(io.BytesIO(pdf_data))
    metadata = pdf.docinfo
    for key, value in metadata.items():
        print(f"  {key}: {value}")
except Exception as e:
    print("Could not read PDF metadata:", e)

# Compute hash of current PDF
new_hash = hashlib.sha256(pdf_data).hexdigest()

# --- Step 4: Load previous hash (if exists) ---
if os.path.exists(HASH_FILE):
    with open(HASH_FILE, "r") as f:
        old_hash = json.load(f).get("hash")
else:
    old_hash = None

# --- Step 5: Compare hashes ---
changed = (old_hash != new_hash)

if changed:
    print("\n⚠️ Form I-765 has changed!")
    # Save updated PDF
    with open(PDF_FILE, "wb") as f:
        f.write(pdf_data)
    # Save new hash
    with open(HASH_FILE, "w") as f:
        json.dump({"hash": new_hash}, f, indent=2)
else:
    print("\nNo change detected.")

# Output useful info
print("PDF URL:", pdf_url)
print("Changed:", changed)