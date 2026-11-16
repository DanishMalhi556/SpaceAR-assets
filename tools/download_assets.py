"""Downloads the raw source files for catalog items.

    python download_assets.py <work dir> [items file]   # default: <work>/items.json

Poly Haven: 1K glTF + its textures, the transparent product render, and the
asset info (authors). Khronos: the GLB (or glTF + files), the large
screenshot, and metadata.json. Sketchfab (CC-BY only): the GLB through the
download API, the largest thumbnail, and the model's licence as reported on
the download date; needs an API token in .sketchfab_token at the assets repo
root (git-ignored, never committed).

Writes <work>/raw/<id>/... and merges into <work>/sources.json (source URL,
licence, authors, download date). Re-running skips files that already exist.
"""

import datetime
import io
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path

UA = {"User-Agent": "asset-download-script/1.0"}
KH = "https://raw.githubusercontent.com/KhronosGroup/glTF-Sample-Assets/main/Models"
SF = "https://api.sketchfab.com/v3"
TOKEN_FILE = Path(__file__).resolve().parent.parent / ".sketchfab_token"


def get(url: str, headers: dict | None = None) -> bytes:
    for attempt in range(4):
        try:
            req = urllib.request.Request(url, headers={**UA, **(headers or {})})
            with urllib.request.urlopen(req, timeout=300) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < 3:
                time.sleep(15 * (attempt + 1))
                continue
            if e.code in (401, 403, 404) or attempt == 3:
                raise
            time.sleep(2)
        except Exception:
            if attempt == 3:
                raise
            time.sleep(2)


def save(url: str, dest: Path, headers: dict | None = None) -> None:
    if dest.exists() and dest.stat().st_size > 0:
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(get(url, headers))


def sketchfab(it: dict, out: Path, today: str) -> dict:
    token = TOKEN_FILE.read_text(encoding="utf-8").strip()
    auth = {"Authorization": f"Token {token}"}
    uid = it["src"]
    info = json.loads(get(f"{SF}/models/{uid}"))
    licence = (info.get("license") or {}).get("label")
    if licence != "CC Attribution":  # checked again at download time
        raise SystemExit(f"{it['id']}: licence is now {licence!r}, not CC Attribution; skipping all downloads")
    model_dir = out / "model"
    if not any(model_dir.glob("*.glb")) and not any(model_dir.glob("*.gltf")):
        links = json.loads(get(f"{SF}/models/{uid}/download", auth))
        if "glb" in links:
            save(links["glb"]["url"], model_dir / f"{uid}.glb")
        else:  # some models only offer a zipped glTF
            data = get(links["gltf"]["url"])
            zipfile.ZipFile(io.BytesIO(data)).extractall(model_dir)
    thumbs = sorted(info.get("thumbnails", {}).get("images", []), key=lambda i: -i["width"])
    if thumbs:
        save(thumbs[0]["url"], out / "render.jpg")
    user = info["user"]
    return {
        "source": "Sketchfab", "title": info["name"].strip(), "url": info["viewerUrl"],
        "authors": [user["displayName"]], "author_url": user["profileUrl"],
        "licence": "CC-BY 4.0", "licence_as_reported": licence, "downloaded": today,
    }


def main() -> None:
    work = Path(sys.argv[1])
    items_file = Path(sys.argv[2]) if len(sys.argv) > 2 else work / "items.json"
    items = json.loads(items_file.read_text(encoding="utf-8"))
    today = datetime.date.today().isoformat()
    sources_file = work / "sources.json"
    sources = json.loads(sources_file.read_text(encoding="utf-8")) if sources_file.exists() else {}
    for n, it in enumerate(items, 1):
        cid, src = it["id"], it["src"]
        out = work / "raw" / cid
        if it["source"] == "sketchfab":
            sources[cid] = sketchfab(it, out, today)
        elif it["source"] == "polyhaven":
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
        sources_file.write_text(json.dumps(sources, indent=1, ensure_ascii=False), encoding="utf-8")
        print(f"[{n}/{len(items)}] {cid}", flush=True)


if __name__ == "__main__":
    main()
