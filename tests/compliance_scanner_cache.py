"""D14 source-byte caching must leave module discovery and approved digests live."""
from pathlib import Path
import os
import tempfile

from core.compliance import owner
from tools.signer import sign


def test_identical_bytes_still_recheck_new_module_and_changed_equal_size_source():
    for scanner in (owner, sign):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            seed = root / "execution" / "seed.py"
            seed.parent.mkdir()
            seed.write_text("import hook_a\n")
            hook_a, hook_b = root / "hook_a.py", root / "hook_b.py"
            hook_b.write_text("base = 1\n")
            initial = dict(scanner.code_files(root))
            assert "hook_a.py" not in initial
            hook_a.write_text("base = 2\n")
            present = dict(scanner.code_files(root))
            assert "hook_a.py" in present and "hook_b.py" not in present
            info = seed.stat()
            seed.write_text("import hook_b\n")
            os.utime(seed, ns=(info.st_atime_ns, info.st_mtime_ns))
            changed = dict(scanner.code_files(root))
            assert "hook_a.py" not in changed and "hook_b.py" in changed
            assert present["execution/seed.py"] != changed["execution/seed.py"]


def test_identical_relative_source_in_different_packages_resolves_separately():
    for scanner in (owner, sign):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            for name in ("pkg_a", "pkg_b"):
                module = root / name / "entry.py"
                module.parent.mkdir()
                module.write_text("from . import child\n")
                (module.parent / "child.py").write_text("")
                paths = scanner._repo_imports(root, module, module.read_bytes())
                assert paths == [module.parent / "child.py"]
