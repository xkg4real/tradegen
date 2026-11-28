"""Deterministic C++17 native kernel compiler with SHA-256 manifest recording."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

from core.isolation import checked_target

ACCEL_DIR = Path(__file__).resolve().parent
SOURCE_PATH = ACCEL_DIR / "kernels.cpp"
BUILD_DIR = ACCEL_DIR / "build"
LIB_NAME = "libqlib_accel.so"
LIB_PATH = BUILD_DIR / LIB_NAME
MANIFEST_PATH = BUILD_DIR / "build_manifest.json"

RESEARCH_FLAGS = {
    "research_only": True,
    "live_eligible": False,
    "execution_ready": False,
    "source_authenticated": False,
    "owner_approval_verified": False,
}

CXX_FLAGS = ("-std=c++17", "-O3", "-fno-fast-math", "-shared", "-fPIC")


def sha256_file(path: Path) -> str:
    target = checked_target(path, "accel_file")
    return hashlib.sha256(target.read_bytes()).hexdigest()


def build_shared_library(*, compiler: str = "g++", output_dir: Path | None = None) -> dict:
    """Compile kernels.cpp into build/libqlib_accel.so and write build_manifest.json."""
    out_dir = checked_target(output_dir or BUILD_DIR, "accel_build_dir")
    out_dir.mkdir(parents=True, exist_ok=True)
    src = checked_target(SOURCE_PATH, "accel_source", within=ACCEL_DIR)
    so_path = checked_target(out_dir / LIB_NAME, "accel_shared_lib", within=out_dir)
    manifest_path = checked_target(out_dir / "build_manifest.json", "accel_manifest", within=out_dir)

    cxx = shutil.which(compiler)
    if not cxx:
        raise RuntimeError(f"C++17 compiler {compiler!r} not found on PATH")

    cmd = [cxx, *CXX_FLAGS, str(src), "-o", str(so_path)]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        raise RuntimeError(
            f"Failed to compile {src.name} (exit {proc.returncode}):\n{proc.stderr.strip()}"
        )

    src_sha = sha256_file(src)
    bin_sha = sha256_file(so_path)
    manifest = {
        "schema": "tradegen-qlib-accel-manifest-v1",
        "compiler": compiler,
        "flags": list(CXX_FLAGS),
        "source_file": src.name,
        "source_sha256": src_sha,
        "library_file": so_path.name,
        "binary_sha256": bin_sha,
        "research_flags": dict(RESEARCH_FLAGS),
        **RESEARCH_FLAGS,
    }
    raw = json.dumps(manifest, sort_keys=True, ensure_ascii=True, indent=2, allow_nan=False) + "\n"
    manifest_path.write_bytes(raw.encode("ascii"))
    return manifest


def main(argv: list[str] | None = None) -> int:
    _ = argv
    manifest = build_shared_library()
    sys.stdout.write(json.dumps(manifest, sort_keys=True, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
