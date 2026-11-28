"""Compare a target D14 export and independent signer to an explicit reviewed Git commit.

Run on the deployment interpreter from its reviewed checkout. No code from Git
objects or from the independent signer is imported. Output contains no private paths.
"""
from __future__ import annotations

import hashlib
import json
import ntpath
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from threading import Timer

from core.compliance import owner
from execution_launch import deployment as D
from execution_launch.workflow import _read_file


_COMMIT = re.compile(r"(?:[a-f0-9]{40}|[a-f0-9]{64})")
_SIGNER = "tools/signer/sign.py"
_HELP = ("python -m tools.reviewed_deployment --review-repo PATH --commit FULL_COMMIT_ID "
         "--manifest TARGET_EXPORT.json --trusted-signer PATH_TO_EXTERNAL_sign.py")
_MAX_TREE = 4 * 1024 * 1024
_MAX_SOURCE = 4 * 1024 * 1024
_MAX_TOTAL = 64 * 1024 * 1024


class ReviewError(ValueError):
    pass


def _require(condition, code):
    if not condition:
        raise ReviewError(code)


def _git(repo, args, *, data=None, maximum):
    # Read raw objects without replacement refs, filters, network or Git
    # configuration inherited from an unrelated working tree.
    env = {key: os.environ[key] for key in ("PATH", "SYSTEMROOT", "SystemRoot", "WINDIR", "TEMP", "TMP")
           if key in os.environ}
    env.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull, GIT_NO_LAZY_FETCH="1",
               GIT_TERMINAL_PROMPT="0", GIT_OPTIONAL_LOCKS="0", GIT_ALLOW_PROTOCOL="")
    args = ["git", "--no-replace-objects", "-C", str(repo), *args]
    with tempfile.TemporaryFile() as payload:
        payload.write(data or b"")
        payload.seek(0)
        with subprocess.Popen(args, stdin=payload, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, env=env) as proc:
            timeout = Timer(60, proc.kill)
            timeout.start()
            try:
                result = proc.stdout.read(maximum + 1)
                _require(len(result) <= maximum, "REVIEW_OBJECT_LIMIT")
                _require(proc.wait() == 0, "REVIEW_OBJECT_UNAVAILABLE")
                return result
            finally:
                timeout.cancel()
                if proc.poll() is None:
                    proc.kill()


def _sources(repo, commit):
    _require(_COMMIT.fullmatch(commit), "REVIEW_FULL_COMMIT_REQUIRED")
    resolved = _git(repo, ["rev-parse", "--verify", commit], maximum=65)
    _require(resolved == commit.encode("ascii") + b"\n", "REVIEW_FULL_COMMIT_REQUIRED")
    _require(_git(repo, ["cat-file", "-t", commit], maximum=16) == b"commit\n", "REVIEW_COMMIT_REQUIRED")
    tree = _git(repo, ["ls-tree", "-r", "-l", "-z", "--full-tree", commit], maximum=_MAX_TREE)
    _require(tree.endswith(b"\0"), "REVIEW_TREE_INVALID")
    rows, total, spellings = [], 0, {}
    for entry in tree[:-1].split(b"\0"):
        metadata, path = entry.split(b"\t", 1)
        mode, kind, oid, size = metadata.split()
        _require(not path.lower().endswith(b".py") or path.endswith(b".py"), "REVIEW_SOURCE_CASE_UNSUPPORTED")
        # A module or package behind a link/gitlink cannot be represented by
        # ordinary immutable Python blobs in the pinned tree.
        if mode in (b"120000", b"160000"):
            parts = path.split(b"/")
            if path.endswith(b".py") or all(part.decode("utf-8").isidentifier() for part in parts):
                raise ReviewError("REVIEW_INDIRECT_SOURCE_UNSUPPORTED")
        if not path.endswith(b".py"):
            continue
        name = path.decode("utf-8")
        parts = name.split("/")
        _require(mode in (b"100644", b"100755") and kind == b"blob"
                 and all(re.fullmatch(r"[A-Za-z0-9_.-]+", part) and not ntpath.isreserved(part)
                         and not part.endswith(".") and part.casefold() not in {".", "..", ".git", *D._PRIVATE}
                         and not part.casefold().startswith(".env") for part in parts), "REVIEW_SOURCE_PATH_INVALID")
        for stop in range(1, len(parts) + 1):
            prefix = "/".join(parts[:stop])
            _require(spellings.setdefault(prefix.casefold(), prefix) == prefix, "REVIEW_SOURCE_CASE_COLLISION")
        length = int(size)
        total += length
        _require(0 <= length <= _MAX_SOURCE and total <= _MAX_TOTAL and len(rows) < 4096,
                 "REVIEW_OBJECT_LIMIT")
        rows.append((name, oid, length))
    _require(any(name == _SIGNER for name, _, _ in rows), "REVIEW_SIGNER_BLOB_REQUIRED")
    return rows, total


