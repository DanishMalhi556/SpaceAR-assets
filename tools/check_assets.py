"""Checks the assets before a push. Run from the repository root:

    python tools/check_assets.py

Fails (exit code 1) if any file is badly named, the wrong format, too large,
stored with Git LFS, or missing from LICENSES.md. Standard library only.
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NAME = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
RULES = {
    # folder: (extension, magic-bytes check, warn above, fail above)
    "images": (".webp", lambda b: b[:4] == b"RIFF" and b[8:12] == b"WEBP", 300 * 1024, 2 * 1024 * 1024),
    "models": (".glb", lambda b: b[:4] == b"glTF", 5 * 1024 * 1024, 20 * 1024 * 1024),
}


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")  # Windows consoles default to cp1252
    errors: list[str] = []
    warnings: list[str] = []
    licences = (ROOT / "LICENSES.md").read_text(encoding="utf-8")
    counts = {}

    for folder, (ext, is_valid, warn_at, fail_at) in RULES.items():
        files = [p for p in sorted((ROOT / folder).iterdir()) if p.name != ".gitkeep"]
        counts[folder] = len(files)
        for p in files:
            rel = f"{folder}/{p.name}"
            if p.suffix != ext:
                errors.append(f"{rel}: must be a {ext} file")
                continue
            if not NAME.match(p.stem):
                errors.append(f"{rel}: name must be the catalog id (lowercase letters, digits, hyphens)")
            head = p.read_bytes()[:16]
            if head.startswith(b"version https://git-lfs"):
                errors.append(f"{rel}: stored with Git LFS, which jsDelivr can't serve")
            elif not is_valid(head):
                errors.append(f"{rel}: not a valid {ext} file")
            size = p.stat().st_size
            if size > fail_at:
                errors.append(f"{rel}: {size / 1e6:.1f} MB, over the {fail_at / 1e6:.0f} MB limit")
            elif size > warn_at:
                warnings.append(f"{rel}: {size / 1e6:.1f} MB, consider optimising (target ≤ {warn_at / 1e6:.1f} MB)")
            if f"`{rel}`" not in licences:
                errors.append(f"{rel}: missing from LICENSES.md")

    for w in warnings:
        print("warning:", w)
    for e in errors:
        print("error:  ", e)
    print(f"{counts['images']} images, {counts['models']} models, {len(errors)} errors, {len(warnings)} warnings")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
