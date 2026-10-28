# Repo map: the compliance follow-up (area key "followup")

Mapped read-only at `main` 995534b on 2026-10-24. Sources read in full: the execution ledger (245 lines),
`tests/compliance_guards.py`, the D12 part of `core/compliance/owner.py` (lines 1-1017), `core/compliance/rules.py`
(the row loader, lines 380-565), the relevant parts of `gate.py`, `alerts.py`, `tools/signer/sign.py`, spec sections
1-6.4, 8, 9, 13. Stdlib claims come from the venv's own stdlib sources (Python 3.13.14), read as text, never imported.
Inside a backtick quote, any backticks of the source text are dropped (markdown cannot nest them); the ledger
inventory in section 8 reproduces each ledger line exactly, outside backticks.
Classes used below: FOLLOWUP = belongs in the compliance hardening plan; EXEC = carried to the execution spec; ODDS =
belongs to the odds plan; OWNER = owner act; FIXED = already fixed; ACCEPT = accepted, cosmetic or harness only.

## 0. State the follow-up starts from

* [state] HEAD is 995534b on `main`; the `compliance-gate` branch is merged and gone.
   EVIDENCE: `git log --oneline -1` `995534b test: full run after the final review wave`; `git branch -a` prints only `* main`
   IMPACT: The follow-up branches from main (A.0 used a named branch; pick a new one, e.g. `compliance-followup`).
