"""Section-6 artifact schemas: one registry keyed by $id, a stdlib validator, canonical JSON,
header/results md5, field classes and the per-artifact check (R-32; TASK-M0-08/09/10).

Pure leaf: stdlib only, reads nothing but its own schema files. `core/rules` and
`core/ficc/macro_artifacts` import from here, never the reverse.
"""
from __future__ import annotations

import copy
import functools
import hashlib
import json
import re
from datetime import date, datetime
from pathlib import Path

SCHEMA_DIR = Path(__file__).resolve().parent / "schemas"
BASE = "quantgen/"
NAMES = ("macro_state", "overlay_decision", "event_calendar", "context_log",
         "model_card_header.macro", "model_card.macro", "governance_event")
HEADER_ID = BASE + "model_card_header.macro.v2.0"
CARD_ID = BASE + "model_card.macro.v2.0"
# reproducibility.determinism.volatile_fields plus tree_hash (ruling 3.1): excluded from results_md5 and replay.
VOLATILE_FIELDS = ("generated_at_utc", "git_hash", "tree_hash")

SUPPORTED = {"$id", "$ref", "$defs", "type", "required", "properties", "const", "enum", "format", "description",
             "items", "minimum", "maximum", "exclusiveMinimum", "exclusiveMaximum", "minItems", "maxItems", "pattern",
             "additionalProperties", "unevaluatedProperties", "allOf", "anyOf", "oneOf", "if", "then", "else"}
_DT = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?Z$")
_TYPES = {"object": dict, "array": list, "string": str, "boolean": bool, "null": type(None)}
_SUBS = ("items", "additionalProperties", "if", "then", "else")
_LISTS = ("allOf", "anyOf", "oneOf")


class SchemaLoadError(Exception):
    pass


def _is_type(v, t):
    if t == "number":
        return isinstance(v, (int, float)) and not isinstance(v, bool)
    if t == "integer":
        return (isinstance(v, int) and not isinstance(v, bool)) or (isinstance(v, float) and v.is_integer())
    return isinstance(v, _TYPES[t])


def _json_eq(a, b):
    if isinstance(a, bool) or isinstance(b, bool):
        return a is b
    return a == b


def _is_num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def close_objects(schema, *, key=None, is_fields=False):
    """Section-6 closed-object rule (L3509), applied once at load to a copy."""
    if isinstance(schema, list):
        for s in schema:
            close_objects(s)
        return
    if not isinstance(schema, dict):
        return
    if ("properties" in schema and key != "extras" and not is_fields
            and "additionalProperties" not in schema and "unevaluatedProperties" not in schema):
        schema["additionalProperties"] = False
    for k, sub in (schema.get("properties") or {}).items():
        close_objects(sub, key=k)
    for k, sub in (schema.get("$defs") or {}).items():
        close_objects(sub, is_fields=(k == "fields"))
    for k in _SUBS:
        if isinstance(schema.get(k), dict):
            close_objects(schema[k])
    for k in _LISTS:
        close_objects(schema.get(k) or [])


