# Copyright 2026 PackDB Contributors
# Licensed under the Apache License, Version 2.0

"""Check license metadata for the locked examples dependencies."""

import json
import re
from importlib.metadata import distribution
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PERMISSIVE = {"Apache-2.0", "MIT", "BSD-3-Clause", "BSD-2-Clause", "ISC"}
PYTHON_TERMS = {
    "certifi": "MPL-2.0",
    "packaging": "Apache-2.0 OR BSD-2-Clause",
    "protobuf": "3-Clause BSD License",
    "typing-extensions": "PSF-2.0",
}


def main() -> None:
    packages = json.loads((ROOT / "typescript/package-lock.json").read_text())[
        "packages"
    ]
    for path, package in packages.items():
        if package.get("license") not in PERMISSIVE:
            raise SystemExit(
                f"Review the license for {path}: {package.get('license')!r}"
            )

    lock = (ROOT / "python/requirements.txt").read_text()
    for name, version in re.findall(r"^([\w.-]+)==([^\s]+)", lock, re.MULTILINE):
        dist = distribution(name)
        if dist.version != version:
            raise SystemExit(f"Install the Python lockfile before checking {name}")
        metadata = dist.metadata
        license_name = metadata.get("License-Expression") or metadata.get("License")
        if license_name not in PERMISSIVE and license_name != PYTHON_TERMS.get(
            name, ""
        ):
            raise SystemExit(f"Review the license for {name}: {license_name!r}")


if __name__ == "__main__":
    main()