def _reviewed(repo, commit):
    rows, total = _sources(repo, commit)
    # All names and sizes come from the selected tree. Unreferenced Python
    # blobs are needed for the same module-resolution decisions as D14.
    body = _git(repo, ["cat-file", "--batch"], data=b"".join(oid+b"\n" for _, oid, _ in rows),
                maximum=total+len(rows)*100)
    position = 0
    with tempfile.TemporaryDirectory(prefix="tradegen-reviewed-source-") as directory:
        root = Path(directory)
        for name, oid, size in rows:
            header = oid+b" blob "+str(size).encode()+b"\n"
            _require(body.startswith(header, position), "REVIEW_OBJECT_INVALID")
            position += len(header)
            end = position + size
            _require(body[end:end+1] == b"\n", "REVIEW_OBJECT_INVALID")
            raw = body[position:end]
            algorithm = "sha1" if len(oid) == 40 else "sha256"
            digest = hashlib.new(algorithm, usedforsecurity=False)
            digest.update(b"blob " + str(size).encode() + b"\0")
            digest.update(raw)
            _require(digest.hexdigest().encode() == oid, "REVIEW_OBJECT_INVALID")
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
            position = end + 1
        _require(position == len(body), "REVIEW_OBJECT_INVALID")
        sources = [[name, digest] for name, digest in owner.code_files(root) if not name.startswith("venv:")]
        return sources, hashlib.sha256((root/_SIGNER).read_bytes()).hexdigest()


def verify(*, review_repo, commit, manifest, trusted_signer):
    repo = Path(review_repo)
    signer = Path(trusted_signer)
    _require(repo.is_absolute() and ".." not in repo.parts
             and not any(part.casefold() in D._PRIVATE or part.casefold().startswith(".env") for part in repo.parts)
             and not repo.drive.startswith(("\\", "//"))
             and not any(D._linked(part) for part in (repo, *repo.parents)) and repo.is_dir(),
             "REVIEW_REPOSITORY_REQUIRED")
    _require(signer.is_absolute() and signer.name == "sign.py" and ".." not in signer.parts
             and not any(part.casefold() in D._PRIVATE or part.casefold().startswith(".env") for part in signer.parts)
             and not any(signer.resolve().is_relative_to(root.resolve()) for root in (repo, D._ROOT)),
             "REVIEW_EXTERNAL_SIGNER_REQUIRED")
    claimed = D.parse_manifest(_read_file(manifest, D.MAX_MANIFEST_BYTES))
    expected, signer_hash = _reviewed(repo, commit)
    current = D.export_manifest(repo_root=D._ROOT)
    actual_signer = hashlib.sha256(_read_file(trusted_signer, _MAX_SOURCE, suffix=".py")).hexdigest()
    checkout_signer = hashlib.sha256(_read_file(str(D._ROOT/_SIGNER), _MAX_SOURCE, suffix=".py")).hexdigest()
    source_matches = current["repository_files"] == expected
    manifest_matches = current == claimed
    signer_matches = actual_signer == signer_hash
    return {"reviewed_commit": commit, "reviewed_source_count": len(expected),
            "reviewed_signer_sha256": signer_hash, "target_code_hash": current["code_hash"],
            "target_sources_match_review": source_matches, "saved_manifest_matches_target": manifest_matches,
            "dependency_records_match_export": current["dependency_records"] == claimed["dependency_records"],
            "runtime_matches_export": current["runtime"] == claimed["runtime"],
            "checkout_signer_matches_review": checkout_signer == signer_hash,
            "external_signer_matches_review": signer_matches,
            "comparison_passed": source_matches and manifest_matches and signer_matches and checkout_signer == signer_hash,
            "signature_verified": False, "execution_ready": False}


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if argv == ["--help"]:
        print(_HELP)
        return 0
    try:
        opts = dict(zip(argv[::2], argv[1::2]))
        _require(len(argv) == 8 and set(opts) == {"--review-repo", "--commit", "--manifest", "--trusted-signer"},
                 "REVIEW_ARGUMENTS_INVALID")
        report = verify(review_repo=opts["--review-repo"], commit=opts["--commit"],
                        manifest=opts["--manifest"], trusted_signer=opts["--trusted-signer"])
    except (OSError, ValueError, RuntimeError, SyntaxError, subprocess.SubprocessError) as exc:
        # Details from Git, paths and arbitrary exception messages are private.
        code = str(exc) if type(exc) is ReviewError else "REVIEW_INPUT_UNAVAILABLE"
        report = {"comparison_passed": False, "reason": code, "signature_verified": False, "execution_ready": False}
    print(json.dumps(report, sort_keys=True, ensure_ascii=True))
    return 0 if report["comparison_passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
