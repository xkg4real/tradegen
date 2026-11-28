"""Deterministic C++20 builder for native/tradegen_fast/build/libtradegen_fast.so."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
BUILD_DIR = ROOT / "build"
SO_NAME = "libtradegen_fast.so"
MANIFEST_NAME = "build_manifest.json"

SOURCE_PATHS = (
    "include/tg_abi.h",
    "include/tg_fp128.hpp",
    "src/hp1_continuous.cpp",
    "src/hp2_hp4_orders_books.cpp",
    "src/hp3_strategy_carry.cpp",
    "src/hp5_kis.cpp",
    "src/hp6_odds_mc.cpp",
)

CXX_FLAGS = (
    "-std=c++20",
    "-O3",
    "-fno-fast-math",
    "-ffp-contract=off",
    "-shared",
    "-fPIC",
    "-Wall",
    "-Wextra",
)


def compute_source_manifest(root: Path = ROOT) -> tuple[str, list[list[str]]]:
    rows: list[list[str]] = []
    for rel in sorted(SOURCE_PATHS):
        target = root / rel
        if not target.is_file() or target.is_symlink():
            raise RuntimeError(f"missing or invalid native source: {rel}")
        digest = hashlib.sha256(target.read_bytes()).hexdigest()
        rows.append([rel, digest])
    canonical = json.dumps(rows, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")
    return hashlib.sha256(canonical).hexdigest(), rows


def build(compiler: str = "g++") -> dict:
    source_sha256, rows = compute_source_manifest(ROOT)
    BUILD_DIR.mkdir(mode=0o755, parents=True, exist_ok=True)
    so_path = BUILD_DIR / SO_NAME
    cpp_files = [str(ROOT / rel) for rel in SOURCE_PATHS if rel.endswith(".cpp")]
    cmd = [
        compiler,
        *CXX_FLAGS,
        f"-I{ROOT / 'include'}",
        *cpp_files,
        "-o",
        str(so_path),
    ]
    subprocess.run(cmd, check=True)
    ver_proc = subprocess.run([compiler, "--version"], check=True, capture_output=True, text=True)
    compiler_version = ver_proc.stdout.splitlines()[0].strip() if ver_proc.stdout else compiler
    binary_sha256 = hashlib.sha256(so_path.read_bytes()).hexdigest()
    manifest = {
        "abi_version": 1,
        "binary_name": SO_NAME,
        "binary_sha256": binary_sha256,
        "compiler": compiler_version,
        "cxx_flags": list(CXX_FLAGS),
        "source_files": rows,
        "source_sha256": source_sha256,
    }
    manifest_bytes = (json.dumps(manifest, sort_keys=True, indent=2, ensure_ascii=True) + "\n").encode("ascii")
    (BUILD_DIR / MANIFEST_NAME).write_bytes(manifest_bytes)
    return manifest


def main() -> int:
    manifest = build()
    print(json.dumps(manifest, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
