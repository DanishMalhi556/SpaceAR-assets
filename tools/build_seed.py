"""Builds backend/data/catalog_seed.json from the processed assets.

    python -I build_seed.py <work dir> <backend dir> <cdn tag>
"""

import hashlib
import json
import re
import sys
from pathlib import Path

work, backend, tag = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3]
sys.path.insert(0, str(backend))
from models.catalog import FurnitureItem  # noqa: E402
from services.recommender import item_kind  # noqa: E402
from services.vision.style import STYLES  # noqa: E402

CDN = f"https://cdn.jsdelivr.net/gh/DanishMalhi556/SpaceAR-assets@{tag}"
M_TO_IN = 39.3701

# Every item needs at least one style the room analyser can return.
STYLE_OVERRIDES = {
    "chair-farm-arm": ["rustic", "boho"],
    "table-side-mini": ["rustic", "scandinavian"],
    "table-night-painted": ["rustic", "boho"],
    "table-small-wood": ["rustic", "scandinavian"],
    "wardrobe-painted": ["rustic", "boho"],
    "wardrobe-sideboard-painted": ["rustic", "boho"],
    "chair-gallinera": ["traditional", "classic", "rustic"],
    "table-gallinera": ["traditional", "classic", "rustic"],
}
BASE_PRICE = {
    "Sofa": 1600, "Armchair": 750, "Chair": 260, "Dining Chair": 240, "Coffee Table": 650, "Side Table": 280,
    "Bedside Table": 320, "Dining Table": 1200, "Table": 480, "Bed": 1500, "Wardrobe": 1400, "Dresser": 950,
    "Sideboard": 1100, "Bookcase": 520, "Ceiling Light": 380, "Lamp": 160, "Floor Lamp": 300,
}
STYLE_FACTOR = {
    "luxury": 1.5, "classic": 1.2, "traditional": 1.15, "mid-century": 1.15, "modern": 1.1, "japandi": 1.1,
    "contemporary": 1.05, "scandinavian": 1.0, "minimalist": 1.0, "boho": 0.9, "industrial": 0.9, "rustic": 0.85,
}
KIND_WORDS = {  # description wording per type (must not change the type)
    "Sofa": "sofa", "Armchair": "armchair", "Chair": "chair", "Dining Chair": "dining chair",
    "Coffee Table": "coffee table", "Side Table": "side table", "Bedside Table": "bedside table",
    "Dining Table": "dining table", "Table": "table", "Bed": "bed", "Wardrobe": "storage cabinet",
    "Dresser": "dresser", "Sideboard": "sideboard", "Bookcase": "bookcase", "Ceiling Light": "ceiling light",
    "Lamp": "lamp", "Floor Lamp": "floor lamp",
}

items = json.loads((work / "items.json").read_text(encoding="utf-8"))
dims = json.loads((work / "models_report.json").read_text(encoding="utf-8"))
colors = json.loads((work / "colors.json").read_text(encoding="utf-8"))
sources = json.loads((work / "sources.json").read_text(encoding="utf-8"))

LICENCE_URL = {
    "CC0": "https://creativecommons.org/publicdomain/zero/1.0/",
    "CC-BY 4.0": "https://creativecommons.org/licenses/by/4.0/",
}


def credit_for(s: dict) -> dict:
    """Same author wording as LICENSES.md (write_licenses.py)."""
    if s.get("authors") is not None:  # Poly Haven
        author = ", ".join(s["authors"]) or s["source"]
    else:
        people = []
        for l in s.get("legal", []):
            who = re.sub(r"^(Copyright|©)\s*\d{4}\s*", "", l.get("owner") or l.get("artist") or "")
            if l.get("artist") and l.get("artist") != who:
                who += f" ({l['artist']})"
            if who and who not in people:
                people.append(who)
        author = "; ".join(people) or s.get("credit", "")
    licence = s["licence"]
    # A mixed licence ("CC0 + CC-BY 4.0") links to the stricter one.
    url = LICENCE_URL["CC-BY 4.0"] if "BY" in licence else LICENCE_URL["CC0"]
    return {"title": s["title"], "author": author, "licence": licence, "licence_url": url, "source_url": s["url"]}

seed = []
for it in items:
    cid = it["id"]
    styles = STYLE_OVERRIDES.get(cid, it["styles"])
    assert any(s in STYLES for s in styles), f"{cid}: no analyser style in {styles}"
    d = dims[cid]
    w, h, dp = (round(d[k] * M_TO_IN, 1) for k in ("w_m", "h_m", "d_m"))
    probe = FurnitureItem(id=cid, name=it["name"], category=it["category"], price=0)
    kind = item_kind(probe)
    factor = max(STYLE_FACTOR.get(s, 1.0) for s in styles)
    if "chandelier" in it["name"].lower():
        factor *= 2.5
    jitter = 0.9 + (int(hashlib.md5(cid.encode()).hexdigest(), 16) % 21) / 100  # 0.90-1.10, stable
    price = round(BASE_PRICE[kind] * factor * jitter / 10) * 10
    style_word = styles[0].replace("-", " ").title().replace("Mid Century", "Mid-century")
    description = (f"{style_word} {KIND_WORDS[kind]}, {round(d['w_m'] * 100)} × {round(d['d_m'] * 100)} × "
                   f"{round(d['h_m'] * 100)} cm (W × D × H), true to scale in AR.")
    item = FurnitureItem(
        id=cid, name=it["name"], category=it["category"], price=price,
        width_in=w, depth_in=dp, height_in=h, tag="AR ready", description=description,
        style_tags=styles, colors=colors[cid],
        image_url=f"{CDN}/images/{cid}.webp", model_url=f"{CDN}/models/{cid}.glb",
        credit=credit_for(sources[cid]),
    )
    assert item_kind(item) == kind, f"{cid}: description changed the type"
    row = item.model_dump(exclude_none=True)
    row["price"] = int(row["price"])  # whole dollars, as in the original file
    seed.append(row)

out = backend / "data" / "catalog_seed.json"
out.write_text("[\n" + ",\n".join("  " + json.dumps(s, ensure_ascii=False) for s in seed) + "\n]\n",
               encoding="utf-8")  # one item per line, like the original file
print(f"{len(seed)} items -> {out}")
from collections import Counter  # noqa: E402
print(Counter(item_kind(FurnitureItem(**s)) for s in seed))
