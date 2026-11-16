# SpaceAR assets

Public catalog images and 3D models for the SpaceAR app, served free through
the **jsDelivr CDN**. The app's code lives in a separate private repository;
this repository holds only freely licensed assets.

## How files are served

Every file here is available at:

```
https://cdn.jsdelivr.net/gh/DanishMalhi556/SpaceAR-assets@<version>/<path>
```

For example:

```
https://cdn.jsdelivr.net/gh/DanishMalhi556/SpaceAR-assets@v1/images/sofa-aethel.webp
https://cdn.jsdelivr.net/gh/DanishMalhi556/SpaceAR-assets@v1/models/sofa-aethel.glb
```

These URLs go into each catalog item's `image_url` and `model_url` in
`backend/data/catalog_seed.json` in the SpaceAR repository.

**Always use a version tag** (`@v1`, `@v2`, …), not `@main`. jsDelivr caches
tagged files permanently, which is what makes it fast. To change a file,
commit it, create a new tag, and update the URLs to the new tag.

## Layout and naming

| Folder | Contents | Format | Target size |
|---|---|---|---|
| `images/` | One product photo per item | WebP, ~800 px on the long side | ≤ 300 KB (aim ~100 KB) |
| `models/` | One 3D model per item, for AR | GLB (binary glTF), real-world scale in metres | ≤ 5 MB (aim 1–3 MB), never over 20 MB |

- **File names must match the catalog item id:** `images/<id>.webp` and
  `models/<id>.glb`, e.g. `sofa-aethel.webp` / `sofa-aethel.glb`.
- Lowercase letters, digits and hyphens only.

## Rules

1. **Only CC0 or CC-BY assets** (or ones you created). Record every asset in
   [`LICENSES.md`](LICENSES.md) in the same commit that adds it. CC-BY
   requires credit, and this file is that credit.
2. **No Git LFS.** jsDelivr can't serve LFS files.
3. **Keep files small.** jsDelivr won't serve files over 20 MB, and GitHub
   rejects files over 100 MB. Use the pipeline below, which keeps textures
   as JPEG/PNG (no WebP/KTX2/Draco/Meshopt), so any AR viewer can open the
   models without extra decoders.
4. **Check before pushing:** `python tools/check_assets.py` verifies names,
   sizes, formats and that every asset is listed in `LICENSES.md`.

## Pipeline (`tools/`)

`tools/items.json` lists every item: `{source, src, id, name, category,
styles}`. The scripts work in a scratch folder outside this repo: create it
and copy `tools/items.json` into it first.

| Step | Command | Result |
|---|---|---|
| 1. Download | `python tools/download_assets.py <work>` | Raw models + renders in `<work>/raw/<id>/`, licence info in `<work>/sources.json` |
| 2. Models | `cd tools && npm install && node optimize.mjs <work> ..` then `node validate.mjs ../models` | `models/<id>.glb`: base centred on the floor, unused data removed, textures ≤ 1024 px; then checked with the Khronos glTF validator |
| 3. Images | `python tools/make_images.py <work> . <SpaceAR>/backend` | `images/<id>.webp` (800 × 800, padded, transparent where the source is) and `<work>/colors.json` |
| 4. Credits | `python tools/write_licenses.py <work> .` | `LICENSES.md` and `sources/<id>.json` |
| 5. Catalog | `python tools/build_seed.py <work> <SpaceAR>/backend v<N>` | `backend/data/catalog_seed.json` in the SpaceAR repo |

Steps 3 and 5 import the SpaceAR backend's colour, style and item-type code,
so catalog colours and types match what the recommender uses.

## Releasing a new version

```sh
python tools/check_assets.py
git add images models LICENSES.md
git commit -m "Add <n> items"
git tag v2
git push origin main --tags
```

Then point the catalog URLs at `@v2` and reseed the catalog from the SpaceAR
repository (`python -m scripts.seed_catalog` in `backend/`).
