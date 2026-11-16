"""Writes LICENSES.md and sources/<id>.json in the assets repo.

    python -I write_licenses.py <work dir> <assets repo>
"""

import json
import sys
from pathlib import Path

work, assets = Path(sys.argv[1]), Path(sys.argv[2])
items = {i["id"]: i for i in json.loads((work / "items.json").read_text(encoding="utf-8"))}
sources = json.loads((work / "sources.json").read_text(encoding="utf-8"))

LICENCE_URL = {
    "CC0": "https://creativecommons.org/publicdomain/zero/1.0/",
    "CC-BY 4.0": "https://creativecommons.org/licenses/by/4.0/",
}
CHANGES = "Converted to GLB, re-centred, textures resized to ≤1024 px; product image cropped and converted to WebP."

rows = []
(assets / "sources").mkdir(exist_ok=True)
for cid in sorted(items):
    s = sources[cid]
    files = f"`models/{cid}.glb`, `images/{cid}.webp`"
    if s["source"] == "Poly Haven":
        author = ", ".join(s["authors"]) or "Poly Haven"
        lic = "[CC0](" + LICENCE_URL["CC0"] + ")"
    elif s["source"] == "Sketchfab":
        author = ", ".join(f"[{a}]({s['author_url']})" for a in s["authors"])
        lic = "[CC-BY 4.0](" + LICENCE_URL["CC-BY 4.0"] + ")"
    else:
        people = []
        for l in s.get("legal", []):
            who = l.get("owner") or l.get("artist") or ""
            if l.get("artist") and l.get("artist") != who:
                who += f" ({l['artist']})"
            if who and who not in people:
                people.append(who)
        author = "; ".join(people) or s["credit"]
        lic = " + ".join(
            f"[{part}]({LICENCE_URL.get(part, LICENCE_URL['CC-BY 4.0'])})" for part in s["licence"].split(" + ")
        )
    rows.append(f"| `{cid}` | {items[cid]['name']} | {files} | [{s['title']}]({s['url']}) | {author} | {lic} |")
    record = dict(s, id=cid, name=items[cid]["name"], changes=CHANGES)
    (assets / "sources" / f"{cid}.json").write_text(json.dumps(record, indent=1) + "\n", encoding="utf-8")

text = f"""# Asset licences and credits

Every file in `images/` and `models/` is listed here. Allowed licences:
**CC0**, **CC-BY** (credit required; this table is the credit), or **Own work**.

**Changes made to every asset:** {CHANGES}

`sources/<id>.json` records each asset's source, licence and download date.

| Item id | Catalog name | Files | Original asset | Author / owner | Licence |
|---|---|---|---|---|---|
""" + "\n".join(rows) + f"""

## Sources

- **Poly Haven** (https://polyhaven.com), CC0. Credit isn't required; the
  authors are listed anyway.
- **Khronos glTF Sample Assets**
  (https://github.com/KhronosGroup/glTF-Sample-Assets): models by Wayfair, LLC
  and Darmstadt Graphics Group (DGG), CC-BY 4.0 unless marked CC0. The
  product images for these items are the screenshots published with each
  model, under the same licence.
- **Sketchfab** (https://sketchfab.com): models published by their authors
  under CC Attribution (CC BY 4.0), checked at download time
  (`licence_as_reported` in `sources/<id>.json`). Some were rescaled to real
  size, turned to face forward, or had loose props removed. The product
  images for these items are renders of each model made for SpaceAR, under
  the same licence.
"""
(assets / "LICENSES.md").write_text(text, encoding="utf-8")
print(len(rows), "rows")
