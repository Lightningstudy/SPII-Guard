#!/usr/bin/env python3
"""SPII-Guard demo: detect sensitive information in a receipt image.

Headless, cross-platform version of ``src/SPII_Guard.py``. Runs the same
pipeline (Tesseract OCR -> regular expressions + spaCy NER) and writes an
image with red boxes around the detected sensitive words instead of opening
GUI windows.

Usage:
    python spii_guard_demo.py                      # runs on the bundled sample receipt
    python spii_guard_demo.py --image my_receipt.jpg
    python spii_guard_demo.py --image my_receipt.jpg --out-dir results --save-ocr

Requirements: Tesseract OCR on the PATH (or --tesseract-cmd / $TESSERACT_CMD),
plus the packages in requirements.txt and the spaCy model en_core_web_sm.
"""
import argparse
import os
import re
import shutil
import sys

import cv2
import pytesseract
from pytesseract import Output

HERE = os.path.dirname(os.path.abspath(__file__))
SAMPLE_IMAGE = os.path.join(HERE, "images", "originalReceipt.png")

# Words that spaCy tends to tag as PERSON on receipts but are not people.
NOT_NAMES = {
    "SAM'S", "ACTIVATION", "sam", "Sam's", "Ross", "Cashier", "Reg", "Shk",
    "Salesperson", "Walmart", "Costco", "Amazon", "Aldi", "Home Depot", "Target",
    "Walgreens", "Best Buy", "Dollar general", "IKEA", "Kroger", "7-Eleven",
    "Macy's", "Verizon", "CVS", "Lowe's", "Albertsons", "Apple",
    "Royal Ahold Delhaize USA", "Publix", "TJX", "Dollar General", "H.E. Butt",
    "Dollar Tree", "Ace Hardware", "At&t", "AT&T", "Meijer", "BJ's", "Wakefern",
    "Rite Aid", "Kohl's", "Nordstrom", "Tractor Supply", "Gap", "GAP", "GAp",
    "gap", "Dillard's", "McDonald", "Starbucks", "Subway", "Taco Bell",
    "Chick-fil-A", "Wendy's", "Burger King", "Dunkin", "Domino's", "Panera Bread",
    "Pizza Hut", "Chipotle", "Sonic", "KFC", "kfc", "Arby's", "Little Caesars",
    "Dairy Queen", "Jack in the Box", "Panda Express", "Panda", "panda",
    "Popeyes", "popeyes", "Papa John's", "Whataburger", "Jimmy John's",
    "Hardee's", "Zaxby's", "Five Guys", "five guys", "Culver's", "Carl's Jr",
    "Bojangles", "Wingstop", "Cane's", "COUNTER-Eat", "Raising Cane's",
}


def resolve_tesseract(cmd_arg):
    """Pick the Tesseract binary: CLI flag, env var, PATH, then common Windows paths."""
    candidates = [
        cmd_arg,
        os.environ.get("TESSERACT_CMD"),
        shutil.which("tesseract"),
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    ]
    for c in candidates:
        if c and os.path.isfile(c):
            return c
    sys.exit(
        "Tesseract OCR was not found. Install it (apt install tesseract-ocr, "
        "brew install tesseract, or the Windows installer from "
        "https://github.com/UB-Mannheim/tesseract/wiki) and either put it on the "
        "PATH or pass --tesseract-cmd /path/to/tesseract."
    )


def load_ner():
    import spacy
    try:
        return spacy.load("en_core_web_sm")
    except OSError:
        sys.exit(
            "spaCy model en_core_web_sm is missing. Install it with:\n"
            "    python -m spacy download en_core_web_sm"
        )


def ocr_words(image_bgr):
    """Run Tesseract and return one dict per word with its bounding box."""
    rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
    results = pytesseract.image_to_data(
        rgb, config="--oem 3 --psm 6", output_type=Output.DICT
    )
    words = []
    for i, text in enumerate(results["text"]):
        words.append({
            "text": text,
            "box": (
                (results["left"][i], results["top"][i]),
                (results["left"][i] + results["width"][i],
                 results["top"][i] + results["height"][i]),
            ),
            "conf": float(results["conf"][i]),
        })
    return words


