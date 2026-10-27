### Task 4: Closure scan: a guard counts only while its name is unbound and unmutated (`owner.py`, `sign.py`)

**Files:**
- Modify: `core/compliance/owner.py` (anchors: `_skipped` (:708-724 today; `_guards` is inserted right before it,
  after `_typing_flag`), `_import_nodes` (:727-736), the `_import_nodes(...)` loop line of `_repo_imports` (:755); LF;
  a D14 closure file)
- Modify: `tools/signer/sign.py` (anchors: the same three, `_skipped` :631-647, `_import_nodes` :650-659,
  `_repo_imports` :678; LF; off the closure, the owner keeps a copy)
- Modify: `tests/compliance_store.py` (anchors: the module's import block, `import contextlib` :7; and
  `test_code_files_counts_lazy_imports_and_skips_main_and_type_checking`, :153-194; LF)
- Modify: `tests/compliance_signer.py` (anchors: `test_code_files_match_owner`, :630-677, and the start of
  `test_store_layout_matches_owner_store_put`, :680, before which the new test goes; LF)
- Test: `tests/compliance_store.py`, `tests/compliance_signer.py`

**Interfaces:**
- Consumes (unchanged, identical in owner.py and sign.py): `_binds(tree: ast.AST, name: str) -> int` (owner.py:683,
  sign.py:606: bindings of `name` at any depth, imports, assignments, defs, parameters, except-as, match captures);
  `_typing_flag(tree: ast.AST) -> bool` (owner.py:699, sign.py:622); `_module_file(root, dotted)`;
  `code_files(repo_root) -> list[tuple[str, str]]` and `code_hash(repo_root) -> str` (their bodies do not change).
  Test fixtures: `F.temp_home()` (tests/compliance_store.py, from tests.compliance_fixtures); in
  tests/compliance_signer.py the module-level `signer` (loaded by path as `tradegen_signer_under_test`), `owner`,
  `ROOT` and `_home()` (:120, the test's temp TRADEGEN_HOME).
- Produces, character-identical in `core/compliance/owner.py` and `tools/signer/sign.py`:
  - `_guards(tree: ast.AST) -> tuple[bool, bool, bool]`: (bare `TYPE_CHECKING` trusted, `typing.TYPE_CHECKING`
    trusted, `__name__ == "__main__"` trusted) for one module;
  - `_skipped(node: ast.AST, guards: tuple[bool, bool, bool]) -> bool` (was `bare_flag: bool`);
  - `_import_nodes(node: ast.AST, guards: tuple[bool, bool, bool])` (was `bare_flag: bool`);
  - `_repo_imports(root, path)` keeps its signature and passes `_guards(tree)`.
  - New test `test_closure_scan_helpers_are_identical_in_owner_and_signer` in tests/compliance_signer.py. Task 5 edits
    sign.py after this task (other functions only); nothing here is renamed.

**Plan decisions used:** R4 (with its stated limit, accepted by R2-12); R13 and the drift rule (Global Constraints).

What this task does and why:
- Today `if typing.TYPE_CHECKING:` is skipped whatever `typing` is bound to (owner.py:718-719), and
  `if __name__ == "__main__":` is skipped even when the module rebinds `__name__` (owner.py:720-723). So
  `typing = SimpleNamespace(TYPE_CHECKING=True)` or `__name__ = "__main__"` hides an import that does run from the
  D14 closure (ledger:208), and so do `typing.TYPE_CHECKING = True`, `setattr(typing, ...)`,
  `globals()["__name__"] = ...` and `sys.modules["typing"] = ...`, which change the names without binding them.
- After: `typing.TYPE_CHECKING` counts only when `typing` is bound exactly once in the module, by a plain
  `import typing`; the `__main__` test counts only when `__name__` is bound nowhere in the module; the bare
  `TYPE_CHECKING` keeps today's `_typing_flag` rule. A module that stores to an attribute `TYPE_CHECKING` or
  `__name__`, or uses any Name or attribute `setattr`, `delattr`, `globals`, `vars`, `locals`, `modules`, `__dict__`,
  `builtins` or `__builtins__`, trusts no guard at all, the bare one included. Every change only scans more.
- The signer's copy (sign.py:597-718, "a copy of owner.code_files (P6)") gets the identical text, and a new test
  compares the source of the seven closure-scan helpers in the two files, so a hardening in one cannot be forgotten in
  the other; `test_code_files_match_owner` keeps comparing their outputs on the real and the synthetic tree.
- State after this task, checked in a sandbox on 2026-10-24 with exactly the text below: the real closure is unchanged
  (10 entries: `core/__init__.py`, `core/isolation.py`, `core/compliance/__init__.py`, `alerts.py`, `gate.py`,
  `model.py`, `owner.py`, `rules.py`, and the PyYAML and cryptography RECORD rows), and no closure file uses any of the
  route names, so `rules.py` and `model.py` keep their bare `TYPE_CHECKING` skip and `rules.py` and `alerts.py` their
  `__main__` skip. Of the ten synthetic modules below, today's helpers hide all ten targets and the new ones hide none;
  the eight route cases asserted directly on `_guards` each void all three guards. For the odds plan: a core/odds
  module that uses any route name anywhere (a `vars()` call, a name `modules`, `.__dict__`) trusts no guard, so its
  `if TYPE_CHECKING:` and `__main__` imports count in the D14 closure (and `test_code_files_is_the_import_closure`
  turns red if one names a repo file outside its expected set: core/__init__.py, core/isolation.py,
  core/compliance/*.py, core/odds/*.py). The same holds for E1's execution/*.py once its Task 9 adds them to the
  closure: keep TYPE_CHECKING-only imports out of a closure module that uses a route name.
- Code hash: owner.py is a closure file, so the D14 code hash moves. No `code_approved` exists yet (owner act 2 is not
  done), so nothing is re-signed now. sign.py is off the closure, but the owner runs a copy of it: owner act 1 is not
  done, so the owner copies the merged file then; if a copy already exists, the owner reads the diff of
  `tools/signer/sign.py`, re-hashes it in Windows Terminal (PowerShell) with the certutil line of Task 8 Step 9,
  `certutil -hashfile "$env:USERPROFILE\tradegen-signer\sign.py" SHA256`, and re-records the hash on paper (Task 5
  changes sign.py again; one owner act after the merge covers both).
- Stated limit (spec rev 3.3; accepted as stated, RULINGS_ROUND2 R2-12): the route list is a denylist. Another module
  changing `typing.TYPE_CHECKING` before this one is imported, or a name built at run time, is not seen; the owner's
  review of each hashed file's diff is the barrier there. The `_guards` docstring names the first of these (its text
  is fixed by Appendix A section 6.1). In-module routes the list misses include these, each confirmed in the sandbox (2026-10-24) to
  still hide an import that runs: a frame's globals (`sys._getframe().f_globals["__name__"] = "__main__"`), an
  attribute fetched by string (`getattr(sys, "modules")["typing"] = ...`), a dunder call
  (`typing.__setattr__("TYPE_CHECKING", True)`, `object.__setattr__(typing, "TYPE_CHECKING", True)`) and a
  from-import alias of a route name (`from sys import modules as m`, `from builtins import setattr as s`,
  `from builtins import globals as g`). No Task 1 guard sees them either (sys and builtins are on no list). Each is
  plain to read in a hashed diff. Listing `getattr` or `__setattr__` would void every guard of rules.py (`getattr` at
  rules.py:813, :867), model.py (`getattr` at :37, :198 and `object.__setattr__` at model.py:199) and alerts.py
  (alerts.py:223); today's closure would stay the same, because their guarded bodies import only closure files
  (model.py:17-18, rules.py:24-25) or nothing (rules.py:970, alerts.py:353), but Appendix A section 6.1 fixes the route list, so this
  task leaves those names and alias names out.
- Departures from Appendix A (the task wins): Appendix A section 6.4 lists only the ten synthetic files for
  tests/compliance_store.py. This task also adds `import ast` there (Edit T0) and, after the expected set (Edit T3),
  one assert that `owner._guards` trusts all three guards of a plain module plus eight direct `owner._guards` route
  asserts (delattr, vars, locals, `__dict__`, builtins, `__builtins__`, a `__name__` attribute store, a `del` of
  `TYPE_CHECKING`), each voiding all three guards. owner.py and sign.py get exactly Appendix A sections 6.1-6.3.
- Drift: no earlier task of this plan touches these four files (Task 2 changes rules.py, not owner.py), so the quoted
  text is that of `5816d3c`. Re-read each file before its Edit; if the quoted old text differs only because an earlier
  plan changed it, apply the same change to the current text, keep the earlier behaviour and write one ledger line;
  if the change no longer makes sense, stop and rule. Edits O1-O3 are applied to owner.py and then, unchanged, to
  sign.py: the old texts are character-identical in the two files today.

- [ ] **Step 1: Write the failing tests**

  All Edits with the Edit tool; both files are LF.

  **Edit T0**, `tests/compliance_store.py`, the module's import block (`ast` is new there; the route asserts of
  Edit T3 parse source text). Old text (exact):

```python
import contextlib
import datetime as _dt
```

  New text:

```python
import ast
import contextlib
import datetime as _dt
```

  **Edit T1**, `tests/compliance_store.py`, `test_code_files_counts_lazy_imports_and_skips_main_and_type_checking`,
  the last docstring line. Old text (exact):

```python
    at import: an `!=` test, a bare TYPE_CHECKING that is a local (or rebound) name, and `not TYPE_CHECKING`."""
```

  New text:

```python
    at import: an `!=` test, a bare TYPE_CHECKING that is a local (or rebound) name, and `not TYPE_CHECKING`; and a
    guard whose name the module rebinds or never imports plainly (typing rebound, `import os as typing`, no `import
    typing`, `__name__` assigned or a parameter), or that the module can change without a binding (an attribute store,
    setattr, globals(), sys.modules), is scanned too (R4)."""
```

  **Edit T2**, same function, the `sources` dict: ten synthetic modules after `f.py` and their ten empty targets after
  `core/rev_cli.py`. Old text (exact):

```python
        "core/compliance/f.py": "if \"__main__\" == __name__:\n    import core.rev_cli\n",
        "core/neq.py": "", "core/local_tc.py": "", "core/rebound.py": "", "core/negated.py": "",
        "core/rev_cli.py": "",
```

  New text:

```python
        "core/compliance/f.py": "if \"__main__\" == __name__:\n    import core.rev_cli\n",
        "core/compliance/h.py": ("import types\nimport typing\ntyping = types.SimpleNamespace(TYPE_CHECKING=True)\n"
                                 "if typing.TYPE_CHECKING:\n    import core.rebound_typing\n"),
        "core/compliance/i.py": "__name__ = \"__main__\"\nif __name__ == \"__main__\":\n    import core.rebound_main\n",
        "core/compliance/j.py": "import os as typing\nif typing.TYPE_CHECKING:\n    import core.alias_typing\n",
        "core/compliance/k.py": "if typing.TYPE_CHECKING:\n    import core.unbound_typing\n",
        "core/compliance/l.py": ("def main(__name__=None):\n    return __name__\n"
                                 "if __name__ == \"__main__\":\n    import core.param_main\n"),
        "core/compliance/m.py": ("import typing\ntyping.TYPE_CHECKING = True\n"
                                 "if typing.TYPE_CHECKING:\n    import core.stored_typing\n"),
        "core/compliance/n.py": ("import typing\nsetattr(typing, \"TYPE_CHECKING\", True)\n"
                                 "if typing.TYPE_CHECKING:\n    import core.setattr_typing\n"),
        "core/compliance/o.py": ("globals()[\"__name__\"] = \"__main__\"\n"
                                 "if __name__ == \"__main__\":\n    import core.globals_main\n"),
        "core/compliance/p.py": ("import sys\nimport types\n"
                                 "sys.modules[\"typing\"] = types.SimpleNamespace(TYPE_CHECKING=True)\n"
                                 "import typing\nif typing.TYPE_CHECKING:\n    import core.modules_typing\n"),
        "core/compliance/q.py": ("import typing\ntyping.TYPE_CHECKING = True\nfrom typing import TYPE_CHECKING\n"
                                 "if TYPE_CHECKING:\n    import core.stored_bare\n"),
        "core/neq.py": "", "core/local_tc.py": "", "core/rebound.py": "", "core/negated.py": "",
        "core/rev_cli.py": "",
        "core/rebound_typing.py": "", "core/rebound_main.py": "", "core/alias_typing.py": "",
        "core/unbound_typing.py": "", "core/param_main.py": "", "core/stored_typing.py": "",
        "core/setattr_typing.py": "", "core/globals_main.py": "", "core/modules_typing.py": "",
        "core/stored_bare.py": "",
```

  **Edit T3**, same function, the expected set, then direct asserts on `owner._guards` for the routes the synthetic
  modules do not exercise (delattr, vars, locals, `__dict__`, builtins, `__builtins__`, an attribute store of
  `__name__`, a `del` of `TYPE_CHECKING`), so dropping one from `routes` turns this test red. Old text (exact):

```python
                    "core/compliance/f.py",
                    "core/neq.py", "core/local_tc.py", "core/rebound.py", "core/negated.py"}, sorted(repo)
```

  New text:

```python
                    "core/compliance/f.py",
                    "core/compliance/h.py", "core/compliance/i.py", "core/compliance/j.py", "core/compliance/k.py",
                    "core/compliance/l.py", "core/compliance/m.py", "core/compliance/n.py", "core/compliance/o.py",
                    "core/compliance/p.py", "core/compliance/q.py",
                    "core/rebound_typing.py", "core/rebound_main.py", "core/alias_typing.py",
                    "core/unbound_typing.py", "core/param_main.py", "core/stored_typing.py",
                    "core/setattr_typing.py", "core/globals_main.py", "core/modules_typing.py",
                    "core/stored_bare.py",
                    "core/neq.py", "core/local_tc.py", "core/rebound.py", "core/negated.py"}, sorted(repo)
    trusted = "import typing\nfrom typing import TYPE_CHECKING\n"
    assert owner._guards(ast.parse(trusted)) == (True, True, True)
    for route in ("delattr(typing, 'x')", "vars(typing)", "locals()", "typing.__dict__", "import builtins\nbuiltins",
                  "__builtins__", "typing.__name__ = 'x'", "del typing.TYPE_CHECKING"):
        assert owner._guards(ast.parse(trusted + route + "\n")) == (False, False, False), route
```

  **Edit T4**, `tests/compliance_signer.py`, `test_code_files_match_owner`, the `sources` dict (its tree also holds
  `core/compliance/g.py`, which stays). Old text (exact):

```python
        "core/compliance/g.py": "def main():\n    from core.compliance import g\n    return g\n",   # rules.main's shape
        "core/neq.py": "", "core/local_tc.py": "", "core/rebound.py": "", "core/negated.py": "",
        "core/rev_cli.py": "",
```

  New text:

```python
        "core/compliance/g.py": "def main():\n    from core.compliance import g\n    return g\n",   # rules.main's shape
        "core/compliance/h.py": ("import types\nimport typing\ntyping = types.SimpleNamespace(TYPE_CHECKING=True)\n"
                                 "if typing.TYPE_CHECKING:\n    import core.rebound_typing\n"),
        "core/compliance/i.py": "__name__ = \"__main__\"\nif __name__ == \"__main__\":\n    import core.rebound_main\n",
        "core/compliance/j.py": "import os as typing\nif typing.TYPE_CHECKING:\n    import core.alias_typing\n",
        "core/compliance/k.py": "if typing.TYPE_CHECKING:\n    import core.unbound_typing\n",
        "core/compliance/l.py": ("def main(__name__=None):\n    return __name__\n"
                                 "if __name__ == \"__main__\":\n    import core.param_main\n"),
        "core/compliance/m.py": ("import typing\ntyping.TYPE_CHECKING = True\n"
                                 "if typing.TYPE_CHECKING:\n    import core.stored_typing\n"),
        "core/compliance/n.py": ("import typing\nsetattr(typing, \"TYPE_CHECKING\", True)\n"
                                 "if typing.TYPE_CHECKING:\n    import core.setattr_typing\n"),
        "core/compliance/o.py": ("globals()[\"__name__\"] = \"__main__\"\n"
                                 "if __name__ == \"__main__\":\n    import core.globals_main\n"),
        "core/compliance/p.py": ("import sys\nimport types\n"
                                 "sys.modules[\"typing\"] = types.SimpleNamespace(TYPE_CHECKING=True)\n"
                                 "import typing\nif typing.TYPE_CHECKING:\n    import core.modules_typing\n"),
        "core/compliance/q.py": ("import typing\ntyping.TYPE_CHECKING = True\nfrom typing import TYPE_CHECKING\n"
                                 "if TYPE_CHECKING:\n    import core.stored_bare\n"),
        "core/neq.py": "", "core/local_tc.py": "", "core/rebound.py": "", "core/negated.py": "",
        "core/rev_cli.py": "",
        "core/rebound_typing.py": "", "core/rebound_main.py": "", "core/alias_typing.py": "",
        "core/unbound_typing.py": "", "core/param_main.py": "", "core/stored_typing.py": "",
        "core/setattr_typing.py": "", "core/globals_main.py": "", "core/modules_typing.py": "",
        "core/stored_bare.py": "",
```

  **Edit T5**, `tests/compliance_signer.py`, the end of `test_code_files_match_owner` (its expected set) and the
  new test between it and `test_store_layout_matches_owner_store_put`. Old text (exact):

```python
        "core/compliance/f.py", "core/compliance/g.py",
        "core/neq.py", "core/local_tc.py", "core/rebound.py", "core/negated.py"}, mine


def test_store_layout_matches_owner_store_put():
```

  New text:

```python
        "core/compliance/f.py", "core/compliance/g.py",
        "core/compliance/h.py", "core/compliance/i.py", "core/compliance/j.py", "core/compliance/k.py",
        "core/compliance/l.py", "core/compliance/m.py", "core/compliance/n.py", "core/compliance/o.py",
        "core/compliance/p.py", "core/compliance/q.py",
        "core/rebound_typing.py", "core/rebound_main.py", "core/alias_typing.py", "core/unbound_typing.py",
        "core/param_main.py", "core/stored_typing.py", "core/setattr_typing.py", "core/globals_main.py",
        "core/modules_typing.py", "core/stored_bare.py",
        "core/neq.py", "core/local_tc.py", "core/rebound.py", "core/negated.py"}, mine


def test_closure_scan_helpers_are_identical_in_owner_and_signer():
    """R4: the signer's copy of the D14 closure scan is owner.py's, character for character, so a hardening in one
    file cannot be forgotten in the other (test_code_files_match_owner compares outputs on chosen trees only)."""
    import inspect
    for name in ("_binds", "_typing_flag", "_guards", "_skipped", "_import_nodes", "_module_file", "_repo_imports"):
        assert inspect.getsource(getattr(signer, name)) == inspect.getsource(getattr(owner, name)), name


def test_store_layout_matches_owner_store_put():
```

  (`code_files` and `code_hash` are not compared: the signer's copies differ on purpose, in their docstrings (its
  `code_hash` has none) and in calling its own `sha256_hex`/`canonical_json` and a function-level
  `from importlib import metadata`, since it may not import the repo. The other six helpers are character-identical
  today, checked 2026-10-24.)

- [ ] **Step 2: Run to verify it fails**

  Overlap check with the PowerShell tool (it must print nothing; otherwise wait and re-run):

```powershell
Get-CimInstance Win32_Process -Filter "Name LIKE 'python%'" | Where-Object { $_.CommandLine -match 'run_all' } | Select-Object ProcessId,Name,CommandLine
```

  Then from the repo root in Git Bash:

```bash
.venv/Scripts/python.exe -m tests.compliance_acceptance compliance_store/
```

  Expected: a traceback, then the line
  `FAIL compliance_store/test_code_files_counts_lazy_imports_and_skips_main_and_type_checking AssertionError: [...]`,
  whose list (the closure today's helpers build) names `core/compliance/h.py` to `core/compliance/q.py` but none of
  the ten targets `core/alias_typing.py`, `core/globals_main.py`, `core/modules_typing.py`, `core/param_main.py`,
  `core/rebound_main.py`, `core/rebound_typing.py`, `core/setattr_typing.py`, `core/stored_bare.py`,
  `core/stored_typing.py`, `core/unbound_typing.py` (the expected-set assert fails before the `owner._guards` asserts
  run, so there is no AttributeError); and, ending, `28/29 passed, 1 failed, 0 not run` (exit code 1).

  Overlap check again, then:

```bash
.venv/Scripts/python.exe -m tests.compliance_acceptance compliance_signer/
```

  Expected, two FAIL lines (each after its traceback):

```
FAIL compliance_signer/test_closure_scan_helpers_are_identical_in_owner_and_signer AttributeError: module 'tradegen_signer_under_test' has no attribute '_guards'
```

  and `FAIL compliance_signer/test_code_files_match_owner AssertionError: [('config.py', ...), ...]` (the signer's
  closure of the synthetic tree, with the same ten targets missing; the signer and owner.py still agree with each
  other, so it is the expected-set assertion that fails); ending `36/38 passed, 2 failed, 0 not run` (exit code 1).
  Any other failure: stop and rule.

- [ ] **Step 3: Implement**

  Apply Edits O1, O2 and O3 to `core/compliance/owner.py`, then the same three Edits, unchanged, to
  `tools/signer/sign.py` (Edit tool; both LF). Each old text occurs exactly once in each file.

  **Edit O1**, anchor `_skipped` (owner.py:708-724, sign.py:631-647): `_guards` goes right after `_typing_flag`, and
  `_skipped` takes the guards tuple. Old text (exact):

```python
def _skipped(node: ast.AST, bare_flag: bool) -> bool:
    """Whether `node` is an `if` whose body never runs at import and so is outside the code closure (P6):
    `if typing.TYPE_CHECKING:`, `if TYPE_CHECKING:` when `bare_flag` (see _typing_flag), and a single `==`
    comparison of `__name__` with "__main__" in either order. Every other test (`!=`, `not TYPE_CHECKING`, a local
    TYPE_CHECKING) is scanned, since its body can run at import."""
    if not isinstance(node, ast.If):
        return False
    t = node.test
    if isinstance(t, ast.Name):
        return t.id == "TYPE_CHECKING" and bare_flag
    if isinstance(t, ast.Attribute):
        return t.attr == "TYPE_CHECKING" and isinstance(t.value, ast.Name) and t.value.id == "typing"
    if isinstance(t, ast.Compare) and len(t.ops) == 1 and isinstance(t.ops[0], ast.Eq):
        sides = [t.left, *t.comparators]
        return (any(isinstance(s, ast.Name) and s.id == "__name__" for s in sides)
                and any(isinstance(s, ast.Constant) and s.value == "__main__" for s in sides))
    return False
```

  New text:

```python
def _guards(tree: ast.AST) -> tuple[bool, bool, bool]:
    """Which `if` guards of `tree` may skip their body (P6, R4): (bare TYPE_CHECKING, typing.TYPE_CHECKING,
    __name__ == "__main__"). The bare name needs _typing_flag; `typing.` needs `typing` bound exactly once, by a
    plain `import typing`; the `__main__` test needs `__name__` bound nowhere in the module. A rebound name
    (typing = SimpleNamespace(TYPE_CHECKING=True), __name__ = "__main__") loses its guard, and a module that can
    change these names without binding them (an attribute store of TYPE_CHECKING or __name__, or any setattr,
    delattr, globals, vars, locals, modules, __dict__, builtins or __builtins__) trusts no guard: the guarded body
    is scanned. Not seen: another module changing typing.TYPE_CHECKING first (the review of each hashed diff)."""
    plain = any(isinstance(n, ast.Import) and any(a.name == "typing" and a.asname is None for a in n.names)
                for n in ast.walk(tree))
    routes = {"setattr", "delattr", "globals", "vars", "locals", "modules", "__dict__", "builtins", "__builtins__"}
    if any((isinstance(n, ast.Name) and n.id in routes) or (isinstance(n, ast.Attribute) and (n.attr in routes or (
            n.attr in ("TYPE_CHECKING", "__name__") and not isinstance(n.ctx, ast.Load)))) for n in ast.walk(tree)):
        return False, False, False
    return _typing_flag(tree), plain and _binds(tree, "typing") == 1, _binds(tree, "__name__") == 0


def _skipped(node: ast.AST, guards: tuple[bool, bool, bool]) -> bool:
    """Whether `node` is an `if` whose body never runs at import and so is outside the code closure (P6):
    `if TYPE_CHECKING:`, `if typing.TYPE_CHECKING:` and a single `==` comparison of `__name__` with "__main__" in
    either order, each only while `guards` (see _guards) trusts its name. Every other test (`!=`, `not
    TYPE_CHECKING`, a local or rebound name) is scanned, since its body can run at import."""
    if not isinstance(node, ast.If):
        return False
    bare, dotted, main = guards
    t = node.test
    if isinstance(t, ast.Name):
        return t.id == "TYPE_CHECKING" and bare
    if isinstance(t, ast.Attribute):
        return dotted and t.attr == "TYPE_CHECKING" and isinstance(t.value, ast.Name) and t.value.id == "typing"
    if isinstance(t, ast.Compare) and len(t.ops) == 1 and isinstance(t.ops[0], ast.Eq):
        sides = [t.left, *t.comparators]
        return (main and any(isinstance(s, ast.Name) and s.id == "__name__" for s in sides)
                and any(isinstance(s, ast.Constant) and s.value == "__main__" for s in sides))
    return False
```

  **Edit O2**, anchor `_import_nodes` (owner.py:727-736, sign.py:650-659): the parameter becomes the guards tuple;
  the docstring stays. Old text (exact):

```python
def _import_nodes(node: ast.AST, bare_flag: bool):
    """Every import statement at any depth, function bodies included; a skipped `if` keeps its `else`."""
    if _skipped(node, bare_flag):
        for child in node.orelse:
            yield from _import_nodes(child, bare_flag)
        return
    if isinstance(node, (ast.Import, ast.ImportFrom)):
        yield node
    for child in ast.iter_child_nodes(node):
        yield from _import_nodes(child, bare_flag)
```

  New text:

```python
def _import_nodes(node: ast.AST, guards: tuple[bool, bool, bool]):
    """Every import statement at any depth, function bodies included; a skipped `if` keeps its `else`."""
    if _skipped(node, guards):
        for child in node.orelse:
            yield from _import_nodes(child, guards)
        return
    if isinstance(node, (ast.Import, ast.ImportFrom)):
        yield node
    for child in ast.iter_child_nodes(node):
        yield from _import_nodes(child, guards)
```

  **Edit O3**, anchor `_repo_imports` (owner.py:754-755, sign.py:677-678). Old text (exact):

```python
    tree = ast.parse(path.read_bytes())
    for node in _import_nodes(tree, _typing_flag(tree)):
```

  New text:

```python
    tree = ast.parse(path.read_bytes())
    for node in _import_nodes(tree, _guards(tree)):
```

  No other line changes: `_binds`, `_typing_flag`, `_module_file`, `code_files`, `code_hash`, `_RECORD_DISTS` and
  sign.py's section comment (sign.py:597-602, "An `if` body that never runs at import is skipped (see _skipped);
  every other body is scanned.", still true) are untouched. Then check (read-only, Git Bash, no overlap check
  needed):

```bash
git diff --stat
git diff --stat --ignore-cr-at-eol
git grep -n -E "bare_flag|_import_nodes\(tree, _typing_flag" -- core/compliance/owner.py tools/signer/sign.py
```

  Expected: the two stat outputs identical, with the per-file counts `core/compliance/owner.py | 42`,
  `tests/compliance_signer.py | 36`, `tests/compliance_store.py | 40`, `tools/signer/sign.py | 42` (each followed by
  its `+`/`-` bar) and `4 files changed, 135 insertions(+), 25 deletions(-)` (owner.py and sign.py 30 insertions and
  12 deletions each; the signer test 36 insertions; the store test 39 insertions and 1 deletion); the `git grep`
  prints nothing (exit code 1).

- [ ] **Step 4: Run to verify it passes**

  Overlap check (PowerShell tool, as in Step 2; it must print nothing), then:

```bash
.venv/Scripts/python.exe -m tests.compliance_acceptance compliance_store/
```

  Expected, ending: `29/29 passed, 0 failed, 0 not run` (exit code 0; `test_code_files_is_the_import_closure` still
  passes, so the real closure is the same 10 entries, and the eight route asserts on `owner._guards` pass).

  Overlap check, then:

```bash
.venv/Scripts/python.exe -m tests.compliance_acceptance compliance_signer/
```

  Expected, ending: `38/38 passed, 0 failed, 0 not run` (exit code 0).

  Overlap check, then the compliance suite (its guards scan the new owner.py text: raw words, imports, dynamic names,
  HTTP verbs, clock calls), then restore the results file. Every `--suite` run first imports all ten suites
  (run_all.py:41-50) and the compliance tests alone took 64 s on 2026-10-24, so give this line `timeout: 300000`;
  never start a second run meanwhile:

```bash
.venv/Scripts/python.exe tests/run_all.py --suite compliance; echo "exit $?"; git checkout -- qa/acceptance_results.json
```

  Expected, ending:

```
323/325 passed, 0 failed, 2 not run; C:\Users\whydi\OneDrive\Desktop\TRADEGEN\qa\acceptance_results.json
exit 0
```

  (325 rows: 324 after Task 3 plus the new signer test; the two not-run rows are the REFDATA symlink
  tests). A guard failure names the file and text: fix owner.py, never the guard. Then `git status --short` lists
  exactly the four files of this task, plus, if the executor keeps its ledger in the repo and has not committed it,
  `?? docs/superpowers/plans/2026-10-24-compliance-followup-execution-ledger.md`; nothing else.

- [ ] **Step 5: Commit**

```bash
git add core/compliance/owner.py tools/signer/sign.py tests/compliance_store.py tests/compliance_signer.py
git diff --cached --stat
git diff --cached --stat --ignore-cr-at-eol
```

  The two stat outputs must be identical (all four files are LF; the counts of Step 3). Then:

```bash
git commit -m "fix(compliance): closure scan skips a guard only while its name is unbound and unmutated" -m "R4 (ledger:208): owner._guards and its character-identical signer copy; a rebound typing or __name__, or an attribute store, setattr, globals or sys.modules route, voids the guard; source-equality test added." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```
