"""Check that committed daily artifacts and generated publication files agree."""

from __future__ import annotations

import glob
import json
import re
import sys
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
DOCS = ROOT / "docs"
OUTPUT = ROOT / "output"
ATOM = "{http://www.w3.org/2005/Atom}"


def main() -> int:
    reports = sorted(OUTPUT.glob("discovery-*.md"), reverse=True)
    if not reports:
        print("build parity: no discovery reports")
        return 1
    latest = re.search(r"discovery-(\d{4}-\d{2}-\d{2})\.md$", reports[0].name).group(1)
    json_path = DATA / f"discovery-{latest}.json"
    if not json_path.exists():
        print(f"build parity: missing {json_path}")
        return 1
    html = (DOCS / "index.html").read_text(encoding="utf-8")
    if f'data-date="{latest}"' not in html or f'<option value="{latest}" selected>' not in html:
        print(f"build parity: index does not select {latest}")
        return 1
    root = ET.parse(DOCS / "feed.xml").getroot()
    updated = root.findtext(f"{ATOM}updated") or ""
    if not updated.startswith(latest + "T"):
        print(f"build parity: feed updated={updated!r}, expected date {latest}")
        return 1
    sitemap = (DOCS / "sitemap.xml").read_text(encoding="utf-8")
    if f"<lastmod>{latest}</lastmod>" not in sitemap:
        print(f"build parity: sitemap does not contain {latest}")
        return 1
    print(f"build parity: report={latest} index=ok feed=ok sitemap=ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
