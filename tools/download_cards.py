#!/usr/bin/env python3
"""
Download all 40 Napoletane card images from Wikimedia Commons.
Files: 01-10 = Denari, 11-20 = Coppe, 21-30 = Spade, 31-40 = Bastoni

Usage: python3 tools/download_cards.py [output_dir]
Default output_dir: reference_cards/
"""

import os
import sys
import json
import hashlib
import urllib.request
import time

OUTPUT_DIR = sys.argv[1] if len(sys.argv) > 1 else 'reference_cards'

# All 40 filenames as they appear on Wikimedia Commons
FILENAMES = [
    "01 Asso di denari.jpg",
    "02 Due di denari.jpg",
    "03 Tre di denari.jpg",
    "04 Quattro di denari.jpg",
    "05 Cinque di denari.jpg",
    "06 Sei di denari.jpg",
    "07 Sette di denari.jpg",
    "08 Otto di denari.jpg",
    "09 Nove di denari.jpg",
    "10 Dieci di denari.jpg",
    "11 Asso di coppe.jpg",
    "12 Due di coppe.jpg",
    "13 Tre di coppe.jpg",
    "14 Quattro di coppe.jpg",
    "15 Cinque di coppe.jpg",
    "16 Sei di coppe.jpg",
    "17 Sette di coppe.jpg",
    "18 Otto di coppe.jpg",
    "19 Nove di coppe.jpg",
    "20 Dieci di coppe.jpg",
    "21 Asso di spade.jpg",
    "22 Due di spade.jpg",
    "23 Tre di spade.jpg",
    "24 Quattro di spade.jpg",
    "25 Cinque di spade.jpg",
    "26 Sei di spade.jpg",
    "27 Sette di spade.jpg",
    "28 Otto di spade.jpg",
    "29 Nove di spade.jpg",
    "30 Dieci di spade.jpg",
    "31 Asso di bastoni.jpg",
    "32 Due di bastoni.jpg",
    "33 Tre di bastoni.jpg",
    "34 Quattro di bastoni.jpg",
    "35 Cinque di bastoni.jpg",
    "36 Sei di bastoni.jpg",
    "37 Sette di bastoni.jpg",
    "38 Otto di bastoni.jpg",
    "39 Nove di bastoni.jpg",
    "40 Dieci di Bastoni.jpg",  # Note: capital B on Commons
]


def wikimedia_thumb_url(filename, width=640):
    """Build a Wikimedia Commons thumbnail URL for a given filename."""
    # Wikimedia uses MD5 of the filename for the directory structure
    name = filename.replace(' ', '_')
    md5 = hashlib.md5(name.encode()).hexdigest()
    a, ab = md5[0], md5[:2]
    encoded = urllib.request.quote(name)
    return (
        f"https://upload.wikimedia.org/wikipedia/commons/thumb/{a}/{ab}/{encoded}"
        f"/{width}px-{encoded}"
    )


def wikimedia_full_url(filename):
    """Build a Wikimedia Commons full-resolution URL."""
    name = filename.replace(' ', '_')
    md5 = hashlib.md5(name.encode()).hexdigest()
    a, ab = md5[0], md5[:2]
    encoded = urllib.request.quote(name)
    return f"https://upload.wikimedia.org/wikipedia/commons/{a}/{ab}/{encoded}"


def download_file(url, dest_path):
    """Download a file with retry logic."""
    headers = {'User-Agent': 'ScopaSpectrum/1.0 (card game project)'}
    req = urllib.request.Request(url, headers=headers)
    for attempt in range(3):
        try:
            resp = urllib.request.urlopen(req, timeout=30)
            data = resp.read()
            with open(dest_path, 'wb') as f:
                f.write(data)
            return len(data)
        except Exception as e:
            if attempt < 2:
                time.sleep(1)
            else:
                raise


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    downloaded = 0
    skipped = 0
    failed = 0

    for filename in FILENAMES:
        # Local filename: replace spaces with underscores
        local_name = filename.replace(' ', '_')
        dest = os.path.join(OUTPUT_DIR, local_name)

        if os.path.exists(dest) and os.path.getsize(dest) > 1000:
            print(f"  SKIP {local_name} (already exists)")
            skipped += 1
            continue

        url = wikimedia_full_url(filename)
        print(f"  GET  {local_name} ...", end=' ', flush=True)

        try:
            size = download_file(url, dest)
            print(f"OK ({size:,} bytes)")
            downloaded += 1
            time.sleep(0.3)  # Be polite to Wikimedia
        except Exception as e:
            print(f"FAILED: {e}")
            failed += 1

    print(f"\nDone: {downloaded} downloaded, {skipped} skipped, {failed} failed")
    print(f"Total files in {OUTPUT_DIR}/: {len(os.listdir(OUTPUT_DIR))}")


if __name__ == '__main__':
    main()
