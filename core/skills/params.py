"""Read a skill script's own argparse definition, so the UI can ask for inputs.

WHY THIS EXISTS
---------------
Every skill in the repository is an argparse CLI, and 25 of the 66 runnable
ones reject an empty command line outright: argparse prints a usage block and
exits 2 in about 0.15 seconds. Before this module the cockpit offered a single
free-text "Arguments" box, so the operator had to already know the flags — and
readiness reported those skills READY, because it only ever looked at
credentials. Clicking Run produced an instant, unexplained failure.

The fix is to stop guessing. This module extracts the actual parameter list
from the script's source and hands it to the UI, which renders one labelled
field per parameter and refuses to launch until the required ones are filled.

WHY STATIC ANALYSIS RATHER THAN `--help`
----------------------------------------
Running `--help` would be authoritative, but it executes the script's
module-level code — imports, client construction, occasionally a network call —
once per skill, and costs 0.15-1.5s each. Reading the source costs nothing and
runs no third-party code. The trade is that a parser assembled dynamically
cannot be read; `Spec.parsed` reports that honestly and the UI falls back to
the raw-arguments box rather than pretending the skill takes no arguments.

WHAT IT UNDERSTANDS
-------------------
Plain `add_argument`, `add_mutually_exclusive_group` (whose `required=True`
means "one of these"), and `add_subparsers` / `add_parser`, because three
skills are subcommand-driven and the subcommand is itself a required argument.
Arguments attached to a subparser are scoped to that subcommand, so selecting
"scan" must not demand the flags that only "backfill" takes.

Source order is preserved throughout. Positional arguments are emitted in the
order the script declares them, which is the only order argparse will accept.
"""
from __future__ import annotations

import ast
from dataclasses import dataclass, replace
from enum import Enum
from functools import lru_cache
from pathlib import Path
from typing import Optional

# Names that mark a value as a filesystem path even when `type=` says nothing.
# Checked as substrings of the flag and dest together: `--tickets-dir` is a
# directory, `--events-json` is a file, `--total-trades` is neither.
_DIR_HINTS = ("dir", "directory", "folder", "root")
_FILE_HINTS = ("-file", "_file", "-json", "_json", "-csv", "_csv",
               "-path", "_path", "-yaml", "_yaml", "input", "output")


class Kind(str, Enum):
    TEXT = "text"
    NUMBER = "number"
    INTEGER = "integer"
    FILE = "file"
    DIR = "dir"
    CHOICE = "choice"
    FLAG = "flag"


@dataclass(frozen=True)
class Param:
    dest: str
    flags: tuple[str, ...] = ()            # empty for a positional argument
    kind: Kind = Kind.TEXT
    required: bool = False
    default: Optional[str] = None
    choices: tuple[str, ...] = ()
    help: str = ""
    nargs: Optional[str] = None
    group: Optional[str] = None            # mutually-exclusive group id
    subcommand: Optional[str] = None       # None means "applies to every run"
    order: int = 0                         # declaration order, for positionals

    @property
    def positional(self) -> bool:
        return not self.flags

    @property
    def flag(self) -> str:
        """The long flag if there is one, else the first flag, else the dest."""
        for name in self.flags:
            if name.startswith("--"):
                return name
        return self.flags[0] if self.flags else self.dest

    @property
    def label(self) -> str:
        return self.flag.lstrip("-").replace("-", " ").replace("_", " ")

    @property
    def wants_path(self) -> bool:
        return self.kind in (Kind.FILE, Kind.DIR)


@dataclass(frozen=True)
class MutexGroup:
    id: str
    required: bool
    members: tuple[str, ...] = ()          # dests