class Registry:
    def __init__(self, schemas):
        self.by_id = {}
        for s in schemas:
            s = copy.deepcopy(s)
            close_objects(s)
            if s.get("$id") in self.by_id:
                raise SchemaLoadError("duplicate $id %s" % s.get("$id"))
            self.by_id[s["$id"]] = s
        for root in self.by_id.values():
            self._check(root, root)

    def _check(self, s, root):
        bad = set(s) - SUPPORTED
        if bad:
            raise SchemaLoadError("unsupported keyword(s) %s in %s" % (sorted(bad), root["$id"]))
        if s.get("format") not in (None, "date", "date-time"):
            raise SchemaLoadError("unsupported format %r in %s" % (s["format"], root["$id"]))
        if "$ref" in s:
            try:
                self.resolve(s["$ref"], root)
            except KeyError:
                raise SchemaLoadError("dangling $ref %s in %s" % (s["$ref"], root["$id"]))
        subs = list((s.get("properties") or {}).values()) + list((s.get("$defs") or {}).values())
        subs += [s[k] for k in _SUBS if isinstance(s.get(k), dict)]
        for k in _LISTS:
            subs += s.get(k) or []
        for sub in subs:
            self._check(sub, root)

    def resolve(self, ref, root):
        doc, _, ptr = ref.partition("#")
        node = root if not doc else self.by_id[doc if doc.startswith(BASE) else BASE + doc]
        newroot = node
        for part in [p for p in ptr.split("/") if p]:
            node = node[part]
        return node, newroot

    def node_at(self, schema_id, pointer):
        """Schema node at a JSON pointer over properties/items/additionalProperties/$ref/allOf."""
        node, root = self.by_id[schema_id], self.by_id[schema_id]
        for part in [p for p in pointer.split("/") if p]:
            node, root = self._step(node, root, part)
        return node

    def _step(self, s, root, part):
        for a, r in self._schemas_at(s, root):
            props = a.get("properties") or {}
            if part in props:
                return props[part], r
            if isinstance(a.get("items"), dict) and (part == "*" or part.isdigit()):
                return a["items"], r
            if isinstance(a.get("additionalProperties"), dict):
                return a["additionalProperties"], r
        raise KeyError(part)

    def _schemas_at(self, s, root):
        out = [(s, root)]
        if "$ref" in s:
            out += self._schemas_at(*self.resolve(s["$ref"], root))
        for k in _LISTS + ("then", "else"):
            for sub in (s.get(k) or []) if k in _LISTS else ([s[k]] if isinstance(s.get(k), dict) else []):
                out += self._schemas_at(sub, root)
        return out

    def declared(self, schema, root):
        """Property names statically reachable (the unevaluatedProperties key set)."""
        return {n for a, _ in self._schemas_at(schema, root) for n in (a.get("properties") or {})}

    def validate(self, schema_id, inst):
        root = self.by_id[schema_id]
        errs = []
        self._v(root, root, inst, "", errs)
        return errs

    def _clean(self, s, root, v):
        scratch = []
        self._v(s, root, v, "", scratch)
        return not scratch

    def _v(self, s, root, v, path, errs):
        if "$ref" in s:
            sub, subroot = self.resolve(s["$ref"], root)
            self._v(sub, subroot, v, path, errs)
        for sub in s.get("allOf") or []:
            self._v(sub, root, v, path, errs)
        if "anyOf" in s and not any(self._clean(sub, root, v) for sub in s["anyOf"]):
            errs.append((path, "anyOf"))
        if "oneOf" in s and sum(self._clean(sub, root, v) for sub in s["oneOf"]) != 1:
            errs.append((path, "oneOf"))
        if isinstance(s.get("if"), dict):
            branch = "then" if self._clean(s["if"], root, v) else "else"
            if isinstance(s.get(branch), dict):
                self._v(s[branch], root, v, path, errs)
        if "const" in s and not _json_eq(v, s["const"]):
            errs.append((path, "const %r" % (s["const"],)))
        if "enum" in s and not any(_json_eq(v, e) for e in s["enum"]):
            errs.append((path, "enum %r" % (s["enum"],)))
        if "type" in s:
            types = s["type"] if isinstance(s["type"], list) else [s["type"]]
            if not any(_is_type(v, t) for t in types):
                errs.append((path, "type %s" % types))
                return
        if _is_num(v):
            if v != v or v in (float("inf"), float("-inf")):
                errs.append((path, "not finite"))
            if "minimum" in s and v < s["minimum"]:
                errs.append((path, "minimum %s" % s["minimum"]))
            if "maximum" in s and v > s["maximum"]:
                errs.append((path, "maximum %s" % s["maximum"]))
            if "exclusiveMinimum" in s and v <= s["exclusiveMinimum"]:
                errs.append((path, "exclusiveMinimum %s" % s["exclusiveMinimum"]))
            if "exclusiveMaximum" in s and v >= s["exclusiveMaximum"]:
                errs.append((path, "exclusiveMaximum %s" % s["exclusiveMaximum"]))
        if isinstance(v, str):
            if "format" in s and not _format_ok(s["format"], v):
                errs.append((path, "format %s" % s["format"]))
            if "pattern" in s and not re.search(s["pattern"], v):
                errs.append((path, "pattern %s" % s["pattern"]))
        if isinstance(v, list):
            if "minItems" in s and len(v) < s["minItems"]:
                errs.append((path, "minItems %s" % s["minItems"]))
            if "maxItems" in s and len(v) > s["maxItems"]:
                errs.append((path, "maxItems %s" % s["maxItems"]))
            if isinstance(s.get("items"), dict):
                for i, x in enumerate(v):
                    self._v(s["items"], root, x, "%s/%d" % (path, i), errs)
        if isinstance(v, dict):
            for r in s.get("required") or []:
                if r not in v:
                    errs.append(("%s/%s" % (path, r), "required"))
            props = s.get("properties") or {}
            for k, x in v.items():
                if k in props:
                    self._v(props[k], root, x, "%s/%s" % (path, k), errs)
            ap = s.get("additionalProperties")
            if ap is False:
                for k in v:
                    if k not in props:
                        errs.append(("%s/%s" % (path, k), "undeclared"))
            elif isinstance(ap, dict):
                for k, x in v.items():
                    if k not in props:
                        self._v(ap, root, x, "%s/%s" % (path, k), errs)
            if s.get("unevaluatedProperties") is False:
                known = self.declared(s, root)
                for k in v:
                    if k not in known:
                        errs.append(("%s/%s" % (path, k), "undeclared"))


