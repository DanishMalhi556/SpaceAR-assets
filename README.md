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
   rejects files over 100 MB. Optimise models before committing, e.g. with
   [gltf-transform](https://gltf-transform.dev/):
   ```sh
   npx @gltf-transform/cli optimize input.glb models/<id>.glb --texture-compress webp --texture-size 1024
   ```
4. **Check before pushing:** `python tools/check_assets.py` verifies names,
   sizes, formats and that every asset is listed in `LICENSES.md`.

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