* [state] No owner key and no signature exist yet, so no code or table approval is in force.
   EVIDENCE: core/compliance/owner.py:24 `PUBKEY_PATH = Path(__file__).with_name("owner_pubkey.pem")   # the trust anchor; absent until owner act 1 (P24)`; `ls core/compliance/owner_pubkey.pem` -> "No such file or directory"; ledger:240 `real-home --check exit 3`
   IMPACT: Any edit to core/compliance/*.py (or the shipped tables) costs no re-signing today. Once the owner signs `code_approved` (owner act 2), every follow-up code change needs a fresh owner signature, and a loader change can turn an approved table INVALID. Land the follow-up before owner acts 2-3, or say in the plan that the owner re-signs.
* [state] The D14 code hash covers core/odds too, so the odds build and the follow-up both move it.
   EVIDENCE: core/compliance/owner.py:773 `todo = [p for sub in ("compliance", "odds") for p in sorted((root / "core" / sub).glob("*.py"))]`
   IMPACT: Order the two plans so the owner signs once (both landed), or state the second re-sign. tests/ is outside the closure, so guard-only changes do not move the hash.
* [line endings] Every file the follow-up touches is LF; the repo forbids conversion.
   EVIDENCE: .gitattributes:2 `* -text`; `git ls-files --eol` gives `i/lf    w/lf    attr/-text` for tests/compliance_guards.py, core/compliance/rules.py, owner.py, gate.py, kr_rules.yaml, core/odds/venues.yaml, tests/compliance_tables.py, tests/compliance_owner.py, tools/signer/sign.py; `i/crlf  w/crlf` for tests/run_all.py, README.md, config.py
   IMPACT: Edit tool only (never `sed -i`); README.md and tests/run_all.py stay CRLF; `git diff --stat` must equal `--ignore-cr-at-eol` (plan:16777).
* [process] Test-run rules from Appendix A.0 still apply.
   EVIDENCE: docs/superpowers/plans/2026-10-23-compliance-gate.md:16763-16765 `Run one suite: .venv/Scripts/python.exe tests/run_all.py --suite compliance from the repo root. A suite run rewrites the TRACKED file qa/acceptance_results.json; restore it with git checkout -- qa/acceptance_results.json`; `git ls-files qa/acceptance_results.json` lists it
   IMPACT: Every task's verify step restores qa/acceptance_results.json; only the final full run commits it; check that no other run_all.py is running first (plan:16766-16771).
* [count] The compliance suite count the follow-up starts from.
   EVIDENCE: README.md:839 `| 315 PASS / 2 NOT_RUN |`; ledger:240 `compliance 315/317`
   IMPACT: The plan's final task updates this README row (CRLF file) after its full run.
* [pending] Task 16 steps 7-9 (daily alert task, memory notes, GPT check) are not recorded as done.
   EVIDENCE: ledger:235 `Step 7 (scheduled task) is an owner gate the controller asks; Steps 8-10 are controller bookkeeping; Step 9 (GPT) waits until after 2026-10-30 14:40`; ledger:236 `steps 1-6 done 355f978`
   IMPACT: GPT's final check (plan:16717-16734, after 2026-10-30 14:40) may produce more compliance findings; the follow-up plan should either run after it or leave room to absorb it.

## 1. Guards: xml.dom, profile/pdb/bdb/trace and the rest (ledger:242)

* [guards: parked item] The parked text, verbatim.
   EVIDENCE: ledger:242 `Final: parked — xml.dom (incl. xml.dom.xmlbuilder DOMBuilder.parseURI / DOMEntityResolver) and profile/pdb/bdb/trace are not in the import bans — Ruling: park as a small guards follow-up; nothing in core/ imports xml or these modules and the T-RO-01/test_08/09 scans plus review cover current code — cost if wrong: a future core/compliance file could fetch a URL through xml.dom without tripping the guard`
   IMPACT: Scope of the guards task: tests/compliance_guards.py only (no product code changes, no code-hash change).
* [guards: current list] NETWORK_MODULES, verbatim.
   EVIDENCE: tests/compliance_guards.py:39-41 `NETWORK_MODULES = ("urllib", "http", "socket", "_socket", "socketserver", "selectors", "ssl", "smtplib", "ftplib", "imaplib", "poplib", "nntplib", "telnetlib", "xmlrpc", "asyncio", "webbrowser", "multiprocessing", "wsgiref", "xml.sax", "xml.dom.pulldom", "xml.dom.expatbuilder", "logging.handlers")`
   IMPACT: webbrowser, xmlrpc, urllib, ftplib are already banned; http.server is banned through "http" (prefix rule below). nntplib and telnetlib are gone from 3.13 (`sys.stdlib_module_names` has neither), so they are refused anyway as non-stdlib; keeping them is harmless.
* [guards: current list] NETWORK_CALLS, DYNAMIC_NAMES, DYNAMIC_MODULES, FORBIDDEN_MODULES, HTTP_VERBS, DEF_NAMES, verbatim.
   EVIDENCE: tests/compliance_guards.py:42 `NETWORK_CALLS = frozenset({"urlopen", "urlretrieve", "create_connection"})`; :49 `DYNAMIC_NAMES = frozenset({"__import__", "import_module", "exec_module", "load_module", "exec", "eval"})`; :50-51 `DYNAMIC_MODULES = ("importlib.util", "importlib.machinery", "runpy", "pkgutil", "zipimport", "pydoc", "timeit", "code", "cProfile")`; :43-44 `FORBIDDEN_MODULES = ("core.engine.orders", "core.quant.forward_sim", "core.quant.refusal", "core.ficc.context_log", "core.ficc.macro", "core.ficc.flows_log", "core.skills.macro_daily")`; :33 `HTTP_VERBS = frozenset({"post", "put", "delete", "patch", "request"})`; :32 `DEF_NAMES = frozenset({"transfer", "withdraw", "deposit_address"})`
   IMPACT: pydoc and cProfile are banned (final wave); profile, pdb, bdb, trace are not.
* [guards: current list] Raw-text and clock lists, verbatim.
   EVIDENCE: tests/compliance_guards.py:27-30 `RAW_CI = ("private_key", "seed_phrase", "order_cash", "order-cash", "place_order", "submit_order", "tttc0802u", "tttc0801u", "vttc0802u", "r18_research_log", "r18_break_log", "context_log/", "tests.reference", "reference_mode")` / `RAW_CS = ("CANO", "KIS_ACCOUNT", "ACNT_PRDT_CD")`; :53-56 `CLOCKS = {"datetime": {"now", "utcnow", "today"}, "date": {"today"}, "time": {"time", "time_ns", "monotonic", ... "thread_time_ns"}}`
   IMPACT: For completeness; the ledger's clock minor (L64) still holds (no clock_gettime).
* [guards: matching rule] A dotted ban covers the module and everything below it, never its parent.
   EVIDENCE: tests/compliance_guards.py:169-170 `net = [t for t in [module] + [f"{module}.{n}" for n in names] for m in NETWORK_MODULES if t == m or t.startswith(m + ".")]`; :35-36 comment `a dotted name bans the module and everything below it, not its parent`
   IMPACT: Adding "xml.dom" bans xml.dom, xml.dom.minidom, xml.dom.xmlbuilder, pulldom, expatbuilder, domreg in one entry; "xml.dom.pulldom" and "xml.dom.expatbuilder" become redundant. xml.etree stays allowed.
* [guards: scope] The network ban and allowlist scan core/compliance only; the dynamic-import ban scans core/compliance AND core/odds.
   EVIDENCE: tests/compliance_guards.py:340 `hits = [h for rel, src in _scope(COMPLIANCE).items() for h in _allowlist_hits(rel, src)]`; :300-301 `hits = [h for rel, src in _scope(COMPLIANCE, ODDS).items() for h in _forbidden_hits(rel, src) + _dynamic_hits(rel, src)]`; :269 http hits `_scope(COMPLIANCE)`; :361 clock `_scope(COMPLIANCE)`; :233 raw `_scope(COMPLIANCE, ODDS)`
   IMPACT: Anything added to DYNAMIC_MODULES / DYNAMIC_NAMES also binds the odds plan's core/odds files (bars.py, models.py, ...). Anything added to NETWORK_MODULES does not (core/odds does network through seams, spec:166-168). Put a code-execution route in DYNAMIC_*, a pure network route in NETWORK_MODULES.
* [guards: probe] Every candidate below passes all four checkers today (no hit).
   EVIDENCE: running tests.compliance_guards._allowlist_hits/_dynamic_hits/_http_hits/_forbidden_hits on synthetic sources (read-only probe): `import xml.dom`, `from xml.dom import minidom`, `import xml.dom.xmlbuilder`, `import profile`, `import pdb`, `import bdb`, `import trace`, `import doctest`, `import unittest.mock`, `import logging.config`, `import antigravity`, `import tkinter`, `import _tkinter`, `import turtle`, `import idlelib`, `import pickle`, `import shelve`, `import marshal`, `import site`, `import importlib.resources`, `import importlib._bootstrap`, `import ensurepip`, `import ctypes`, `import _ssl`, `import _overlapped`, `import _winapi`, `x = compile(s, "x", "exec")`, `f = types.FunctionType(code, {})` -> all "- - - -"; `import http.server`, `import xmlrpc.server`, `import webbrowser`, `import ftplib`, `import urllib.parse`, `import telnetlib` -> allowlist hit
   IMPACT: These are the gaps the guards follow-up closes; each new entry needs a positive control in the same test (the file's rule: "Every test first proves its checker catches a synthetic offender", guards:4-5).
* [guards: xml.dom] xml.dom.xmlbuilder fetches a URL with urllib.
   EVIDENCE: Lib/xml/dom/xmlbuilder.py:180-185 `def parseURI(self, uri): ... input = DOMEntityResolver().resolveEntity(None, uri)`; :193-194 `import urllib.request` / `fp = urllib.request.urlopen(input.systemId)`; :220 `source.byteStream = self._get_opener().open(systemId)`; :245-246 `return urllib.request.build_opener()`; :373-378 `def createDOMBuilder(self, mode, schemaType): ... return DOMBuilder()`
   IMPACT: Ban "xml.dom" in NETWORK_MODULES (compliance scope).
* [guards: xml.dom] minidom and even the bare xml.dom package hand out that builder, so banning only xmlbuilder is not enough.
   EVIDENCE: Lib/xml/dom/minidom.py:23 `from xml.dom.xmlbuilder import DOMImplementationLS, DocumentLS`; :1428 `class DOMImplementation(DOMImplementationLS):`; Lib/xml/dom/__init__.py:140 `from .domreg import getDOMImplementation, registerDOMImplementation`; Lib/xml/dom/domreg.py:56-57 `mod = __import__(mod, {}, {}, ['getDOMImplementation'])` / `return mod.getDOMImplementation()`
   IMPACT: `xml.dom.getDOMImplementation().createDOMBuilder(1, None).parseURI(url)` needs only `import xml.dom`; the ban must be the whole `xml.dom` package.
* [guards: xml.dom] The current negative control asserts minidom is ALLOWED, and the docstring calls it allowed.
   EVIDENCE: tests/compliance_guards.py:332-333 `assert not _allowlist_hits(X, "import logging\nfrom logging import getLogger\nimport xml.etree.ElementTree\n" "from xml.etree import ElementTree\nfrom xml.dom import minidom\n")`; :259-262 `the allowed xml.dom.minidom hands out an xml.dom.xmlbuilder DOMBuilder whose parseURI opens a URL with urllib.request ... All three are left to review.`; :253-255 `two xml.dom modules that are not fetchers themselves: pulldom, built on xml.sax, and expatbuilder, which imports xml.dom.xmlbuilder`
   IMPACT: The follow-up must move `from xml.dom import minidom` from this negative control into the positive list at :324-329, keep `import xml.etree.ElementTree` / `from xml.etree import ElementTree` as the negative control, replace "xml.dom.pulldom", "xml.dom.expatbuilder" by "xml.dom" at :41, and rewrite the docstring at :248-262 (drop the minidom route from "left to review").
* [guards: xml.etree] xml.etree does not fetch: ElementInclude opens local files only.
   EVIDENCE: Lib/xml/etree/ElementInclude.py:89 `with open(href, 'rb') as file:`; :53 `from urllib.parse import urljoin` (parsing only)
   IMPACT: Keep xml.etree allowed (the existing negative control).
* [guards: profile/pdb/bdb/trace] Each runs code given as a string.
   EVIDENCE: Lib/profile.py:425 `exec(cmd, globals, locals)`; Lib/bdb.py:680 `exec(cmd, globals, locals)` and :700 `return eval(expr, globals, locals)`; Lib/pdb.py:2342 `def run(statement, globals=None, locals=None):` and :791 `exec(code, globals, locals)`; Lib/trace.py:456 `exec(cmd, globals, locals)`
   IMPACT: Add "profile", "pdb", "bdb", "trace" to DYNAMIC_MODULES (the same reason guards:45-46 gives for timeit, code and cProfile). This binds core/odds too, which is fine (no odds module needs them).
* [guards: not needed] pstats, tracemalloc and faulthandler run no code from strings and open no connection.
   EVIDENCE: Lib/pstats.py:26 `import marshal` and :143 `self.stats = marshal.load(f)` (profile data, not code); a scan of Lib/tracemalloc.py for `exec(`, `eval(`, `__import__`, `import_module` found nothing; faulthandler is a C module (no Lib source)
   IMPACT: Leave them off the lists; say so in the plan so a reviewer does not re-raise them.
* [guards: also missing] doctest executes example strings and imports by name.
   EVIDENCE: Lib/doctest.py:1398 `exec(compile(example.source, filename, "single",`; :2755 `exec(src, globs, globs)`; :227 `return __import__(module, globals(), locals(), ["*"])`
   IMPACT: Add "doctest" to DYNAMIC_MODULES.
* [guards: also missing] unittest imports by string (mock.patch targets, the loader).
   EVIDENCE: Lib/unittest/mock.py:1683 `return partial(pkgutil.resolve_name, target), attribute`; Lib/unittest/loader.py:137 `module = __import__(module_name)`
   IMPACT: Add "unittest" to DYNAMIC_MODULES (core never needs it; tests may import anything, guards scan core only). The ledger already named this route: ledger:74 `unittest.mock.asyncio, logging.config.dictConfig class strings reach banned modules`.
* [guards: also missing] logging.config imports by string, carries logging.handlers, and opens a TCP listener.
   EVIDENCE: Lib/logging/config.py:31 `import logging.handlers`; :39 `from socketserver import ThreadingTCPServer, StreamRequestHandler`; :387 `importer = staticmethod(__import__)`; :938 `def listen(port=DEFAULT_LOGGING_CONFIG_PORT, verify=None):`; :1013 `ThreadingTCPServer.__init__(self, (host, port), handler)`
   IMPACT: Add "logging.config" (DYNAMIC_MODULES covers both scopes; it is a dynamic import and a network route). The existing negative control `import logging` / `from logging import getLogger` (guards:332) stays valid.
* [guards: also missing] `import antigravity` opens a URL in the browser at import time.
   EVIDENCE: Lib/antigravity.py:2 `import webbrowser`; :5 `webbrowser.open("https://xkcd.com/353/")`
   IMPACT: Add "antigravity" to NETWORK_MODULES.
* [guards: also missing] tkinter embeds a Tcl interpreter whose bundled http package opens sockets.
   EVIDENCE: Lib/tkinter/__init__.py:38 `import _tkinter # If this fails your Python may not be configured for Tk`; :2582 `def Tcl(screenName=None, baseName=None, className='Tk', useTk=False):`; base Python DLLs/_tkinter.pyd and tcl/tcl8.6/http1.0/http.tcl:142-144 `set s [socket $phost $pport]` / `set s [socket $host $port]`
   IMPACT: Add "tkinter", "_tkinter", "turtle" (Lib/turtle.py:101 `import tkinter as TK`), "turtledemo" and "idlelib" (Lib/idlelib/run.py:590 `exec(code, self.locals)`). `.eval(` on a Tcl object is already caught by the attribute check of DYNAMIC_NAMES (guards:153-156); `tk.call("socket", ...)` is not.
* [guards: also missing] pickle/shelve/marshal load code or import by name from data.
   EVIDENCE: Lib/pickle.py:1608 `def find_class(self, module, name):` and :1616 `__import__(module, level=0)`; Lib/shelve.py:59 `from pickle import DEFAULT_PROTOCOL, Pickler, Unpickler`
   IMPACT: Candidate DYNAMIC_MODULES "pickle", "_pickle", "shelve", "marshal". Because DYNAMIC binds core/odds, confirm first that the odds bars cache does not need pickle (spec:136 says only "own sha-manifest cache"; no pickle use exists in core/, data/ or config.py today: grep found none). Open question.
* [guards: also missing] site executes `import` lines of .pth files; ensurepip runs pip through runpy.
   EVIDENCE: Lib/site.py:162 `def addpackage(sitedir, name, known_paths):` and :207 `exec(line)`; Lib/ensurepip/__init__.py:71-75 `import runpy` ... `runpy.run_module("pip", run_name="__main__", alter_sys=True)`
   IMPACT: Candidate DYNAMIC_MODULES "site", "ensurepip" (and "venv", which drives ensurepip by subprocess).
* [guards: also missing] importlib.resources imports a package named by a string; only importlib.util and .machinery are banned.
   EVIDENCE: Lib/importlib/resources/_common.py:82 `return importlib.import_module(cand)`; tests/compliance_guards.py:47 `importlib.metadata stays allowed: owner.py reads the RECORD files with it`; core/compliance/owner.py:594 `import importlib.metadata  # noqa: E402`
   IMPACT: Simplest correct rule: any `importlib` import other than `importlib.metadata` is a dynamic import (covers resources, abc, _bootstrap, _bootstrap_external). Note importlib.metadata itself keeps a string-import route (Lib/importlib/metadata/__init__.py:173-179 `def load(self)` ... `module = import_module(match.group('module'))`) through an attribute `.load()`; leave it to the docstring's "not a proof" list, since owner.py needs the module.
* [guards: also missing] A bare `compile(...)` is not banned (ledger:75 listed it as uncovered).
   EVIDENCE: probe: `_dynamic_hits(X, 'x = compile(s, "x", "exec")\n')` -> no hit; `types.FunctionType(code, {})` runs a code object without exec/eval
   IMPACT: Ban the bare Name `compile` only: adding "compile" to DYNAMIC_NAMES as-is would flag every `re.compile` attribute, because _dynamic_hits checks Name and Attribute alike (guards:153-156), and core/compliance uses re.compile at rules.py:383-386, owner.py:75-78, alerts.py:25-28. A grep found no bare `compile(` in core/compliance.
* [guards: also missing] Native and private modules: ctypes is named "not covered"; _ssl, _overlapped, _winapi are not banned.
   EVIDENCE: tests/compliance_guards.py:256-258 `Not covered: a subprocess call (...), ctypes, and reaching a network API through an allowed module`; base Python DLLs list `_ctypes.pyd`, `_overlapped.pyd`, `_ssl.pyd`; Lib/ssl.py:100 `import _ssl             # if we can't import it, let the error propagate`
   IMPACT: core/compliance imports none of them (its import list has no ctypes; only tools/signer/sign.py:794 `import ctypes`, outside core). Banning "ctypes", "_ctypes", "_ssl", "_overlapped" in NETWORK_MODULES is cheap and removes ctypes from the "not covered" list. "_winapi" (process creation) sits with subprocess, which alerts.py:11 needs; leave it documented.
* [guards: attribute routes stay open] Allowed modules that import socket keep it as an attribute.
   EVIDENCE: Lib/mailbox.py:12 `import socket`; Lib/concurrent/futures/process.py:54 `import multiprocessing.connection`; Lib/multiprocessing/connection.py:16 `import socket`
   IMPACT: A denylist cannot list every carrier; keep the docstring's "an allowed module that imports a banned one carries it as an attribute" and add `mailbox` / `concurrent.futures.process` only if the plan wants examples. Do not claim completeness.
* [guards: what core/compliance imports today] The follow-up's bans must not hit shipped code.
   EVIDENCE: the import statements of core/compliance/*.py are: __future__, math, json, collections.abc, re, os, weakref, sys, string, hashlib, dataclasses, argparse, typing, pathlib, datetime, zoneinfo, yaml, threading, subprocess, msvcrt, fcntl, importlib.metadata, codecs, binascii, base64, ast, types, contextlib, cryptography.*, core.isolation, core.compliance.*
   IMPACT: None of the candidates above is imported, so the shipped-file asserts (guards:300-302, :340-341) stay green. Recheck core/odds once the odds plan adds files (DYNAMIC scope).
* [guards: tests that change] Positive controls loop over every banned module in each import form.
   EVIDENCE: tests/compliance_guards.py:292-294 `for module in DYNAMIC_MODULES: ... for src in (f"import {module}\n", f"import {module}.x\n", f"from {module} import x\n"):`; :319-322 the same loop over NETWORK_MODULES with four forms
   IMPACT: New tuple entries get positive controls for free; still add explicit cases for the motivating routes (`from xml.dom import minidom`, `import xml.dom`, `import antigravity`, `from logging import config`) and keep the negative controls `import logging`, `import xml.etree.ElementTree`, `import importlib.metadata`, `import subprocess` (guards:332-335).
* [guards: registration literal] The suite-list literal guard will break when the odds suite registers.
   EVIDENCE: tests/compliance_guards.py:488-489 `assert "paper, grokteam or compliance" in (ROOT / "tests" / "run_all.py").read_text(encoding="utf-8")` (and README.md); tests/run_all.py:113 `help="run one suite: cockpit, engine, ui, quant, ficc, expansion, macro, paper, grokteam or compliance"`; README.md:816 the same list
   IMPACT: Whichever plan lands second edits this assert (ledger:69 already called it brittle). The follow-up can loosen it to "compliance appears in the suite list" so the odds plan does not have to touch a compliance test.

## 2. D15 enforced only by row content (ledger:243)

* [D15: parked item] The parked text, verbatim.
   EVIDENCE: ledger:243 `Final: parked — D15 is enforced only by row content: an explicit financing: [cash, margin] or action: [..., lend, sell_short] on an allow row still loads VALID (D16 has a loader check, D15 does not) — Ruling: park as loader hardening for the next table change; the shipped table is cash-only and every change needs the owner's signature — cost if wrong: a signed table that widens an allow row would be honoured`
   IMPACT: Scope: core/compliance/rules.py `_row` plus tests/compliance_tables.py.
* [D15: the rule] D15 is "no credit buying and no coin lending or borrowing"; the seed rows make credit/margin and lend/borrow out_of_scope.
   EVIDENCE: spec:69 `| D15 | **No credit buying and no coin lending or borrowing.** This is owner policy, stricter than the law, and applies in the strategies spec too |`; spec:344 `| KR-KIS-CREDIT | kis: any / buy / credit | out_of_scope (D15) | policy (D15) | 23 |`; spec:353 `| KR-DOMESTIC-LENDING | upbit, bithumb, coinone, korbit: coin / lend, borrow | out_of_scope (D15) | policy (D15) | 11 |`; spec:975 `credit is BLOCK (D15); lend and borrow are BLOCK (D15);`; spec:1164 `credit and lending stay out (D15).`
   IMPACT: The loader rule: a row whose treatment is allow, gated or grey may not match financing credit or margin, nor action lend or borrow. Margin counts as D15 by the Task 7 ruling (ledger:131 `D15 forbids credit buying and margin`) and by the shipped row (kr_rules.yaml:244 `financing: [credit, margin]`).
* [D15: sell_short is D16, not D15] The ledger's example names sell_short, but spec puts short selling under D16.
   EVIDENCE: spec:70 `| D16 | Short selling, leveraged and single-stock ETPs, KRX derivatives and ELW are **refused until live broker evidence exists**`; shipped gated D16 rows that match sell_short: KR-KIS-KRX-DERIV (kr_rules.yaml:201 `action: [buy, sell_short, write], financing: [cash]`) and KR-KIS-SHORT (kr_rules.yaml:265 `action: [sell_short], financing: [cash]`)
   IMPACT: A D15 check must NOT refuse sell_short (it would make the shipped table INVALID). Refusing sell_short on an allow row without requires.live is a D16-by-content check, a separate rule (see the next bullets).
* [D15: where the D16 check lives] Inside `_row`, keyed on the policy_ref text, not on row content.
   EVIDENCE: core/compliance/rules.py:487-492 `policy_ref = item.get("policy_ref")` / `if policy_ref is not None:` / ... / `if "D16" in policy_ref.split(", ") and not live:` / `raise Invalid(f"{where}: requires.live: a D16 row needs live broker evidence (requires.live)")`; :493-494 `if treatment == "gated" and not (owner or live):`
   IMPACT: Put the D15 check in `_row` (rules.py:440-538) after the axis check at :454-459 (which guarantees `match["action"]` and `match["financing"]` exist on every allow/gated/grey row, and `any` is already refused there by `_match`, rules.py:416-418), e.g. next to :491-494. Name the row and field like the neighbours: f"{where}: match.financing: ..." / f"{where}: match.action: ...".
* [D15: guarantees the check can rely on] Non-blocking rows always name action, financing and a class or asset, and never `any`.
   EVIDENCE: rules.py:454-459 `if treatment not in _BLOCKING: ... missing = sorted({"action", "financing"} - set(match)) + ...` / `raise Invalid(f"{where}: match: an allow, gated or grey row names action, financing and a class or an asset; missing {missing}")`; rules.py:405 `_BLOCKING = frozenset({"hard_block", "out_of_scope"})`
   IMPACT: The D15 test is a set test on two keys; conduct rows are hard_block (rules.py:449-450) and blocking rows stay free to match credit, margin, lend and borrow (KR-KIS-CREDIT, KR-DOMESTIC-LENDING).
* [D15: the shipped table already complies] Every allow/gated/grey shipped row is financing [cash] with no lend/borrow.
   EVIDENCE: read-only probe of rules.parse_rules(core/compliance/kr_rules.yaml): 47 rows; the 15 non-blocking rows all print `'financing': ['cash']`, none has lend or borrow; tests/compliance_tables.py:930-932 already pin `assert r.match["financing"] == frozenset({"cash"}), r.id` for shipped non-blocking rows
   IMPACT: The new loader rule leaves the shipped table VALID and changes no shipped bytes (no new owner approval needed for the table itself).
* [D15: existing loader tests stay green] The `any` test builds an allow row with financing credit, but it fails earlier on `any`.
   EVIDENCE: tests/compliance_tables.py:197-199 `wide = {"venue": ["kis"], "class": ["any"], "action": ["buy"], "financing": ["credit"]}` / `for treatment in ("allow", "gated", "grey"):` / `_bad(_row(treatment=treatment, match=wide), "match.class: any is allowed only on hard_block")`
   IMPACT: `_match` (rules.py:451) raises before the D15 check, so the expected reason holds as long as the D15 check comes after line 451. The blocking-row half of that test (:200-201) stays valid.
* [D15: test home] Mirror the D16 loader test.
   EVIDENCE: tests/compliance_tables.py:285-299 `def test_d16_rows_need_requires_live():` using `_bad(_row(), _row(**lev), "row T-LEV: requires.live")` and `_parse(_row(), _row(**{**lev, "policy_ref": "D15", "treatment": "out_of_scope"}))`; fixture builder :50-59 `_row(**over)` (a valid allow row covering all 38 matrix rows)
   IMPACT: New `test_d15_rows_never_let_credit_margin_lending_or_borrowing_through` next to it: `_bad` for allow/gated/grey with financing [cash, margin], [credit], action [buy, lend], [borrow]; `_parse` for the same matches on out_of_scope and hard_block rows.
* [D15: optional label check] A row citing D15 could also be required to be blocking.
   EVIDENCE: rules.py:385 `_POLICY = re.compile(r"D[1-9][0-9]*(?:, D[1-9][0-9]*)*")`; shipped D15 rows: tests/compliance_tables.py:826 `"D15": {"KR-KIS-CREDIT", "KR-DOMESTIC-LENDING"}` (both out_of_scope, plan:4557)
   IMPACT: `if "D15" in policy_ref.split(", ") and treatment not in _BLOCKING: Invalid` is the D16-style label rule; the content rule is the one that closes the parked gap.
* [D16 by content: same gap, not parked] D16 is also enforced only through the policy_ref label: an allow row that matches sell_short or a D16 class without citing D16 loads VALID.
   EVIDENCE: rules.py:491 `if "D16" in policy_ref.split(", ") and not live:` (fires only when the row cites D16); tests/compliance_tables.py:295 `_parse(_row(), _row(**{**lev, "policy_ref": "D160"}, requires={"owner": ["kofia_leveraged_1h"]}))   # not D16` (a gated etp_leveraged row with no live evidence loads VALID when it cites another decision)
   IMPACT: Optional companion rule: a non-blocking row whose action includes sell_short, or whose class includes etp_leveraged, etp_single_stock, krx_derivative or elw, or whose asset includes krx_derivative or elw, needs requires.live. The shipped D16 rows already carry live (probe: KR-KIS-ETP-LEV, KR-KIS-SINGLE-ETP, KR-KIS-KRX-DERIV, KR-KIS-ELW, KR-KIS-SHORT). An asset-keyed allow row (`asset: [krx_etp]`) also covers etp_leveraged; the rule should look at asset too. Owner decision whether this is in scope (open question).
* [D15: the gate side today] Exits require cash, but new exposure relies on the table rows; a comment claims more than the code enforces.
   EVIDENCE: core/compliance/gate.py:196-200 `Only a cash-financed intent is an exit (D15).` / `if intent.financing != "cash":` / `return "new_exposure"`; gate.py:312 `leverage = abs(intent.multiple)                                    # P4; no row lets credit or margin through`
   IMPACT: The loader rule makes the gate.py:312 comment true by construction. Alternative or extra site: the hard-coded floor `_floor_new` (gate.py:404-420) could add "floor: D15 ..." for new exposure with financing != cash or action lend/borrow (stricter than spec 5.2's floor list, so allowed). That changes exact-reason tests: tests/compliance_gate.py:587-592 assert `d.reasons == ("out_of_scope: KR-KIS-CREDIT",)` and `("out_of_scope: KR-DOMESTIC-LENDING",)`. The ledger chose the loader.
* [D15: approved-table effect] A tightened loader re-parses stored approvals on every load_context.
   EVIDENCE: core/compliance/owner.py:960-961 `return rules.approved_state(raws["rules"], raws["instruments"], raws["venues"], ...`; rules.py:766-767 `except Invalid as exc:` / `return ApprovedState.invalid(exc.reason)`; latest_snapshot rebuilds the same way (owner.py:854)
   IMPACT: An already-approved table that breaks the new rule would turn INVALID (new exposure blocked, exits via snapshot also invalid, so manual). No approval exists today, so no effect now; the plan should say so.

## 3. H2 and T2: D12 dating in owner.py (ledger:188-189)

* [H2: parked item] Verbatim.
   EVIDENCE: ledger:188 `Task 12: parked — a halt stamped ahead (system clock past Seoul midnight) with no later line stamped on/before the loosening's date lets a same-date loosening through after the halt (H2) — Ruling: accept and document for the final review and GPT's check; bounding the halt date by the latest stamp before it would revoke loosenings that were in force before the halt when no line sits between them (over-block); needs a clock skew past midnight — cost if wrong: under that skew a loosening survives a halt written the same Seoul day`
   IMPACT: H2 is ALSO on the execution carry list (ledger:239 `H2 halt-dating before execution writes system_halt`), so ownership between the follow-up and the execution spec must be decided (open question).
* [T2: parked item] Verbatim.
   EVIDENCE: ledger:189 `Task 12: parked — a backdated loosening that is the first line of its day counts at once (T2): needs the owner's key and a backdated signer clock; no outside time anchor in the log — Ruling: known limit of round 1's dating, documented — cost if wrong: one loosening a day early`
   IMPACT: Any fix needs a time source outside the owner's stamps (see the alerts.jsonl bullet).
* [D12 dating: rulings it implements] The fold follows the round-2/3 rulings.
   EVIDENCE: ledger:182 `date each loosening as LATE as plausible (running maximum Asia/Seoul date over the log up to its seq) and each restriction (system_halt, session_armed, and the halt cutoff) as EARLY as plausible (the minimum of its own stamp date, the dates of every later line in seq order, and today's date); the halt cutoff is the minimum such halt date over all halts`; ledger:185 `every session_armed counts whatever its stamp (dated early, as ruled), cleared by system_disarm; armed_sessions (which enables trading) keeps ignoring armings stamped after now`
   IMPACT: A fix may only make loosenings later or restrictions earlier (stricter); it may not undo either ruling.
* [D12 dating: the code] The two date arrays.
   EVIDENCE: core/compliance/owner.py:495-503 `stamps = [_seoul_date(e.utc) for e in entries]` / `late, seen = [], _dt.date.min` / `for on in stamps:` / `seen = max(seen, on)` / `late.append(seen)` / `early, soonest = [_dt.date.min] * len(stamps), day` / `for i in range(len(stamps) - 1, -1, -1):` / `soonest = min(soonest, stamps[i])` / `early[i] = soonest`
   IMPACT: `late[i]` dates loosenings (T2 lives here); `early[i]` dates halts and armings (H2 lives here).
* [D12 dating: the halt cutoff] Halts are dated early; the loosening test.
   EVIDENCE: owner.py:505-508 `halts = [(e.seq, soon, float(e.data["floor_krw"])) for e, _, soon in dated if e.kind == "system_halt"]` / `first_halt = min(...)` / `halt_day = min((soon for _, soon, _ in halts), default=None)` / `halt_floor = max(...)`; owner.py:525-528 `def loosening_counts(e, on) -> bool:` / `return (e.utc <= now_utc and on < day` / `and (first_halt is None or (e.seq < first_halt and on < halt_day))` / `and (mine is None or mine > on))`
   IMPACT: H2 mechanics: loosening L on true Seoul date D, halt H on true date D but stamped D+1, no line after H: early[H] = min(D+1, today) = D+1 on the next day, so `on (D) < halt_day (D+1)` and L counts. Only `halt_day` (or a new bound on it) can change that.
* [D12 dating: where loosenings apply] Only cap_set and limit_set are D12 loosenings; future-stamped other kinds are dropped.
   EVIDENCE: owner.py:535-542 `if e.utc > now_utc and e.kind not in ("cap_set", "limit_set"):` / `continue` / ... / `if key in _TIGHTER and ((old is not None and _TIGHTER[key](value, old)) or loosening_counts(e, on)):`; owner.py:437-439 `_TIGHTER = {"okx_equity_share": lambda new, old: new <= old, ... "total_loss_floor_krw": lambda new, old: new >= old, ... "daily_loss_krw": lambda new, old: new <= old}`; owner.py:557-558 the floor clamp `values["total_loss_floor_krw"] = max(values["total_loss_floor_krw"], halt_floor)`
   IMPACT: T2 and H2 only ever move cap/limit loosenings; the floor clamp to the highest halted floor holds whatever the dating.
* [D12 dating: the docstring states the rule] The follow-up must update it with any change.
   EVIDENCE: owner.py:488-494 `A loosening is dated as late as the log allows: by the latest Asia/Seoul date among the lines up to and including it ... A restriction (a system_halt or a session_armed) is dated as early as the log allows: by the earliest of its own stamp, the stamps of the lines after it, and day ... The halt cutoff is the earliest halt date.`; Appendix A.8.3 plan:17392-17395 `D12: caps and limits: a tightening applies from its entry; a loosening applies only when its Asia/Seoul date is before date ...`
   IMPACT: Contract text (A.8.3) and the docstring change together; the signer's help text states D12 in user words (tools/signer/sign.py:36-39 `cap_set and limit_set: a tighter value applies at once; a looser one ... applies only from the next Asia/Seoul date, never inside a session armed on or before the day you set it, and never after a system_halt`) and needs no change unless the user-facing rule changes.
* [H2: a test pins the current behaviour as a control] Fixing H2 flips an existing assertion.
   EVIDENCE: tests/compliance_owner.py:958-960 `alone = _state_at(_state_log(*loosen, bogus), _state_kst(2026, 10, 24))` / `assert alone.caps == {"okx_equity_share": 0.50}, "control: nothing shows that halt came before 15 October"` / `assert alone.halted_floors == {21_000.0}` (bogus = a halt stamped 2099-01-01 after a loosening on 2026-10-14)
   IMPACT: A "bound the halt by the latest stamp before it" fix makes that control 0.10; the plan must rewrite it deliberately, with the over-block the ledger names (a loosening in force before a real, later halt is revoked when no line sits between them). Related pins: :944-950 (a line stamped ahead does not delay a halt), :875-891 (halt/disarm apply before their stamp), :719-736 (no loosening after a halt).
* [H2: nothing writes halts yet] There is no production caller of append_system_entry.
   EVIDENCE: grep over *.py outside tests/ and .venv/: `append_system_entry` appears only at its definition core/compliance/owner.py:400; spec:567 `system (unsigned): system_halt, system_disarm. The execution spec writes halts here.`
   IMPACT: H2 is latent until execution writes halts, which is why the ledger also carries it there. The execution writer has a time source the log lacks (broker/exchange server time; inference, not checked).
* [H2: the writer] append_system_entry stamps the caller's `now` and does not compare it with the last line.
   EVIDENCE: owner.py:409 `utc = iso_utc(now)`; owner.py:415-417 `last = parsed[-1][0] if parsed else None` / `body = {"seq": ..., "prev_sha256": ..., "utc": utc, "kind": kind, "data": data}`; the signer, by contrast, refuses a stamp earlier than the last line: tools/signer/sign.py:923-925 `last = json.loads(lines[-1])["utc"] if lines else ""` / `if utc < last:` / `raise RuntimeError(f"the stamp {utc} is earlier than entry #{head[0]}'s {last}: check the PC clock; "`
   IMPACT: A writer-side H2 guard (e.g. refuse or flag a halt stamped on a later Seoul date than now's trusted date) belongs where `now` comes from, i.e. the execution caller. The carried item "system entry stamped far ahead blocks signer stamps" (ledger:239) is the same interaction seen from the signer: a halt stamped 2099 makes sign.py:924 refuse every later owner entry.
* [T2: the only outside time source] alerts.jsonl rows carry a system-clock utc and an owner-log head that log() checks against owner.jsonl.
   EVIDENCE: core/compliance/alerts.py:253-256 `row = {"utc": model.iso_utc(now), "channel": channel, "result": result, **{k: summary[k] for k in rules._SUMMARY_KEYS}}` / `if not _in_log(summary["head_seq"], summary["head_sha256"]):`; alerts.py:312 `now = datetime.now(timezone.utc)`; owner.py:357-361 read_anchors takes every alerts row's (head_seq, head_sha256), but owner_state receives no time from them (owner.py:938-943)
   IMPACT: A T2 fix could date a loosening no earlier than the Seoul date of the latest alerts row whose head_seq < the loosening's seq (that row proves the entry did not exist yet). It only makes loosenings later (allowed), but it changes owner_state's pure signature (A.8.3 plan:17387-17388) and _owner_now (owner.py:921-944), and it is only as good as the daily job (rows exist only when the 09:00 task ran). Snapshots and store anchors carry no time (owner.py:807-809 snapshot body `{"state_seq", "state_hash", "hashes"}` + head; owner.py:665-666 anchor `{"seq", "row_sha256"}`). Whether to fix T2 at all is an owner/ruling question (open question).
* [T2: the owner-side mitigation that exists] The signer shows the stamp and asks the owner to check it.
   EVIDENCE: tools/signer/sign.py:856-860 `def _confirm(kind: str, data: dict, head: tuple[int, str], utc: str) -> None:` ... `stamped {utc}. Check the stamp against the real time in UTC:`; sign.py:874-875 `def _utc_now() -> str:` / `return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")`
   IMPACT: T2 needs the owner's key plus a backdated PC clock that the owner fails to notice; the plan can cite this when it keeps T2 as a documented limit.
* [T2: tests that pin the current dating] Cases any T2 fix must keep.
   EVIDENCE: tests/compliance_owner.py:687-688 `first = _state_log(_state_cap(0.20, _state_kst(2026, 10, 20, 10)))` / `assert _state_at(first, _state_kst(2026, 10, 21, 0)).caps == {"okx_equity_share": 0.20}, "alone, it applies next day"`; :854-872 `test_state_backdated_loosening_is_dated_by_the_log_before_it`; :691-697 the Seoul-midnight boundary
   IMPACT: With no alerts rows, a T2 fix must reproduce today's results exactly.

## 4. The other parked or carried notes

* [KONEX structural_max] spec 7.4 applies structural_max to KONEX legs, but the calendars hold no KONEX band.
   EVIDENCE: spec:822-823 `structural_max(plan, cal) applies only to buy-and-hold KRX or KONEX legs: (1 + limit)/(1 − limit) × (1 + limit)^{n−1}`; core/calendars/data/kr_regime_tags.yaml:70 `- effective_from: '2015-06-15'` and :76 `value: 0.3` (one market-wide price_limit); `grep -i konex core/calendars/` finds nothing; repo map:793 `Flag to the odds plan: spec 7.4 lists KONEX for structural_max, but regime_tags has no KONEX limit.`
   IMPACT: ODDS item, not compliance: KONEX is gate-only (spec:175 `KONEX is gate-only, so it needs no odds cost book`), and the odds whitelist (spec:46-47) excludes KONEX shares, so structural_max never sees one. The follow-up plan does nothing; the odds plan should say why KONEX drops out.
* [yfinance cache] yfinance keeps its sqlite cache outside ~/.tradegen; the hand-off assigns the redirect to the odds plan.
   EVIDENCE: plan:16742-16743 `call yf.set_cache_location under the state root (the map found yfinance's shared sqlite cache in %LOCALAPPDATA%\py-yfinance)`; plan:1212 `Residual, not changed here: ... and yfinance's own sqlite cache under %LOCALAPPDATA%\py-yfinance`; constraints.txt:106 `yfinance==1.4.1` (the repo map's :105 is now :106); core/ficc/data.py:53 `import yfinance as _yf`; no `set_cache_location` anywhere in core/, data/ or config.py
   IMPACT: ODDS item. The follow-up plan does not touch yfinance.
* [KRX-DERIV] The live-evidence ruling is applied; only the reason text lags.
   EVIDENCE: ledger:111 ruling `replace it with live item` (broker_approval); core/compliance/kr_rules.yaml:203 `requires: {owner: [kofia_derivatives_1h, krx_derivatives_mock_3h], live: [broker_approval, deposit_krw_10m, deposit_krw_20m]}`; :204 reason `KOSPI200 futures and options need a broker deposit of KRW 10M (stage 1) or KRW 20M (stage 2 ...), at least 1h of course and 3h of mock trading; ... refused until live broker evidence exists (D16)` (no "broker approval"); ledger:118 `KR-KIS-KRX-DERIV reason text does not mention broker approval (cosmetic)`
   IMPACT: FOLLOWUP-table (cosmetic): one reason edit in kr_rules.yaml. It changes the table sha, so the owner's first rules approval must be of the edited bytes (free today: none exists). Bundle with the 2027-01-01 affected_by item (ledger:114) if the plan touches the table.
* [OKX stablecoin exits] No in-gate exit for OKX USDT/USDC until the owner signs a verified deposit network.
   EVIDENCE: ledger:112 ruling `do NOT add unverified USDT/USDC networks (a wrong network loses funds ...)`; ledger:120 `Owner act for the final report: add a verified USDT/USDC deposit network (and verify the BTC 'bitcoin' entry) in core/odds/venues.yaml before approving it; until then OKX stablecoins exit manually.`; core/odds/venues.yaml:47-48 `deposits:                       # UNVERIFIED: no repo source names the network; owner to confirm before approval` / `- {symbol: BTC, network: bitcoin, tag_required: false}`; core/compliance/kr_rules.yaml:554 `USDT, USDC and other destinations are withdrawn manually in the exchange app until the owner signs a verified deposit network`
   IMPACT: OWNER item; no follow-up code. The odds plan, which extends core/odds/venues.yaml (lots, minimums, ticks), must keep the deposits block as is and must not invent networks; both plans list it as an owner act.
* [zero stake] The odds plan must not screen a zero stake.
   EVIDENCE: ledger:244 `Final: carried — odds plan must not send a zero stake to screen() (it now reports malformed: notional_krw); execution spec must derive notional and held_krw from live prices (P19)`; core/compliance/gate.py:65 `more += [] if intent.notional_krw > 0 else ["malformed: notional_krw"]`; gate.py:633 screen builds the buy with `notional_krw=first_stake_krw`
   IMPACT: ODDS (first half) and EXEC (second half). Not a follow-up item.

## 5. Other compliance-hardening candidates (from the deferred minors; full list in section 8)

* [closure scan] A rebound guard name escapes the D14 closure scan; one-line hardening is on record.
   EVIDENCE: ledger:208 `a rebound guard name escapes the closure scan (typing = SimpleNamespace(TYPE_CHECKING=True), __name__ = "__main__"); one-line hardening: require _binds(tree,"typing")==1 / _binds(tree,"__name__")==0 — Task 15's signer copy must match whatever owner.py does`; owner.py:718-719 `if isinstance(t, ast.Attribute):` / `return t.attr == "TYPE_CHECKING" and isinstance(t.value, ast.Name) and t.value.id == "typing"`; owner.py:720-723 the `__name__ == "__main__"` branch with no binding check
   IMPACT: FOLLOWUP-owner+signer: edit owner.py `_skipped` and tools/signer/sign.py:631-650 identically; tests/compliance_signer.py:630-634 (`test_code_files_match_owner`) and :670-671 catch drift. Code-hash-relevant (owner.py is in the closure).
* [signer ancestor walk] The Claude-ancestor refusal fails open when a parent has exited.
   EVIDENCE: tools/signer/sign.py:761-767 `while pid in table and pid not in seen and len(seen) < 256:` ... `pid = parent` / `return False`; ledger:229 ruling `a refusal check must fail closed`; ledger:233 `ancestor walk returns False when a parent pid has exited`
   IMPACT: FOLLOWUP-signer. The repo copy is only a proposal; the owner's copy changes only by a deliberate owner act (spec:598-599 `Updating the owner's copy is a deliberate owner act: read the diff, re-hash, re-record.`), so the plan must hand that act to the owner.
* [snapshot trust] A forged unsigned snapshot can steer exits under a broken log.
   EVIDENCE: ledger:204; owner.py:836-857 latest_snapshot accepts the newest snapshot whose stored bytes rebuild to its state_hash; spec:620-630 honest limits
   IMPACT: FOLLOWUP-owner (optional): cross-check the snapshot's state_seq against in_force when the log is readable. Within the spec's stated limits, so not required.
* [first fingerprint] The first recorded fingerprint can come from an unverified key.
   EVIDENCE: ledger:219; alerts.py:242-256 log() writes `fingerprint` from any valid summary; owner.py:913-918 `_first_recorded` takes the first row with a fingerprint
   IMPACT: FOLLOWUP-alerts: record fingerprints only from code 0-2 summaries. Changes alerts.py (code hash).
* [loader bounds] review_by has no lower bound, max_leverage no upper bound, and {cap} is legal in non-grey warnings.
   EVIDENCE: ledger:103, :146; rules.py:486 `leverage = 1.0 if item.get("max_leverage") is None else _positive(item["max_leverage"], f"{where}: max_leverage")`; rules.py:76 `WARNING_SLOTS = frozenset({"cap"})                  # the only {slot} a warning may contain`; rules.py:484-485 only `if treatment == "grey" and "cap" not in ...`
   IMPACT: FOLLOWUP-loader, same task as D15 (one file, one test module).
* [exact row pins] Widening an allow row passes the table tests.
   EVIDENCE: ledger:113 `tests pin exact match dicts only for KR-OKX-SPOT; widening an allow row (e.g. sell_short on KR-KIS-US-SHARE, p2p_buy on KR-DOMESTIC-SPOT) passes all 18 tests`; tests/compliance_tables.py:968-972 the KR-OKX-SPOT exact pin (`assert row.match == {"venue": frozenset({"okx"}), ...`)
   IMPACT: FOLLOWUP-tests: pin {id: (match, requires_owner, requires_live, treatment)} for every non-blocking shipped row (15 rows, probe above). Pairs with D15 (loader) as defence in depth.

## 6. Items carried to the EXECUTION spec (verbatim)

* [carried] The final review's carry list.
   EVIDENCE: ledger:239 `Final: carried to the execution spec: ack accepted with session None and gate never reads ctx.session.armed; shared reservation_id; permit edited in place; append_system_entry TypeError/OSError; torn alerts.jsonl / owner.jsonl last line repair; KEY CHANGED after rotation in due(); KIS token burnt on refusal; system entry stamped far ahead blocks signer stamps; signer signs acks as bare hashes; P20 retired-key history rewrite; H2 halt-dating before execution writes system_halt`
   IMPACT: Not in the compliance follow-up, except that H2 also appears as parked (ledger:188); decide its owner.
* [carried] Live notional.
   EVIDENCE: ledger:244 `execution spec must derive notional and held_krw from live prices (P19)`
   IMPACT: EXEC.
* [carried] Reservation ids.
   EVIDENCE: ledger:155 `two permits sharing one reservation_id both verify (120k vs a 100k cap); add "a reservation id names exactly one intent, reserved at its notional" to P36 / A.5.2 for the execution spec`; ledger:150 `_transfer carries the transfer's reservation_id into the synthetic destination buy, so a destination reservation with the same id is excluded (assumes globally unique ids)`
   IMPACT: EXEC.
* [carried] The rest of the final review's triage.
   EVIDENCE: ledger:238 `the rest is carried to the execution spec or accepted per the reviewer's triage`
   IMPACT: The reviewer's triage itself is not in the repo; only the ledger lines are. Treat any minor not named in ledger:238-244 as "deferred" (section 8).
* [spec 13] The execution spec's own scope.
   EVIDENCE: spec:1160-1163 `**Execution:** adapters, arming and sessions, atomic reservations, single-use permits, the audit log, writing system_halt and system_disarm, reading live balances and broker answers (which lifts D16 row by row), and retiring the read-only guards narrowly. The owner asked on 2026-10-23 about doing this early, for account inquiry only. That is its own small reviewed design.`
   IMPACT: The follow-up must not touch arming, sessions, permits' single use or the read-only guards' retirement.

## 7. What the follow-up may not loosen (spec 5.2, 6.4, D11, D12)

* [5.2 loading] Loader rules are a floor.
   EVIDENCE: spec:295-300 `The loader uses a SafeLoader subclass that rejects duplicate keys, anchors, aliases and native dates.` / `The file is capped at 256 KB.` / `Every match value must belong to the vocabulary, and any is allowed only on hard_block, out_of_scope and conduct rows.` / `Every row citing D16 must carry requires.live.` / `Any violation makes the table INVALID.`
   IMPACT: The D15 (and optional D16-by-content) rules only add refusals; none of these may be relaxed, and the D16 label rule (rules.py:491-492) stays.
* [5.2 in force] Approval semantics stay.
   EVIDENCE: spec:311-317 `the version in force is the sha256 named by the latest signed approved {kind, sha256} entry in log order` ... `A superseded hash never counts again unless it is re-signed as a new entry.` ... `A git commit is not approval.`
   IMPACT: A table edit (KRX-DERIV reason, affected_by) is a draft until the owner signs it.
* [5.2 floor] The hard-coded floor.
   EVIDENCE: spec:319-326 `Hard-coded floor (defence in depth, whatever the table says): all intents, exits included: the conduct classes and tags, and the event_contract and sports_bet assets; new exposure only ...: the prediction, sportsbook and state-blocked venues; OKX derivatives and P2P; fx_pair, cfd, overseas_future, overseas_crypto_derivative; etp_crypto_spot; option + write.`; gate.py:17-22 FLOOR_* constants
   IMPACT: May be extended (e.g. a D15 floor), never shrunk; an extension must stay "new exposure only" for D11.
* [D11] Exits stay open.
   EVIDENCE: spec:65 `Stale rows, auto-off, unmet gates, caps and out-of-scope or hard-block venue rows block **new exposure only**. Closing a position is still allowed, and so is withdrawing to an FIU-registered domestic exchange at a registered address.`
   IMPACT: No follow-up check may block a cash close-long, cover-short or domestic withdraw; a D15 floor must sit in `_floor_new` (gate.py:404), which exits never reach.
* [6.4 log] BROKEN rules and the unsigned kinds.
   EVIDENCE: spec:546-548 `no signature, for system entries: system_halt {floor_krw} and system_disarm {session_id, reason}. These are the only unsigned kinds, and they can only tighten.`; spec:551-556 BROKEN = `a bad signature on an owner entry; an unsigned line of any other kind; fewer than seq lines for some recorded anchor; a line whose row_sha256 differs from its anchor.` / `All owner state counts as absent: new exposure is BLOCK, and withdrawals are manual.`
   IMPACT: An H2/T2 fix may not make a system entry loosen anything or accept a broken log.
* [6.4 D12] The rule the dating serves.
   EVIDENCE: spec:569-570 `D12. Tightening takes effect at once. Loosening applies only from the next Asia/Seoul date, never while armed, and never for a floor in halted_floors.`; spec:66 `never inside an armed session, and never after a recorded halt`
   IMPACT: Every dating change must keep tightenings immediate and may only delay loosenings.
* [6.4 load_context, code hash, signer] Single producer, closure, signer refusals.
   EVIDENCE: spec:577-582 `load_context(now) is the only non-pure constructor in core/compliance, and the only producer of Context ... No caller may build a Context by hand.`; spec:584-588 the code hash `over sorted (relative path, sha256) pairs of: the .py files of core/compliance and core/odds; their in-repo .py import closure`; spec:600-602 `sign.py refuses to run when a CLAUDECODE or CLAUDE_CODE_* variable is set, when a parent process is the Claude app, or when stdin is not a TTY.`; spec:615 `Claude never runs the signer, never asks for the passphrase, and never writes owner entries.`
   IMPACT: The closure-scan hardening may only add files; the signer change may only refuse more; tests keep using a test key in a temp TRADEGEN_HOME (plan:16813-16814).
* [spec 4 guards] Repo-wide guards stay; the follow-up only adds.
   EVIDENCE: spec:1064-1065 `Existing guards stay in force: test_08, test_09, T-RO-01 (including private_key and the /trading/ path) and T-CTX-01 with the extended prefixes.`
   IMPACT: Guard edits add bans and controls; none is removed.

## 8. Every parked, carried, deferred or follow-up line of the ledger (exact text, classified)

The ledger's own header names these classes: ledger:3-4 `every task review, fix round, controller ruling (each with what it costs if wrong), deferred minor and parked finding.`

* [ledger L64: FOLLOWUP-guards (low)] Task 1: minor (deferred): _clock_hits flags `from time import sleep` but not time.sleep; clock_gettime absent; alias/getattr bypasses pass
   EVIDENCE: docs/superpowers/plans/2026-10-23-compliance-gate-execution-ledger.md:64 (the text above, verbatim)
   IMPACT: CLOCKS at tests/compliance_guards.py:53-56 still lacks clock_gettime/clock_gettime_ns; an alias via getattr still passes. Optional: add the two names with a positive control.
* [ledger L65: ACCEPT] Task 1: minor (deferred): _walk tags a directly nested def's body with outer names only (no effect on current predicates)
   EVIDENCE: docs/superpowers/plans/2026-10-23-compliance-gate-execution-ledger.md:65 (the text above, verbatim)
   IMPACT: Still true (guards:81-93); only `"main" in funcs` (guards:187) reads funcs, so no predicate is affected today.
* [ledger L66: ACCEPT (harness)] Task 1: minor (deferred): _wrap's finally-raise replaces fn()'s exception (chained traceback keeps it)
   EVIDENCE: docs/superpowers/plans/2026-10-23-compliance-gate-execution-ledger.md:66 (the text above, verbatim)
   IMPACT: tests/compliance_acceptance._wrap; no product risk.
* [ledger L67: ACCEPT (harness)] Task 1: minor (deferred): real ~/.tradegen/compliance listing check can fail an unrelated test if the daily job writes during a run
   EVIDENCE: docs/superpowers/plans/2026-10-23-compliance-gate-execution-ledger.md:67 (the text above, verbatim)
   IMPACT: Flake risk only once the daily job runs; note it for the follow-up's test runs.
* [ledger L68: ODDS note] Task 1: minor (deferred): shipped-file clean asserts vacuous at this commit; no on-disk end-to-end control
   EVIDENCE: docs/superpowers/plans/2026-10-23-compliance-gate-execution-ledger.md:68 (the text above, verbatim)
   IMPACT: The clean asserts become non-vacuous for core/odds once the odds plan adds .py files there.
* [ledger L69: ODDS + FOLLOWUP-guards] Task 1: minor (deferred): registration test asserts the literal "paper, grokteam or compliance" (brittle; plan-mandated)
   EVIDENCE: docs/superpowers/plans/2026-10-23-compliance-gate-execution-ledger.md:69 (the text above, verbatim)
   IMPACT: guards:488-489 assert the literal "paper, grokteam or compliance" in tests/run_all.py and README.md; registering an `odds` suite changes that text (tests/run_all.py:113, README.md:816) and breaks this guard. Whichever plan lands second must edit it.
* [ledger L70: FOLLOWUP-guards (low)] Task 1: minor (deferred): _main_block_hits misses reversed `"__main__" == __name__`; temp_home rmtree ignore_errors may leak temp dirs
   EVIDENCE: docs/superpowers/plans/2026-10-23-compliance-gate-execution-ledger.md:70 (the text above, verbatim)
   IMPACT: guards:213 compares ast.unparse(n.test) to "__name__ == '__main__'" only; the reversed form escapes the one-line rule.
* [ledger L71: ACCEPT] Task 1: minor (deferred): compliance_acceptance imports temp_home lazily without need
   EVIDENCE: docs/superpowers/plans/2026-10-23-compliance-gate-execution-ledger.md:71 (the text above, verbatim)
   IMPACT: Cosmetic.
* [ledger L74: FIXED (final wave)] Task 1: minor (deferred): test_no_http_verb_calls docstring says getattr indirection matters only with a banned import — false (unittest.mock.asyncio, logging.config.dictConfig class strings reach banned modules); "xml.dom parsers that fetch" inaccurate (xml.sax fetches)
   EVIDENCE: docs/superpowers/plans/2026-10-23-compliance-gate-execution-ledger.md:74 (the text above, verbatim)
   IMPACT: guards:248-262 docstring now says the guards "do not prove that core/compliance cannot reach the network" and names the minidom/parseURI route.
* [ledger L75: PARTLY FIXED; rest FOLLOWUP-guards] Task 1: minor (deferred): uncovered fetch/exec routes: xml.dom.xmlbuilder DOMEntityResolver, pydoc.locate, timeit/code/cProfile string execution, compile (covered only by the "not a proof" disclaimer)
   EVIDENCE: docs/superpowers/plans/2026-10-23-compliance-gate-execution-ledger.md:75 (the text above, verbatim)
   IMPACT: pydoc, timeit, code, cProfile are now in DYNAMIC_MODULES (guards:50-51). xml.dom is parked (line 242). A bare `compile` is still unbanned (probe in section Guards).
* [ledger L80: FIXED (final wave)] Task 2: minor (deferred): pyproject requires-python >=3.10 but Path.is_junction needs 3.12 (venv is 3.13)
   EVIDENCE: docs/superpowers/plans/2026-10-23-compliance-gate-execution-ledger.md:80 (the text above, verbatim)
   IMPACT: guards:505 asserts requires-python == ">=3.12".
* [ledger L81: EXEC (carried, line 239)] Task 2: minor (deferred): KIS token is issued before the final-target check refuses, burning an issuance per call when the target is bad
   EVIDENCE: docs/superpowers/plans/2026-10-23-compliance-gate-execution-ledger.md:81 (the text above, verbatim)
   IMPACT: "KIS token burnt on refusal" is in the execution carry list.
* [ledger L82: FOLLOWUP-isolation] Task 2: minor (deferred): ficc _cache_put sets _MEM before checked_target, so a refused key is later served from memory without re-raising
   EVIDENCE: docs/superpowers/plans/2026-10-23-compliance-gate-execution-ledger.md:82 (the text above, verbatim)
   IMPACT: Still true: core/ficc/data.py:273 `_MEM[key] = (now, rows)` precedes :274 checked_target. Outside core/compliance; it enters the D14 closure only if core/odds imports core.ficc.data.
* [ledger L83: FOLLOWUP-tests] Task 2: minor (deferred): no test for a refusal propagating from config.ficc_cache_dir() itself
   EVIDENCE: docs/superpowers/plans/2026-10-23-compliance-gate-execution-ledger.md:83 (the text above, verbatim)
   IMPACT: Test gap only.
* [ledger L84: ACCEPT (test hygiene)] Task 2: minor (deferred): grokteam isolation test clears B._MANIFESTS instead of restoring it
   EVIDENCE: docs/superpowers/plans/2026-10-23-compliance-gate-execution-ledger.md:84 (the text above, verbatim)
   IMPACT: No product risk.
* [ledger L86: OPEN QUESTION] Task 2: minor (deferred): an ancestor of the state root that is a junction/symlink is not judged (only the root itself; OneDrive reparse points make ancestors a design question)
   EVIDENCE: docs/superpowers/plans/2026-10-23-compliance-gate-execution-ledger.md:86 (the text above, verbatim)
   IMPACT: Design question (OneDrive reparse points); not decided in the ledger.
* [ledger L88: NOTE] Note for later dispatches: compliance_isolation has 16 tests (plan said 15), so any brief's whole-suite compliance count is one higher (one REFDATA NOT_RUN there).
   EVIDENCE: docs/superpowers/plans/2026-10-23-compliance-gate-execution-ledger.md:88 (the text above, verbatim)
   IMPACT: Count note; compliance now 315 PASS / 2 NOT_RUN (README.md:839).
* [ledger L92: ACCEPT] Task 3: minor (deferred): derive_class with |int| beyond 4300 digits raises ValueError from the f-string (outside load_strict's domain)
   EVIDENCE: docs/superpowers/plans/2026-10-23-compliance-gate-execution-ledger.md:92 (the text above, verbatim)
   IMPACT: Outside load_strict's domain: the loader's ints are a "decimal int of at most 18 digits" (rules.py:95).
* [ledger L93: FOLLOWUP-loader (low)] Task 3: minor (deferred): refusal reasons echo offending values unbounded (250 KB scalar -> 250 KB reason); truncate if reasons reach alerts/logs
   EVIDENCE: docs/superpowers/plans/2026-10-23-compliance-gate-execution-ledger.md:93 (the text above, verbatim)
   IMPACT: Reasons can reach --check lines; truncation is a small hardening.
* [ledger L94: ACCEPT] Task 3: minor (deferred): "native date"/YAML 1.1 reasons carry no line number (plan-mandated text)
   EVIDENCE: docs/superpowers/plans/2026-10-23-compliance-gate-execution-ledger.md:94 (the text above, verbatim)
   IMPACT: Plan-mandated text.
* [ledger L95: ACCEPT/FOLLOWUP (tiny)] Task 3: minor (deferred): load_strict accepts bytearray (contract says bytes)
   EVIDENCE: docs/superpowers/plans/2026-10-23-compliance-gate-execution-ledger.md:95 (the text above, verbatim)
   IMPACT: The contract says bytes.
* [ledger L96: FOLLOWUP-tests] Task 3: minor (deferred): test_plain_scalars_load_as_expected uses dict equality (0==False, 3==3.0); cross-type duplicate keys and parse_date trailing newline untested
   EVIDENCE: docs/superpowers/plans/2026-10-23-compliance-gate-execution-ledger.md:96 (the text above, verbatim)
   IMPACT: Test gap only.
* [ledger L101: ODDS/EXEC note] Task 4: minor (deferred): Row/RulesTable not deepcopy/asdict-safe (mappingproxy); Task 6/14 must not asdict Row
   EVIDENCE: docs/superpowers/plans/2026-10-23-compliance-gate-execution-ledger.md:101 (the text above, verbatim)
   IMPACT: Row.match is a MappingProxyType (rules.py:422): never dataclasses.asdict/deepcopy a Row in report or execution code.
* [ledger L102: ACCEPT] Task 4: minor (deferred): calendar_sha256 lets OSError from read_bytes escape; empty dir hashes to empty sha256 (callers compare to approved hash)
   EVIDENCE: docs/superpowers/plans/2026-10-23-compliance-gate-execution-ledger.md:102 (the text above, verbatim)
   IMPACT: store_get catches OSError and rules.Invalid (owner.py:678); callers compare against the approved hash.
* [ledger L103: FOLLOWUP-loader] Task 4: minor (deferred): review_by has no lower bound; max_leverage no upper bound
   EVIDENCE: docs/superpowers/plans/2026-10-23-compliance-gate-execution-ledger.md:103 (the text above, verbatim)
   IMPACT: No lower bound on review_by and no upper bound on max_leverage in _row (rules.py:486, :522-528).
* [ledger L104: FOLLOWUP-tests] Task 4: minor (deferred): non-str settlement items, market bases, deposit symbols handled but untested
   EVIDENCE: docs/superpowers/plans/2026-10-23-compliance-gate-execution-ledger.md:104 (the text above, verbatim)
   IMPACT: Test gap only.
* [ledger L105: ACCEPT] Task 4: minor (deferred): Formatter().parse(warning) runs twice per row
   EVIDENCE: docs/superpowers/plans/2026-10-23-compliance-gate-execution-ledger.md:105 (the text above, verbatim)
   IMPACT: Perf cosmetic (rules.py:431 and :484).
* [ledger L107: FOLLOWUP-tests (one line)] Task 4: minor (deferred): D0016 refused but untested
   EVIDENCE: docs/superpowers/plans/2026-10-23-compliance-gate-execution-ledger.md:107 (the text above, verbatim)
   IMPACT: tests/compliance_tables.py:297-298 lists "D016" and "D15, D016" but not "D0016".
* [ledger L112: OWNER (ruling applied)] Task 5: Ruling: OKX stablecoins have no in-gate exit (Upbit/OKX deposit facts list only BTC; P22), which conflicts with D11 "exits stay open" — do NOT add unverified USDT/USDC networks (a wrong network loses funds, which is what the deposit check exists to prevent); instead make KR-OKX-WITHDRAW's reason accurate (with the shipped venue facts only BTC to Upbit is a gate exit; stablecoins and other destinations exit manually in the exchange app until the owner signs a verified deposit network) and carry an owner act to Task 16's hand-off — fail closed, matches D11's manual-withdrawal fallback — cost if wrong: the owner exits OKX stablecoins by hand until they add a verified network
   EVIDENCE: docs/superpowers/plans/2026-10-23-compliance-gate-execution-ledger.md:112 (the text above, verbatim)
   IMPACT: KR-OKX-WITHDRAW reason is accurate (core/compliance/kr_rules.yaml:554); core/odds/venues.yaml:47-48 lists only BTC for okx. No code change: Claude must not add deposit networks.
* [ledger L113: FOLLOWUP-tests] Task 5: minor (deferred): tests pin exact match dicts only for KR-OKX-SPOT; widening an allow row (e.g. sell_short on KR-KIS-US-SHARE, p2p_buy on KR-DOMESTIC-SPOT) passes all 18 tests — suggest exact {id: match, requires} pins for the ~15 rows that can let something through
   EVIDENCE: docs/superpowers/plans/2026-10-23-compliance-gate-execution-ledger.md:113 (the text above, verbatim)
   IMPACT: Exact {id: match, requires} pins for the rows that can let something through; pairs with the D15 loader check.
* [ledger L114: FOLLOWUP-table (owner approval)] Task 5: minor (deferred): no row lists 2027-01-01 in affected_by (tax date; crypto tax_basis depends on it)
   EVIDENCE: docs/superpowers/plans/2026-10-23-compliance-gate-execution-ledger.md:114 (the text above, verbatim)
   IMPACT: Table content change; needs a fresh owner `approved {kind: rules}`.
* [ledger L115: NOTE] Task 5: minor (deferred): report says trailer Sonnet while constraints said Opus (superseded by the attribution ruling)
   EVIDENCE: docs/superpowers/plans/2026-10-23-compliance-gate-execution-ledger.md:115 (the text above, verbatim)
   IMPACT: Superseded by the attribution ruling (line 90).
* [ledger L116: ACCEPT] Task 5: minor (deferred): KR-DRIFT lists a repo research path under sources (duplicates research; brief-mandated)
   EVIDENCE: docs/superpowers/plans/2026-10-23-compliance-gate-execution-ledger.md:116 (the text above, verbatim)
   IMPACT: Brief-mandated.
* [ledger L118: FOLLOWUP-table (cosmetic)] Task 5: minor (deferred): KR-KIS-KRX-DERIV reason text does not mention broker approval (cosmetic)
   EVIDENCE: docs/superpowers/plans/2026-10-23-compliance-gate-execution-ledger.md:118 (the text above, verbatim)
   IMPACT: core/compliance/kr_rules.yaml:204 reason lacks "broker approval" while :203 requires.live lists broker_approval.
* [ledger L120: OWNER] Owner act for the final report: add a verified USDT/USDC deposit network (and verify the BTC 'bitcoin' entry) in core/odds/venues.yaml before approving it; until then OKX stablecoins exit manually.
   EVIDENCE: docs/superpowers/plans/2026-10-23-compliance-gate-execution-ledger.md:120 (the text above, verbatim)
   IMPACT: Owner act; the odds plan extends core/odds/venues.yaml and must leave the stablecoin networks to the owner.
* [ledger L123: FOLLOWUP-model (low)] Task 6: minor (deferred): jsonable stringifies non-tuple Mapping keys (frozenset/object keys give hash-seed-dependent canonical JSON)
   EVIDENCE: docs/superpowers/plans/2026-10-23-compliance-gate-execution-ledger.md:123 (the text above, verbatim)
   IMPACT: model.jsonable key stringification.
* [ledger L124: ACCEPT] Task 6: minor (deferred): "|".join tuple keys not injective across mappings (needs a "|" in a venue/symbol; plan-mandated A.5.1)
   EVIDENCE: docs/superpowers/plans/2026-10-23-compliance-gate-execution-ledger.md:124 (the text above, verbatim)
   IMPACT: Plan-mandated A.5.1; needs a '|' in a venue or symbol, which the vocabularies and _SYMBOL (rules.py:383) forbid.
* [ledger L125: ACCEPT] Task 6: minor (deferred): seal_context keeps the caller's dicts (mutation after sealing keeps is_sealed True with a stale ctx_hash; Task 13's load_context freezes copies)
   EVIDENCE: docs/superpowers/plans/2026-10-23-compliance-gate-execution-ledger.md:125 (the text above, verbatim)
   IMPACT: load_context freezes copies (owner.py:908-910 `_frozen`).
* [ledger L126: FOLLOWUP-tests] Task 6: minor (deferred): no explicit jsonable(MappingProxyType) test; fixture-defaults test checks only part of A.5.4
   EVIDENCE: docs/superpowers/plans/2026-10-23-compliance-gate-execution-ledger.md:126 (the text above, verbatim)
   IMPACT: Test gap only.
* [ledger L132: ACCEPT] Task 7: minor (deferred): exit on a vocabulary venue with no venue facts (e.g. held BTC on binance) is malformed: venue with no close-manually guidance
   EVIDENCE: docs/superpowers/plans/2026-10-23-compliance-gate-execution-ledger.md:132 (the text above, verbatim)
   IMPACT: Fail closed (malformed).
* [ledger L133: FIXED (final wave)] Task 7: minor (deferred): conduct rows keyed on an ETP class never fire and the loader does not refuse them (ponytail-marked)
   EVIDENCE: docs/superpowers/plans/2026-10-23-compliance-gate-execution-ledger.md:133 (the text above, verbatim)
   IMPACT: rules.py:460-462 refuses a conduct row keyed on an ETP class.
* [ledger L134: NOTE] Task 7: minor (deferred): report said "Deviations: None" despite the trailer change (superseded by the attribution ruling)
   EVIDENCE: docs/superpowers/plans/2026-10-23-compliance-gate-execution-ledger.md:134 (the text above, verbatim)
   IMPACT: Superseded by the attribution ruling.
* [ledger L136: ACCEPT] Task 7: minor (deferred): a cash sell that classifies as new_exposure (settlement symbol or non-settlement counter) can still be looked up in history_maps — unreachable with the shipped venue markets
   EVIDENCE: docs/superpowers/plans/2026-10-23-compliance-gate-execution-ledger.md:136 (the text above, verbatim)
   IMPACT: Unreachable with the shipped venue markets.
* [ledger L138: ACCEPT] Task 7: minor (deferred): a domestic-destination transfer that fails the withdraw test can still carry a superseded instrument into new_exposure (step 6 then needs the same registered address + credited network, so it blocks); under a broken log a credit sell gets the snapshot's state_hash
   EVIDENCE: docs/superpowers/plans/2026-10-23-compliance-gate-execution-ledger.md:138 (the text above, verbatim)
   IMPACT: Step 6 still blocks; fail closed.
* [ledger L143: EXEC (carried, line 239)] Task 8: minor (deferred): per-session ack accepted with session_id None (needs Task 12 never to produce None; defence: require a non-empty str)
   EVIDENCE: docs/superpowers/plans/2026-10-23-compliance-gate-execution-ledger.md:143 (the text above, verbatim)
   IMPACT: "ack accepted with session None and gate never reads ctx.session.armed".
* [ledger L144: ACCEPT/EXEC] Task 8: minor (deferred): derived destination buy keeps the source intent's asset/multiple (asset-keyed rows, asset floor, P4 read the source); no shipped path
   EVIDENCE: docs/superpowers/plans/2026-10-23-compliance-gate-execution-ledger.md:144 (the text above, verbatim)
   IMPACT: No shipped path.
* [ledger L145: FIXED (final wave)] Task 8: minor (deferred): missing exposure entry counts as held 0 even with holdings on that venue
   EVIDENCE: docs/superpowers/plans/2026-10-23-compliance-gate-execution-ledger.md:145 (the text above, verbatim)
   IMPACT: gate.py:328-330 reports holdings on a grey venue without an exposure entry as "state: positions invalid (exposure)".
* [ledger L146: FOLLOWUP-loader] Task 8: minor (deferred): loader allows {cap} in non-grey warnings, so "the share you set" text could be ack-signed on a non-grey per_session row
   EVIDENCE: docs/superpowers/plans/2026-10-23-compliance-gate-execution-ledger.md:146 (the text above, verbatim)
   IMPACT: WARNING_SLOTS = frozenset({"cap"}) (rules.py:76) is allowed in every warning; only a grey row is required to carry it (rules.py:484-485).
* [ledger L147: ACCEPT] Task 8: minor (deferred): address/tag rule duplicated in _dest_check and _credited
   EVIDENCE: docs/superpowers/plans/2026-10-23-compliance-gate-execution-ledger.md:147 (the text above, verbatim)
   IMPACT: Refactor only.
* [ledger L148: ACCEPT] Task 8: minor (deferred): test_no_snapshot_means_manual_exits is a Task 7 regression pin in the Task 8 block
   EVIDENCE: docs/superpowers/plans/2026-10-23-compliance-gate-execution-ledger.md:148 (the text above, verbatim)
   IMPACT: Test placement.
* [ledger L150: EXEC] Task 8: minor (deferred): _transfer carries the transfer's reservation_id into the synthetic destination buy, so a destination reservation with the same id is excluded (assumes globally unique ids)
   EVIDENCE: docs/superpowers/plans/2026-10-23-compliance-gate-execution-ledger.md:150 (the text above, verbatim)
   IMPACT: Globally unique reservation ids belong to execution (P36).
* [ledger L155: EXEC (carried, line 239)] Task 9: minor (deferred): two permits sharing one reservation_id both verify (120k vs a 100k cap); add "a reservation id names exactly one intent, reserved at its notional" to P36 / A.5.2 for the execution spec
   EVIDENCE: docs/superpowers/plans/2026-10-23-compliance-gate-execution-ledger.md:155 (the text above, verbatim)
   IMPACT: "shared reservation_id".
* [ledger L156: EXEC (carried, line 239)] Task 9: minor (deferred): a registered permit edited in place (object.__setattr__) still verifies (P5 discipline; digest-at-issue hardening possible)
   EVIDENCE: docs/superpowers/plans/2026-10-23-compliance-gate-execution-ledger.md:156 (the text above, verbatim)
   IMPACT: "permit edited in place".
* [ledger L157: EXEC] Task 9: minor (deferred): a permit issued with session_id None verifies under any session-less context
   EVIDENCE: docs/superpowers/plans/2026-10-23-compliance-gate-execution-ledger.md:157 (the text above, verbatim)
   IMPACT: Same family as the carried session-None item.
* [ledger L158: FOLLOWUP-tests / ODDS] Task 9: minor (deferred): malformed plans without leg/venue/symbol get decide's malformed: venue/symbol; a leg raising non-AttributeError gives internal error — fail closed, untested
   EVIDENCE: docs/superpowers/plans/2026-10-23-compliance-gate-execution-ledger.md:158 (the text above, verbatim)
   IMPACT: screen() is the odds plan's entry point; fail closed today.
* [ledger L159: FOLLOWUP-tests] Task 9: minor (deferred): _T9_FORBIDDEN lacks random/secrets/uuid and file-metadata names; purity loop could assert every issued permit verifies; gate.py:599 duplicates _choose_state's buy branch
   EVIDENCE: docs/superpowers/plans/2026-10-23-compliance-gate-execution-ledger.md:159 (the text above, verbatim)
   IMPACT: Purity test hardening.
* [ledger L161: ACCEPT] Task 9: minor (deferred): purity scan does not read module-level imports of model.py/rules.py (Task 1's clock guard flags `from time import` anywhere in core/compliance, so it is covered there); used["model"]/from_model now dead code in the test
   EVIDENCE: docs/superpowers/plans/2026-10-23-compliance-gate-execution-ledger.md:161 (the text above, verbatim)
   IMPACT: Covered by the Task 1 clock guard.
* [ledger L168: EXEC (carried, line 239)] Task 11: minor (deferred): append_system_entry raises TypeError for an unhashable kind and OSError after a ~10 s Windows lock wait (Task 14 halt writer should expect OSError)
   EVIDENCE: docs/superpowers/plans/2026-10-23-compliance-gate-execution-ledger.md:168 (the text above, verbatim)
   IMPACT: "append_system_entry TypeError/OSError".
* [ledger L169: FOLLOWUP-tests] Task 11: minor (deferred): duplicate keys nested inside data are caught by the hook but untested
   EVIDENCE: docs/superpowers/plans/2026-10-23-compliance-gate-execution-ledger.md:169 (the text above, verbatim)
   IMPACT: Test gap only.
* [ledger L170: EXEC (carried, line 239)] Task 11: design note for final review / GPT check: P20 lets the holder of a retired key rewrite history from the rotation point while keeping the first fingerprint; only anchors catch it (a padded forged log defeats the "#seq went down" residual)
   EVIDENCE: docs/superpowers/plans/2026-10-23-compliance-gate-execution-ledger.md:170 (the text above, verbatim)
   IMPACT: "P20 retired-key history rewrite".
* [ledger L172: ACCEPT] Task 11: minor (deferred): unknown-OID test may pass vacuously if cryptography maps it to ValueError rather than UnsupportedAlgorithm (fix handles both); non-ASCII digit literals in tests (style)
   EVIDENCE: docs/superpowers/plans/2026-10-23-compliance-gate-execution-ledger.md:172 (the text above, verbatim)
   IMPACT: The fix handles both exception types (owner.py:268).
* [ledger L178: FOLLOWUP-owner (low)] Task 12: minor (deferred): owner_state never checks date against now_utc (Task 13 derives both from one now); malformed now_utc compared as a string
   EVIDENCE: docs/superpowers/plans/2026-10-23-compliance-gate-execution-ledger.md:178 (the text above, verbatim)
   IMPACT: owner_state (owner.py:464) takes date and now_utc separately; load_context derives both from one now (owner.py:973-974).
* [ledger L179: ACCEPT/FOLLOWUP (low)] Task 12: minor (deferred): owner_state does not catch ArithmeticError (10**400 via hand-built LogCheck; verify_log refuses such data); in_force/history/code_approval raise KeyError on malformed hand-built entries
   EVIDENCE: docs/superpowers/plans/2026-10-23-compliance-gate-execution-ledger.md:179 (the text above, verbatim)
   IMPACT: owner.py:477 catches (KeyError, TypeError, ValueError, rules.Invalid), not ArithmeticError; verify_log refuses such data first.
* [ledger L180: FOLLOWUP-tests] Task 12: minor (deferred): BROKEN path tested only via ValueError; no disarm-then-re-arm-on-the-loosening-date test
   EVIDENCE: docs/superpowers/plans/2026-10-23-compliance-gate-execution-ledger.md:180 (the text above, verbatim)
   IMPACT: Test gap only.
* [ledger L183: FIXED] Task 12: fix 2 752ad9d (owner 41/50, 9 PENDING); concern: future-stamped session_armed ignored (neither arms nor blocks) — left per round-1 ruling
   EVIDENCE: docs/superpowers/plans/2026-10-23-compliance-gate-execution-ledger.md:183 (the text above, verbatim)
   IMPACT: Resolved by the line 185 ruling; owner.py:510-519 `blocking` takes every session_armed whatever its stamp.
* [ledger L186: ACCEPT] Task 12: minor (deferred): tests/compliance_owner.py:923 is a ~180-character line (collapsed continuation)
   EVIDENCE: docs/superpowers/plans/2026-10-23-compliance-gate-execution-ledger.md:186 (the text above, verbatim)
   IMPACT: Cosmetic.
* [ledger L188: PARKED (H2) + EXEC carry] Task 12: parked — a halt stamped ahead (system clock past Seoul midnight) with no later line stamped on/before the loosening's date lets a same-date loosening through after the halt (H2) — Ruling: accept and document for the final review and GPT's check; bounding the halt date by the latest stamp before it would revoke loosenings that were in force before the halt when no line sits between them (over-block); needs a clock skew past midnight — cost if wrong: under that skew a loosening survives a halt written the same Seoul day
   EVIDENCE: docs/superpowers/plans/2026-10-23-compliance-gate-execution-ledger.md:188 (the text above, verbatim)
   IMPACT: See section H2/T2.
* [ledger L189: PARKED (T2)] Task 12: parked — a backdated loosening that is the first line of its day counts at once (T2): needs the owner's key and a backdated signer clock; no outside time anchor in the log — Ruling: known limit of round 1's dating, documented — cost if wrong: one loosening a day early
   EVIDENCE: docs/superpowers/plans/2026-10-23-compliance-gate-execution-ledger.md:189 (the text above, verbatim)
   IMPACT: See section H2/T2.
* [ledger L190: FIXED] Task 12: note for Task 13: owner_state takes date and now_utc separately; load_context must derive both from one now (date = Asia/Seoul date of now)
   EVIDENCE: docs/superpowers/plans/2026-10-23-compliance-gate-execution-ledger.md:190 (the text above, verbatim)
   IMPACT: owner.py:973-974 derive now_utc and day from one `now`.
* [ledger L191: NOTE] Task 12: complete (commits c745819..0ca84ac, review clean after 3 fix rounds, 2 parked)
   EVIDENCE: docs/superpowers/plans/2026-10-23-compliance-gate-execution-ledger.md:191 (the text above, verbatim)
   IMPACT: Task 12 closed with 2 parked.
* [ledger L196: ACCEPT] Task 10: minor (deferred): pin test checks the dist metadata location, not cryptography.__file__; docstring claims coverage of UnsupportedAlgorithm it does not import
   EVIDENCE: docs/superpowers/plans/2026-10-23-compliance-gate-execution-ledger.md:196 (the text above, verbatim)
   IMPACT: The current docstring (guards:493-496) no longer claims UnsupportedAlgorithm.
* [ledger L202: FOLLOWUP-owner (low)] Task 13: minor (deferred): huge int in positions raises OverflowError in _amount (fail closed, but reason "internal error" and real owner state lost)
   EVIDENCE: docs/superpowers/plans/2026-10-23-compliance-gate-execution-ledger.md:202 (the text above, verbatim)
   IMPACT: owner.py:875 `math.isfinite(value)` raises OverflowError on a huge int; load_context's except (owner.py:979) turns it into "internal error" (fail closed).
* [ledger L203: FOLLOWUP-owner (low)] Task 13: minor (deferred): positions validated on one read and copied on another (a non-dict Mapping could differ)
   EVIDENCE: docs/superpowers/plans/2026-10-23-compliance-gate-execution-ledger.md:203 (the text above, verbatim)
   IMPACT: Validated in _positions_problem (owner.py:890-905), copied later (owner.py:1009-1013).
* [ledger L204: FOLLOWUP-owner] Task 13: minor (deferred): a forged unsigned snapshot file can make superseded rules decide exits under a broken log (exits only; within spec 6.4 honest limits); possible cross-check against in_force at its seq
   EVIDENCE: docs/superpowers/plans/2026-10-23-compliance-gate-execution-ledger.md:204 (the text above, verbatim)
   IMPACT: latest_snapshot (owner.py:836-860) trusts any intact snapshot file; a cross-check against in_force at its seq is the suggested hardening.
* [ledger L205: ACCEPT] Task 13: minor (deferred): store_put can report success on a calendar folder with an extra file while store_get returns None (fail closed); repeated imports in owner.py
   EVIDENCE: docs/superpowers/plans/2026-10-23-compliance-gate-execution-ledger.md:205 (the text above, verbatim)
   IMPACT: Fail closed; cosmetic imports.
* [ledger L206: FIXED] Task 13: fix 1 4968bd4; note for Tasks 14/15: owner._calendar_stream is gone — use rules.calendar_stream (briefs 14:21,:488; 15:15,:789)
   EVIDENCE: docs/superpowers/plans/2026-10-23-compliance-gate-execution-ledger.md:206 (the text above, verbatim)
   IMPACT: rules.calendar_stream exists (rules.py:721).
* [ledger L208: FOLLOWUP-owner+signer] Task 13: minor (deferred): a rebound guard name escapes the closure scan (`typing = SimpleNamespace(TYPE_CHECKING=True)`, `__name__ = "__main__"`); one-line hardening: require _binds(tree,"typing")==1 / _binds(tree,"__name__")==0 — Task 15's signer copy must match whatever owner.py does
   EVIDENCE: docs/superpowers/plans/2026-10-23-compliance-gate-execution-ledger.md:208 (the text above, verbatim)
   IMPACT: owner.py:699-724 `_typing_flag`/`_skipped`; the signer copy (tools/signer/sign.py:622-650) must change in lockstep (tests/compliance_signer.py:630-634 and :670-671 compare them).
* [ledger L209: FOLLOWUP-owner (low)] Task 13: minor (deferred): store_dir() outside the try in store_get; a NUL byte in a calendar file name/content framing; UnicodeEncodeError on a lone-surrogate filename not caught; cosmetic long docstring lines
   EVIDENCE: docs/superpowers/plans/2026-10-23-compliance-gate-execution-ledger.md:209 (the text above, verbatim)
   IMPACT: owner.py:675 computes `store_dir()` before the `try:` at :676.
* [ledger L215: EXEC (carried, line 239)] Task 14: minor (deferred): after a legitimate rotation, any other exit-3 cause leads with KEY CHANGED in due() (brief accepts "alerts more")
   EVIDENCE: docs/superpowers/plans/2026-10-23-compliance-gate-execution-ledger.md:215 (the text above, verbatim)
   IMPACT: "KEY CHANGED after rotation in due()".
* [ledger L216: FOLLOWUP-alerts (low)] Task 14: minor (deferred): an unhashable item in an alerts.jsonl row or an unreadable alerts.jsonl kills the send line (Task 16 fallback still sends)
   EVIDENCE: docs/superpowers/plans/2026-10-23-compliance-gate-execution-ledger.md:216 (the text above, verbatim)
   IMPACT: alerts._sent (alerts.py:103-116) and owner._alert_rows (owner.py:340-347).
* [ledger L217: EXEC (carried, line 239)] Task 14: minor (deferred): a torn alerts.jsonl line (disk full mid-write) makes the owner log BROKEN until hand-edited; truncate-back on exception would cover it
   EVIDENCE: docs/superpowers/plans/2026-10-23-compliance-gate-execution-ledger.md:217 (the text above, verbatim)
   IMPACT: "torn alerts.jsonl / owner.jsonl last line repair".
* [ledger L218: FOLLOWUP-alerts (low)] Task 14: minor (deferred): a stdout write failure exits 1, not 4 (alerts cross-check catches it)
   EVIDENCE: docs/superpowers/plans/2026-10-23-compliance-gate-execution-ledger.md:218 (the text above, verbatim)
   IMPACT: Cross-checked by the alerts job.
* [ledger L219: FOLLOWUP-alerts] Task 14: minor (deferred): first recorded fingerprint can come from an unverified key (exit-3 summary); consider recording only from code 0-2 summaries (P20-level)
   EVIDENCE: docs/superpowers/plans/2026-10-23-compliance-gate-execution-ledger.md:219 (the text above, verbatim)
   IMPACT: alerts.log (alerts.py:242-262) records any summary's fingerprint; recording only from code 0-2 summaries is the suggested hardening (P20-level).
* [ledger L220: PARTLY FIXED] Task 14: minor (deferred): calendar-line adaptations untested; footer prints the current fingerprint, spec says "the first recorded fingerprint ... in every alert email"
   EVIDENCE: docs/superpowers/plans/2026-10-23-compliance-gate-execution-ledger.md:220 (the text above, verbatim)
   IMPACT: The footer prints both fingerprints (alerts.py:193-203); the calendar-line adaptations are still untested.
* [ledger L222: NOTE] Task 14: note for Task 16: the daily prompt must log push and email (only those rows suppress a repeat)
   EVIDENCE: docs/superpowers/plans/2026-10-23-compliance-gate-execution-ledger.md:222 (the text above, verbatim)
   IMPACT: The daily prompt must log push and email.
* [ledger L230: FOLLOWUP-signer] Task 15: minor (deferred): signer state_root lacks the root-is-link refusal/A0 scan and checks within=state_root() (gate is stricter and fails closed)
   EVIDENCE: docs/superpowers/plans/2026-10-23-compliance-gate-execution-ledger.md:230 (the text above, verbatim)
   IMPACT: Signer state_root lacks the A0 root-is-link refusal; the gate is stricter.
* [ledger L231: FOLLOWUP-signer (low)] Task 15: minor (deferred): keygen edge cases (junction check after prompts; pem write failure leaves a key without pem; --key X.pem collides); non-BMP passphrase chars fail late; main() lets RecursionError/KeyboardInterrupt escape and argparse usage errors share exit 2 with refusals; no --help refusal test; report counting inaccuracies
   EVIDENCE: docs/superpowers/plans/2026-10-23-compliance-gate-execution-ledger.md:231 (the text above, verbatim)
   IMPACT: Edge cases in keygen and main().
* [ledger L233: FOLLOWUP-signer] Task 15: minor (deferred): ancestor walk returns False when a parent pid has exited; rotation help does not say the log reads BROKEN between steps 3 and 4; fingerprint needs the pem beside the key file; keygen weak-passphrase text does not mention blanks/capitals
   EVIDENCE: docs/superpowers/plans/2026-10-23-compliance-gate-execution-ledger.md:233 (the text above, verbatim)
   IMPACT: tools/signer/sign.py:758-767 `_has_claude_ancestor` returns False when the walk reaches a pid missing from the table (a parent that exited): a refusal check that fails open. The rotation-help part is FIXED (line 238).
* [ledger L238: FIXED (final wave)] Final: Ruling: fix wave includes Important #1 (loader: non-blocking rows must name action and financing and class or asset; a gated row needs at least one requirement; conduct rows keyed on an ETP class refused) and Important #2 (exit fallback via history maps on explicit-market venues: close-long tests the counter is a settlement asset instead of is_market; a retired-coin withdrawal or an exit that still cannot be classified gets the manual advice; test rebuilt through approved_state), plus the cheap fail-closed or owner-facing minors the reviewer marked "worth doing now": exit-3 alert/--check wording (exits are manual under a broken log or with no snapshot), cap text f"{cap*100:g}%", grey new exposure refuses notional_krw <= 0 and holdings on a grey venue without an exposure entry, pyproject requires-python >=3.12, signer rotation help (BROKEN window between steps 3-4; write the new fingerprint on paper), alert footer prints both the current and the first recorded fingerprint, test_no_http_verb_calls docstring made true (+ pydoc/timeit/code/cProfile in DYNAMIC_MODULES) — the rest is carried to the execution spec or accepted per the reviewer's triage — cost if wrong: a slightly wider change set in one reviewed wave
   EVIDENCE: docs/superpowers/plans/2026-10-23-compliance-gate-execution-ledger.md:238 (the text above, verbatim)
   IMPACT: What the final fix wave did; "the rest is carried to the execution spec or accepted".
* [ledger L239: EXEC (carried)] Final: carried to the execution spec: ack accepted with session None and gate never reads ctx.session.armed; shared reservation_id; permit edited in place; append_system_entry TypeError/OSError; torn alerts.jsonl / owner.jsonl last line repair; KEY CHANGED after rotation in due(); KIS token burnt on refusal; system entry stamped far ahead blocks signer stamps; signer signs acks as bare hashes; P20 retired-key history rewrite; H2 halt-dating before execution writes system_halt
   EVIDENCE: docs/superpowers/plans/2026-10-23-compliance-gate-execution-ledger.md:239 (the text above, verbatim)
   IMPACT: Verbatim carry list; see section Execution.
* [ledger L242: PARKED -> FOLLOWUP-guards] Final: parked — xml.dom (incl. xml.dom.xmlbuilder DOMBuilder.parseURI / DOMEntityResolver) and profile/pdb/bdb/trace are not in the import bans — Ruling: park as a small guards follow-up; nothing in core/ imports xml or these modules and the T-RO-01/test_08/09 scans plus review cover current code — cost if wrong: a future core/compliance file could fetch a URL through xml.dom without tripping the guard
   EVIDENCE: docs/superpowers/plans/2026-10-23-compliance-gate-execution-ledger.md:242 (the text above, verbatim)
   IMPACT: See section Guards.
* [ledger L243: PARKED -> FOLLOWUP-loader] Final: parked — D15 is enforced only by row content: an explicit `financing: [cash, margin]` or `action: [..., lend, sell_short]` on an allow row still loads VALID (D16 has a loader check, D15 does not) — Ruling: park as loader hardening for the next table change; the shipped table is cash-only and every change needs the owner's signature — cost if wrong: a signed table that widens an allow row would be honoured
   EVIDENCE: docs/superpowers/plans/2026-10-23-compliance-gate-execution-ledger.md:243 (the text above, verbatim)
   IMPACT: See section D15.
* [ledger L244: ODDS + EXEC (carried)] Final: carried — odds plan must not send a zero stake to screen() (it now reports malformed: notional_krw); execution spec must derive notional and held_krw from live prices (P19)
   EVIDENCE: docs/superpowers/plans/2026-10-23-compliance-gate-execution-ledger.md:244 (the text above, verbatim)
   IMPACT: gate.py:65 refuses a new-exposure notional_krw <= 0 as "malformed: notional_krw".

## Open questions

1. H2 is both "parked" (ledger:188, accept and document) and "carried to the execution spec" (ledger:239). Does the follow-up plan attempt a fold-side H2 fix (with the over-block that flips tests/compliance_owner.py:959), or leave H2 to the execution writer that has a trusted clock?
2. T2: does the owner want the alerts.jsonl time bound (a contract change to owner_state, A.8.3), or keep T2 as the documented limit the ledger ruled?
3. D16 by content (an allow row with sell_short or a D16 class that does not cite D16 loads VALID): add it beside D15, or keep D16 label-only as the spec words it ("Every row citing D16")?
4. D15 site: loader only (the ledger's choice), or loader plus a `_floor_new` D15 floor (stricter, but it changes exact-reason tests at tests/compliance_gate.py:587-592)?
5. pickle/_pickle/shelve/marshal in DYNAMIC_MODULES also binds core/odds: does the odds bars cache (spec:136 "own sha-manifest cache") need any of them? If yes, put them in NETWORK_MODULES-style compliance-only scope instead.
6. Should the broader importlib rule ("any importlib import except importlib.metadata") replace the two named entries, given importlib.metadata's own EntryPoint.load string import stays open?
7. Ancestor junctions of the state root (ledger:86, OneDrive reparse points): in or out of the follow-up?
8. Ordering: should the follow-up land before the odds plan (so the owner signs the code hash once after both), and before or after GPT's 2026-10-30 check, which may add findings?
9. Which plan edits the brittle registration literal (tests/compliance_guards.py:488-489) when the odds suite is registered?
10. The ledger's "reviewer's triage" (ledger:238) is not in the repo; were any deferred minors explicitly accepted there that this map classifies as FOLLOWUP?