def _format_ok(fmt, v):
    try:
        if fmt == "date-time":
            return bool(_DT.match(v)) and bool(datetime.fromisoformat(v[:19]))
        if fmt == "date":
            return len(v) == 10 and bool(date.fromisoformat(v))
    except ValueError:
        return False
    return True


@functools.lru_cache(maxsize=1)
def registry() -> Registry:
    files = sorted(SCHEMA_DIR.glob("*.v2.0.json"))
    reg = Registry([json.loads(p.read_text(encoding="utf-8")) for p in files])
    want = {BASE + n + ".v2.0" for n in NAMES}
    if set(reg.by_id) != want:
        raise SchemaLoadError("schema set mismatch: %s" % sorted(set(reg.by_id) ^ want))
    if _any_name(reg.by_id, "kish"):
        raise SchemaLoadError("the Kish N-hat is never a field (L4092)")
    return reg


def _any_name(node, needle):
    if isinstance(node, dict):
        return any(needle in k.lower() for k in (node.get("properties") or {})) or \
            any(_any_name(v, needle) for v in node.values())
    return isinstance(node, list) and any(_any_name(v, needle) for v in node)


def short_name(name: str) -> str:
    n = name
    for prefix in (BASE, "quantgen."):
        if n.startswith(prefix):
            n = n[len(prefix):]
    if n.endswith(".v2.0"):
        n = n[:-5]
    if n not in NAMES:
        raise KeyError("unknown schema %r" % (name,))
    return n


def schema_id(name: str) -> str:
    return BASE + short_name(name) + ".v2.0"


def load_schema(name: str) -> dict:
    """The closed schema (a copy) by short name, $id or `schema` const."""
    return copy.deepcopy(registry().by_id[schema_id(name)])


def validate(name: str, obj) -> list[str]:
    """[] = valid; each message starts with the JSON pointer of the offending position."""
    return [_msg(p, m) for p, m in registry().validate(schema_id(name), obj)]


def _msg(path, message):
    return "%s: %s" % (path or "/", message)


def enum_of(name: str, pointer: str) -> tuple:
    return tuple(registry().node_at(schema_id(name), pointer)["enum"])


HEADER_FIELDS = frozenset(registry().by_id[HEADER_ID]["$defs"]["fields"]["properties"])
RESULT_FIELDS = frozenset(registry().by_id[CARD_ID]["properties"])
if HEADER_FIELDS & RESULT_FIELDS:
    raise SchemaLoadError("header and result field sets overlap: %s" % sorted(HEADER_FIELDS & RESULT_FIELDS))