@dataclass(frozen=True)
class Spec:
    script: str = ""
    params: tuple[Param, ...] = ()
    groups: tuple[MutexGroup, ...] = ()
    subcommands: tuple[str, ...] = ()
    subcommand_dest: str = ""
    subcommand_required: bool = False
    parsed: bool = False
    note: str = ""

    def for_subcommand(self, sub: Optional[str] = None) -> tuple[Param, ...]:
        """Parameters in play when `sub` is selected (global ones always are)."""
        return tuple(p for p in self.params
                     if p.subcommand is None or p.subcommand == sub)

    def required_params(self, sub: Optional[str] = None) -> tuple[Param, ...]:
        return tuple(p for p in self.for_subcommand(sub)
                     if p.required and p.group is None)

    def group_for(self, param: Param) -> Optional[MutexGroup]:
        for group in self.groups:
            if group.id == param.group:
                return group
        return None

    @property
    def takes_arguments(self) -> bool:
        return bool(self.params) or bool(self.subcommands)

    @property
    def needs_arguments(self) -> bool:
        """True when an empty command line cannot possibly succeed."""
        if self.subcommand_required and self.subcommands:
            return True
        if any(p.required and p.group is None and p.subcommand is None
               for p in self.params):
            return True
        return any(g.required for g in self.groups)

    def missing(self, values: Optional[dict] = None,
                sub: Optional[str] = None) -> tuple[str, ...]:
        """Required parameters `values` does not satisfy, as displayable names."""
        values = values or {}
        gaps: list[str] = []
        if self.subcommand_required and self.subcommands and not sub:
            gaps.append(self.subcommand_dest or "command")
        for param in self.required_params(sub):
            if not str(values.get(param.dest, "") or "").strip():
                gaps.append(param.flag)
        by_dest = {p.dest: p for p in self.for_subcommand(sub)}
        for group in self.groups:
            if not group.required:
                continue
            members = [d for d in group.members if d in by_dest]
            if not members:
                continue
            if not any(str(values.get(d, "") or "").strip() for d in members):
                gaps.append(" or ".join(by_dest[d].flag for d in members))
        return tuple(dict.fromkeys(gaps))

    def build_argv(self, values: Optional[dict] = None,
                   sub: Optional[str] = None) -> tuple[str, ...]:
        """Compose a command line. Only non-empty values are emitted.

        Positionals go first, in declaration order, because argparse matches
        them by position; flags follow in any order.
        """
        values = values or {}
        active = self.for_subcommand(sub)
        argv: list[str] = []
        if self.subcommands and sub:
            argv.append(sub)

        def text_of(param: Param) -> str:
            raw = values.get(param.dest)
            return "" if raw is None else str(raw).strip()

        for param in sorted((p for p in active if p.positional),
                            key=lambda p: p.order):
            text = text_of(param)
            if not text:
                continue
            argv.extend(text.split() if param.nargs in ("*", "+") else [text])

        for param in active:
            if param.positional:
                continue
            text = text_of(param)
            if not text:
                continue
            if param.kind is Kind.FLAG:
                if text.strip().lower() in ("1", "true", "yes", "on"):
                    argv.append(param.flag)
                continue
            argv.append(param.flag)
            if param.nargs in ("*", "+"):
                argv.extend(text.split())
            else:
                argv.append(text)
        return tuple(argv)


# --------------------------------------------------------------------------- #
# extraction
# --------------------------------------------------------------------------- #
def _literal(node: Optional[ast.AST]):
    if node is None:
        return None
    try:
        return ast.literal_eval(node)
    except Exception:
        return None


def _callee_name(node: Optional[ast.AST]) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    if isinstance(node, ast.Call):
        return _callee_name(node.func)
    return ""


def _classify(flags: tuple[str, ...], dest: str, type_name: str,
              choices: tuple[str, ...], action: str) -> Kind:
    if action in ("store_true", "store_false"):
        return Kind.FLAG
    if choices:
        return Kind.CHOICE
    lowered = (" ".join(flags) + " " + dest).lower()
    if any(hint in lowered for hint in _DIR_HINTS):
        return Kind.DIR
    if type_name == "Path" or any(hint in lowered for hint in _FILE_HINTS):
        return Kind.FILE
    lowered_type = type_name.lower()
    if "int" in lowered_type:
        return Kind.INTEGER
    if "float" in lowered_type:
        return Kind.NUMBER
    return Kind.TEXT


def _dest_for(flags: tuple[str, ...], explicit: Optional[str]) -> str:
    if explicit:
        return explicit
    if not flags:
        return ""
    long_flags = [f for f in flags if f.startswith("--")]
    chosen = long_flags[0] if long_flags else flags[0]
    return chosen.lstrip("-").replace("-", "_")


def _roles(tree: ast.AST) -> tuple[dict, dict, list, str, bool]:
    """Map each variable holding a parser-like object to what it is.

    Two passes are needed over the tree: this one records the parsers, groups
    and subparsers, so the argument pass below can attribute every
    `add_argument` call to the right scope.
    """
    roles: dict[str, str] = {}
    groups: dict[str, MutexGroup] = {}
    subcommands: list[str] = []
    sub_dest = ""
    sub_required = False
    mutex_seq = 0

    for node in ast.walk(tree):
        if not (isinstance(node, ast.Assign) and isinstance(node.value, ast.Call)):
            continue
        call = node.value
        targets = [t.id for t in node.targets if isinstance(t, ast.Name)]
        if not targets:
            continue
        name = _callee_name(call.func)

        if name == "ArgumentParser":
            for target in targets:
                roles[target] = "root"
        elif name == "add_argument_group":
            # A titled group is only cosmetic; its arguments are ordinary ones.
            for target in targets:
                roles[target] = "root"
        elif name == "add_mutually_exclusive_group":
            mutex_seq += 1
            gid = f"group{mutex_seq}"
            required = any(kw.arg == "required" and bool(_literal(kw.value))
                           for kw in call.keywords)
            groups[gid] = MutexGroup(id=gid, required=required)
            for target in targets:
                roles[target] = f"mutex:{gid}"
        elif name == "add_subparsers":
            for kw in call.keywords:
                if kw.arg == "dest":
                    sub_dest = str(_literal(kw.value) or "") or sub_dest
                elif kw.arg == "required":
                    sub_required = bool(_literal(kw.value))
            for target in targets:
                roles[target] = "subparsers"
        elif name == "add_parser" and isinstance(call.func, ast.Attribute):
            owner = call.func.value
            if isinstance(owner, ast.Name) and roles.get(owner.id) == "subparsers":
                label = str(_literal(call.args[0]) or "") if call.args else ""
                if label:
                    subcommands.append(label)
                    for target in targets:
                        roles[target] = f"sub:{label}"

    return roles, groups, subcommands, sub_dest, sub_required