def find_sensitive(words, ner):
    """Apply the SPII-Guard rules. Returns a list of (word, reason) hits.

    Rules are the same as in src/SPII_Guard.py:
      - masked card numbers such as XXXX1234 / xx 1234 / KK1234
      - dates containing a slash, times containing a colon
      - PERSON entities from spaCy, minus a list of store/role words
    """
    hits = []

    def add(word, reason):
        if word["text"].strip():
            hits.append((word, reason))

    for idx, w in enumerate(words):
        t = w["text"]

        masked_upper = re.search(r"[X][X]..[0-9][0-9][0-9]", t)
        masked_lower = re.findall(r"[x][x]", t)
        masked_kk = re.findall(r"[K][K]", t)
        trailing_digits = re.findall(r"...[0-9][0-9]", t)

        if masked_upper:
            add(w, "last 4 digits")
        if masked_lower:
            add(w, "last 4 digits")
            # "xx" followed by the digits in the next OCR token
            if not trailing_digits and idx + 1 < len(words):
                nxt = words[idx + 1]
                if re.search(r"^[0-9]..[0-9]$", nxt["text"]):
                    add(nxt, "last 4 digits")
        if masked_kk:
            add(w, "last 4 digits")

        if re.findall(r"^[0-9].+/.[0-9]$", t) or re.findall(r"[0-9].+/.[0-9]", t):
            add(w, "date")
        if re.findall(r"[0-9].+:.[0-9]", t) or re.findall(r"[0-9]+:[0-9][0-9]", t):
            add(w, "time")

        for ent in ner(t).ents:
            if ent.label_ == "PERSON":
                if ent.text in NOT_NAMES:
                    break
                add(w, "person")

    # de-duplicate while keeping order
    seen = set()
    unique = []
    for w, reason in hits:
        key = (w["box"], reason)
        if key not in seen:
            seen.add(key)
            unique.append((w, reason))
    return unique


def draw_boxes(image_bgr, boxes, color, thickness=2):
    out = image_bgr.copy()
    for (p1, p2) in boxes:
        cv2.rectangle(out, p1, p2, color, thickness)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("-i", "--image", default=SAMPLE_IMAGE,
                    help="receipt image to scan (default: bundled sample)")
    ap.add_argument("-o", "--out-dir", default="output",
                    help="where to write result images (default: ./output)")
    ap.add_argument("--save-ocr", action="store_true",
                    help="also save an image with every OCR word boxed in blue")
    ap.add_argument("--tesseract-cmd", default=None,
                    help="path to the tesseract binary if it is not on the PATH")
    args = ap.parse_args()

    pytesseract.pytesseract.tesseract_cmd = resolve_tesseract(args.tesseract_cmd)

    if not os.path.isfile(args.image):
        sys.exit(f"Image not found: {args.image}")
    image = cv2.imread(args.image)
    if image is None:
        sys.exit(f"Could not read image: {args.image}")

    print(f"Image:     {args.image}")
    print(f"Tesseract: {pytesseract.pytesseract.tesseract_cmd}")
    print("Running OCR ...")
    words = ocr_words(image)
    non_empty = [w for w in words if w["text"].strip()]
    print(f"OCR found {len(non_empty)} words/numbers.")

    print("Loading spaCy NER ...")
    ner = load_ner()
    hits = find_sensitive(words, ner)

    print(f"\nSensitive items detected: {len(hits)}")
    for w, reason in hits:
        (x1, y1), (x2, y2) = w["box"]
        print(f"  [{reason:13}] {w['text']!r:24} box=({x1},{y1})-({x2},{y2})")

    os.makedirs(args.out_dir, exist_ok=True)
    stem = os.path.splitext(os.path.basename(args.image))[0]

    detect_path = os.path.join(args.out_dir, f"{stem}_detect.jpg")
    cv2.imwrite(detect_path, draw_boxes(image, [w["box"] for w, _ in hits], (0, 0, 255)))
    print(f"\nWrote {detect_path}")

    if args.save_ocr:
        ocr_path = os.path.join(args.out_dir, f"{stem}_ocr.jpg")
        cv2.imwrite(ocr_path, draw_boxes(image, [w["box"] for w in non_empty], (255, 0, 0)))
        print(f"Wrote {ocr_path}")


if __name__ == "__main__":
    main()