# --------------------------------------------------------------------------- #
# Canonical JSON and hashes (reproducibility.determinism.canonical_json)
# --------------------------------------------------------------------------- #
def canonical_json(obj) -> str:
    """Sorted keys, no insignificant whitespace, floats via repr, UTF-8 text; NaN/inf refused."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def md5_hex(data) -> str:
    if isinstance(data, str):
        data = data.encode("utf-8")
    return hashlib.md5(data).hexdigest()


def strip_volatile(artifact: dict) -> dict:
    return {k: v for k, v in artifact.items() if k not in VOLATILE_FIELDS}


def header_md5(header: dict) -> str:
    """md5 over the header fields only, excluding header_md5 itself (L3913, F-2)."""
    return md5_hex(canonical_json({k: v for k, v in header.items() if k in HEADER_FIELDS and k != "header_md5"}))


def results_md5(card: dict) -> str:
    """md5 over the result fields, excluding results_md5 and the volatile fields (L3913, F-3)."""
    skip = ("results_md5",) + VOLATILE_FIELDS
    return md5_hex(canonical_json({k: v for k, v in card.items() if k in RESULT_FIELDS and k not in skip}))


def split_card(card: dict) -> tuple[dict, dict]:
    return ({k: v for k, v in card.items() if k in HEADER_FIELDS},
            {k: v for k, v in card.items() if k in RESULT_FIELDS})


# --------------------------------------------------------------------------- #
# Field classes (R-32 L3370): unclassified = acting = fail closed
# --------------------------------------------------------------------------- #
DISPLAY_PATHS = {
    "macro_state": (
        "/owner_decisions", "/alerts", "/annotations", "/refusal_books", "/forward_sim",
        "/flags/gap_sessions", "/flags/kr_open_gap_event", "/flags/var_display_scale",
        "/flags/hedge_credit_off", "/flags/hedge_failure", "/flags/classic_risk_off", "/flags/fx_hedge_credit",
        "/flags/hedge_reasons", "/flags/hedge_stale_inputs",
        "/vol/display_label_rel", "/vol/display_label_abs", "/vol/label_method_rel", "/vol/label_method_abs",
        "/vol/alt_sigma_logged", "/vol/label_status",
    ),
    "overlay_decision": ("/reasons", "/refusal", "/forward_sim"),
}
NON_ACTING_ROLES = ("forward_sim", "risk_model", "context", "history")
# Whole-artifact refusal class: written to quarantine, alerted, never a HALT (P9, P18).
WHOLE_REFUSAL = ("context_log", "event_calendar", "model_card.macro", "model_card_header.macro", "governance_event")
_INPUT_ITEM = re.compile(r"^/inputs/(\d+)(/|$)")


def field_class(name: str, pointer: str, obj=None) -> str:
    """"acting" | "display" | "context". `obj` resolves the role of an inputs[] entry."""
    short = short_name(name)
    if short not in DISPLAY_PATHS:
        return "context"
    for q in DISPLAY_PATHS[short]:
        if pointer == q or pointer.startswith(q + "/"):
            return "display"
    m = _INPUT_ITEM.match(pointer)
    if m and isinstance(obj, dict) and isinstance(obj.get("inputs"), list):
        i = int(m.group(1))
        if i < len(obj["inputs"]) and isinstance(obj["inputs"][i], dict) \
                and obj["inputs"][i].get("role") in NON_ACTING_ROLES:
            return "display"
    return "acting"


# --------------------------------------------------------------------------- #
# Cross-field checks stated in section 6 but outside the keyword subset
# --------------------------------------------------------------------------- #
def _pass_like(card):
    return isinstance(card, dict) and card.get("verdict") == "PASS" \
        and card.get("disposition") in ("RECOMMENDATION", "BUILD_AS_INSURANCE")


def _acts_in_recommended(card):
    return _pass_like(card) or (isinstance(card, dict) and card.get("disposition") == "INVARIANT_STEP")


def _card_ref_errs(path, card):
    errs = []
    if not isinstance(card, dict):
        return errs
    da = card.get("displayed_as")
    if (da in ("recommendation", "insurance")) != _pass_like(card):
        errs.append((path + "/displayed_as", "S1: recommendation|insurance iff verdict PASS and disposition "
                                             "RECOMMENDATION|BUILD_AS_INSURANCE"))
    if (da == "invariant") != (card.get("disposition") == "INVARIANT_STEP"):
        errs.append((path + "/displayed_as", "S2: invariant iff disposition INVARIANT_STEP"))
    return errs


def _overlay_semantics(o):
    errs = _card_ref_errs("/vol_scale_card", o.get("vol_scale_card"))
    for key in ("multipliers", "forward_sim", "refusal"):
        for i, m in enumerate(o.get(key) if isinstance(o.get(key), list) else []):
            if isinstance(m, dict):
                errs += _card_ref_errs("/%s/%d/card" % (key, i), m.get("card"))
    vs, vsr = o.get("vol_scale"), o.get("vol_scale_recommended_book")
    if _is_num(vs) and _is_num(vsr):
        want = vs if _pass_like(o.get("vol_scale_card")) else 1.0
        if abs(vsr - want) > 1e-12:
            errs.append(("/vol_scale_recommended_book", "S3: vol_scale when its card is PASS, else 1.0"))
    if o.get("family") != "market_gross":
        for k in ("ladder", "post_rearm_cap"):
            if o.get(k) is not None:
                errs.append(("/" + k, "S4: market_gross only"))
    mults = o.get("multipliers")
    if isinstance(mults, list) and all(isinstance(m, dict) and _is_num(m.get("value")) for m in mults):
        ladder, cap = o.get("ladder"), o.get("post_rearm_cap")
        spec = min([1.0] + [m["value"] for m in mults] + [x for x in (ladder, cap) if _is_num(x)])
        # F-10: the ladder enters the recommended book as 1.0 unless an INVARIANT_STEP says otherwise (M8)
        rec = min([1.0] + [m["value"] for m in mults if _acts_in_recommended(m.get("card"))]
                  + ([cap] if _is_num(cap) else []))
        for k, want in (("overlay_min", spec), ("overlay_applied_spec_book", spec),
                        ("overlay_applied_recommended_book", rec)):
            if _is_num(o.get(k)) and abs(o[k] - want) > 1e-12:
                errs.append(("/" + k, "S5: expected %r from min() over the recorded factors" % want))
    return errs


def _state_semantics(o):
    errs = []
    rt, fl = o.get("runtime"), o.get("flags")
    if isinstance(rt, list) and isinstance(fl, dict) and "engine_state" in fl:
        for e in rt:
            if isinstance(e, dict) and e.get("book_id") == "recommended:%s" % o.get("market") \
                    and e.get("engine_state") != fl["engine_state"]:
                errs.append(("/flags/engine_state", "S6: must equal runtime[recommended:<market>].engine_state"))
    return errs


def _extras_bounds(o):
    """extras.w_target / w_held are checked in code, in [0, 1] (R-26, L3370)."""
    errs = []
    ex = o.get("extras")
    if isinstance(ex, dict):
        for key in ("w_target", "w_held"):
            if key in ex:
                _walk_bounds(ex[key], "/extras/" + key, errs)
    return errs


def _walk_bounds(v, path, errs):
    if isinstance(v, dict):
        for k, x in v.items():
            _walk_bounds(x, "%s/%s" % (path, k), errs)
    elif isinstance(v, list):
        for i, x in enumerate(v):
            _walk_bounds(x, "%s/%d" % (path, i), errs)
    elif not (_is_num(v) and v == v and 0.0 <= v <= 1.0):
        errs.append((path, "bounds [0, 1]"))


def _card_semantics(c):
    errs = []
    v, d = c.get("verdict"), c.get("disposition")
    if (d in ("RECOMMENDATION", "BUILD_AS_INSURANCE")) != (v == "PASS"):
        errs.append(("/disposition", "K1: RECOMMENDATION|BUILD_AS_INSURANCE iff verdict PASS"))
    if v == "PASS":
        want = {"BUILD_NOW": "RECOMMENDATION", "BUILD_AS_INSURANCE": "BUILD_AS_INSURANCE"}.get(c.get("build_status_on_pass"))
        if want and d != want:
            errs.append(("/disposition", "K2: build_status_on_pass %s requires %s" % (c.get("build_status_on_pass"), want)))
    if d == "BUILD_AS_INSURANCE" and (c.get("class") != "CARD-P" or c.get("label") is None):
        errs.append(("/disposition", "K3: BUILD_AS_INSURANCE needs class CARD-P and a label"))
    if d == "INVARIANT_STEP" and c.get("family_id") != "R-31":
        errs.append(("/disposition", "K4: INVARIANT_STEP is reserved for R-31"))
    try:
        if c.get("header_md5") != header_md5(c):
            errs.append(("/header_md5", "K5: header_md5 mismatch"))
        if c.get("results_md5") != results_md5(c):
            errs.append(("/results_md5", "K5: results_md5 mismatch"))
    except (TypeError, ValueError) as exc:
        errs.append(("", "K5: not canonicalisable (%s)" % exc))
    for a, b in (("start_band", "start_band_results"), ("midpoint_halves", "midpoint_halves_results")):
        if c.get(a) is not None and c.get(b) is None:
            errs.append(("/" + b, "K6: %s declared without %s" % (a, b)))
    return errs


_FUTURES_BOOKS = ("KOSPI200_futures", "mini_KOSPI200_futures", "CME_micro_ES", "FX_KRX_USD_futures")


def _header_rules(h, acting_long_sample, seed_study):
    """H3, H5-H10, H15: pure header rules (section 8.4 L4087-4089, L4851, L3952, L4882)."""
    errs = []
    if acting_long_sample:
        for k in ("start_band", "midpoint_halves"):
            if h.get(k) is None:
                errs.append(("/" + k, "H3: null on an acting long-sample card"))
    if h.get("checks") != "gate_package_%s" % h.get("gate_package_version"):
        errs.append(("/checks", "H5: must be gate_package_<gate_package_version>"))
    want = {"CARD-P": "S_same_average_exposure", "CARD-O": "overlay_off"}.get(h.get("class"))
    if want and h.get("comparator") != want:
        errs.append(("/comparator", "H6: %s requires %s" % (h.get("class"), want)))
    if h.get("build_status_on_pass") == "BUILD_AS_INSURANCE" and (h.get("class") != "CARD-P" or h.get("label") is None):
        errs.append(("/build_status_on_pass", "H7: BUILD_AS_INSURANCE needs class CARD-P and a label"))
    if h.get("class") == "CARD-P" and h.get("claim_type") != "protection":
        errs.append(("/claim_type", "H8: a protective rule claims protection only (L4851)"))
    if _is_num(h.get("no_trade_band")) and h["no_trade_band"] == 0.10 \
            and h.get("instrument_book") not in ("KRX_stock_book", "US_shares_KIS"):
        errs.append(("/no_trade_band", "H9: 0.10 only on KRX_stock_book and US_shares_KIS"))
    if h.get("instrument_book") == "multi_line" and not h.get("instrument_lines"):
        errs.append(("/instrument_lines", "H10: multi_line needs instrument_lines"))
    if h.get("instrument_book") in _FUTURES_BOOKS and h.get("roll_calendar") is None:
        errs.append(("/roll_calendar", "H10: a futures book needs roll_calendar"))
    if seed_study is not None and h.get("seed") != seed_study:
        errs.append(("/seed", "H15: seed must equal reproducibility.seed_study (%r)" % seed_study))
    return errs


def header_issues(header: dict, *, acting_long_sample: bool = True, committed_md5: str | None = None,
                  seed_study: int | None = None) -> list[str]:
    """Schema + H1-H10, H15 for a pre-registration header. The store-dependent R-26 clauses
    (H11-H13) live in core/rules validate_card_header, which calls this first."""
    if not isinstance(header, dict):
        return [_msg("", "type ['object']")]
    errs = registry().validate(HEADER_ID, header) + _header_rules(header, acting_long_sample, seed_study)
    try:
        want = header_md5(header)
        if header.get("header_md5") != want:
            errs.append(("/header_md5", "H4: header_md5 mismatch"))
        if committed_md5 is not None and committed_md5 != want:
            errs.append(("/header_md5", "H4: differs from the committed header"))
    except (TypeError, ValueError) as exc:
        errs.append(("", "H4: not canonicalisable (%s)" % exc))
    return [_msg(p, m) for p, m in errs]


def check_artifact(name: str, obj) -> tuple[bool, list[str], bool]:
    """(ok, issues, acting_failure). acting_failure is True only for a macro_state / overlay_decision
    whose errors touch an acting field (bounds_ok HALT scope, wired at M8); the whole-refusal kinds
    never HALT."""
    short = short_name(name)
    if not isinstance(obj, dict):
        return False, [_msg("", "type ['object']")], short not in WHOLE_REFUSAL
    errs = registry().validate(schema_id(short), obj)
    if short == "overlay_decision":
        errs += _extras_bounds(obj) + _overlay_semantics(obj)
    elif short == "macro_state":
        errs += _extras_bounds(obj) + _state_semantics(obj)
    elif short == "context_log" and obj.get("as_of_utc") != obj.get("decision_utc"):
        errs.append(("/as_of_utc", "S8: must equal decision_utc"))
    elif short == "model_card.macro":
        errs += _card_semantics(obj)
    issues = [_msg(p, m) for p, m in errs]
    if short in WHOLE_REFUSAL:
        return not errs, issues, False
    return not errs, issues, any(field_class(short, p, obj) == "acting" for p, _ in errs)


def card_issues(card: dict, *, committed_header: dict | None = None,
                acting_long_sample: bool = True, seed_study: int | None = None) -> list[str]:
    """check_artifact errors + K7 (pure header rules on the header part) + K8 (committed header)."""
    _, issues, _ = check_artifact("model_card.macro", card)
    if not isinstance(card, dict):
        return issues
    head, _ = split_card(card)
    issues += [_msg(p, m) for p, m in _header_rules(head, acting_long_sample, seed_study)]
    if committed_header is not None:
        for k in sorted(HEADER_FIELDS):
            if k != "header_md5" and committed_header.get(k) != head.get(k):
                issues.append(_msg("/" + k, "K8: differs from the committed header"))
    return issues
