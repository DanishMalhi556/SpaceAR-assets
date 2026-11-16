"""Downloads the raw source files for every item in items.json.

    python download_assets.py <work dir>

Poly Haven: 1K glTF + its textures, the transparent product render, and the
asset info (authors). Khronos: the GLB (or glTF + files), the large
screenshot, and metadata.json. Writes <work>/raw/<id>/... and
<work>/sources.json (source URL, licence, authors, download date).
Re-running skips files that already exist.
"""

import datetime
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

UA = {"User-Agent": "asset-download-script/1.0"}
KH = "https://raw.githubusercontent.com/KhronosGroup/glTF-Sample-Assets/main/Models"


def get(url: str) -> bytes:
    for attempt in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=120) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code == 404 or attempt == 2:
                raise
            time.sleep(2)
        except Exception:
            if attempt == 2:
                raise
            time.sleep(2)


def save(url: str, dest: Path) -> None:
    if dest.exists() and dest.stat().st_size > 0:
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(get(url))


def main() -> None:
    work = Path(sys.argv[1])
    items = json.loads((work / "items.json").read_text(encoding="utf-8"))
    today = datetime.date.today().isoformat()
    sources = {}
    for n, it in enumerate(items, 1):
        cid, src = it["id"], it["src"]
        out = work / "raw" / cid
        if it["source"] == "polyhaven":
            info = json.loads(get(f"https://api.polyhaven.com/info/{src}"))
            files = json.loads(get(f"https://api.polyhaven.com/files/{src}"))
            entry = files["gltf"]["1k"]["gltf"]
            save(entry["url"], out / "model" / Path(urllib.parse.urlparse(entry["url"]).path).name)
            for rel, f in entry.get("include", {}).items():
                save(f["url"], out / "model" / rel)
            save(f"https://cdn.polyhaven.com/asset_img/primary/{src}.png?width=1200", out / "render.png")
            sources[cid] = {
                "source": "Poly Haven", "title": info["name"], "url": f"https://polyhaven.com/a/{src}",
                "authors": sorted(info.get("authors", {})), "licence": "CC0", "downloaded": today,
            }
        else:
            meta = json.loads(get(f"{KH}/{src}/metadata.json"))
            if src == "StainedGlassLamp":
                base = f"{KH}/{src}/glTF-JPG-PNG"
                gltf_name = f"{src}.gltf"
                gltf = json.loads(get(f"{base}/{gltf_name}"))
                save(f"{base}/{gltf_name}", out / "model" / gltf_name)
                for ref in gltf.get("buffers", []) + gltf.get("images", []):
                    if "uri" in ref and not ref["uri"].startswith("data:"):
                        save(f"{base}/{urllib.parse.quote(ref['uri'])}", out / "model" / urllib.parse.unquote(ref["uri"]))
            else:
                save(f"{KH}/{src}/glTF-Binary/{src}.glb", out / "model" / f"{src}.glb")
            if not (out / "render.jpg").exists():  # names vary between models
                for name in ("screenshot_large.jpg", "screenshot-large.jpg", "screenshot_Large.jpg",
                             "screenshot.jpg", "screenshot.png"):
                    try:
                        save(f"{KH}/{src}/screenshot/{name}", out / "render.jpg")
                        break
                    except urllib.error.HTTPError:
                        continue
            sources[cid] = {
                "source": "Khronos glTF-Sample-Assets", "title": src,
                "url": f"https://github.com/KhronosGroup/glTF-Sample-Assets/tree/main/Models/{src}",
                "legal": [{k: l.get(k) for k in ("owner", "artist", "license", "what", "year") if l.get(k)}
                          for l in meta.get("legal", [])],
                "licence": it["licence"], "credit": it["credit"], "downloaded": today,
            }
        print(f"[{n}/{len(items)}] {cid}", flush=True)
    (work / "sources.json").write_text(json.dumps(sources, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