def _hand_enforced(tree: ast.AST) -> frozenset[str]:
    """Flags a script demands itself, via `parser.error("--x is required")`.

    Two skills enforce requirements in code rather than declaring them, so
    argparse's own metadata says the flag is optional and the run still dies
    with exit 2. Only an exact "<flag> is required" message counts: the same
    scripts also raise conditional variants like "--symbol is required in
    explicit mode", which are genuinely situational and must not be turned
    into a field the operator is forced to fill.
    """
    found: set[str] = set()
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "error"
                and node.args):
            continue
        message = _literal(node.args[0])
        if not isinstance(message, str):
            continue
        head, _, tail = message.partition(" ")
        if tail.strip() == "is required" and head.startswith("--"):
            found.add(head)
    return frozenset(found)


def _extract(tree: ast.AST) -> Spec:
    roles, groups, subcommands, sub_dest, sub_required = _roles(tree)
    enforced = _hand_enforced(tree)
    params: list[Param] = []
    seen: set[tuple[str, Optional[str]]] = set()
    order = 0

    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "add_argument"
                and isinstance(node.func.value, ast.Name)):
            continue
        owner = roles.get(node.func.value.id)
        if owner is None:
            continue
        subcommand = owner[4:] if owner.startswith("sub:") else None
        group_id = owner[6:] if owner.startswith("mutex:") else None

        flags = tuple(str(a.value) for a in node.args
                      if isinstance(a, ast.Constant) and isinstance(a.value, str))
        if not flags:
            continue
        kw = {k.arg: k.value for k in node.keywords if k.arg}
        raw_dest = _literal(kw.get("dest"))
        dest = _dest_for(flags, raw_dest if isinstance(raw_dest, str) else None)
        if not dest:
            continue
        if (dest, subcommand) in seen:
            continue
        seen.add((dest, subcommand))

        positional = not flags[0].startswith("-")
        action = str(_literal(kw.get("action")) or "")
        type_name = _callee_name(kw.get("type"))
        raw_choices = _literal(kw.get("choices"))
        choices = (tuple(str(c) for c in raw_choices)
                   if isinstance(raw_choices, (list, tuple, set)) else ())
        has_default = "default" in kw and _literal(kw["default"]) is not None
        default_value = _literal(kw.get("default"))
        nargs_value = _literal(kw.get("nargs"))
        explicit_required = bool(_literal(kw.get("required")))
        # argparse makes a positional required unless it has a default or an
        # nargs that allows zero values.
        required = explicit_required or any(f in enforced for f in flags) or (
            positional and not has_default and nargs_value not in ("?", "*"))

        order += 1
        params.append(Param(
            dest=dest,
            flags=() if positional else flags,
            kind=_classify(flags, dest, type_name, choices, action),
            required=required,
            default=None if default_value is None else str(default_value),
            choices=choices,
            help=str(_literal(kw.get("help")) or ""),
            nargs=None if nargs_value is None else str(nargs_value),
            group=group_id,
            subcommand=subcommand,
            order=order,
        ))
        if group_id and group_id in groups:
            existing = groups[group_id]
            groups[group_id] = replace(
                existing, members=existing.members + (dest,))

    return Spec(
        params=tuple(params),
        groups=tuple(groups.values()),
        subcommands=tuple(dict.fromkeys(subcommands)),
        subcommand_dest=sub_dest or ("command" if subcommands else ""),
        subcommand_required=sub_required or bool(subcommands),
        parsed=bool(params or subcommands),
        note=("" if (params or subcommands)
              else "no argparse definition could be read from this script"),
    )


@lru_cache(maxsize=512)
def _spec_cached(path_str: str, mtime: float, size: int) -> Spec:
    path = Path(path_str)
    try:
        tree = ast.parse(path.read_text(encoding="utf-8", errors="ignore"))
    except Exception as exc:
        return Spec(script=path.name, parsed=False,
                    note=f"could not read the script ({type(exc).__name__})")
    return replace(_extract(tree), script=path.name)


def spec_for(path: Path) -> Spec:
    """Parameter spec for one script. Cached on (path, mtime, size)."""
    try:
        stat = path.stat()
    except OSError:
        return Spec(script=path.name, parsed=False, note="script not found")
    return _spec_cached(str(path), stat.st_mtime, stat.st_size)


def reload() -> None:
    _spec_cached.cache_clear()
