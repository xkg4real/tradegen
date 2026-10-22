# code_skills_workflows — map of `core/skills/*`, `main.py`, launchers, and the workflow engine

Scope read completely: `core/skills/*.py` (12 files, 2,575 lines), `main.py` (248), `.claude/launch.json` (23), `.claude/run_web.py` (13), `config.py` (347), `ui/workflows_page.py` (698), `ui/runs_page.py` (123), `ui/skills_page.py` (426), `ui/param_form.py` (310), `ui/components.py` (159), `tests/run_all.py`, `tests/acceptance.py`, `tests/flet_api_guard.py`. Spec cross-references are to `QUANTGEN_MACRO_INTEGRATION.md` ("SPEC Lnnn"). Code references are `file:Lnnn`.

Verified at runtime on this machine (2026-10-05): Python 3.13.14, flet 0.85.2, PyYAML 6.0.3; catalogue = 72 skills (ready 34, needs_input 31, missing_key 1, doc_only 6), 11 workflows, 67 steps, 30 decision gates (10 "closed", 20 "open").

## 0. Headline findings (read first)

1. **There is no workflow runner in `core/`.** `core/skills/workflows.py` only *parses* YAML into frozen dataclasses. The step sequencer, gate logic, artifact hand-off and decision persistence live in a closure inside `ui/workflows_page.py::_pipeline` (L213-688) and need a live `ft.Page`. Nothing can run a workflow headless, at app start, on a schedule, or from a test.
2. **Workflow YAMLs and skill scripts are not in the QUANTGEN repo.** They live in an external repository at `config.skills_root()` = env `NEXTGEN_SKILLS_ROOT` or `~/Downloads/claude-trading-skills-main/claude-trading-skills-main` (`config.py:L50-58`): `<root>/skills-index.yaml`, `<root>/workflows/*.yaml`, `<root>/skills/<skill_id>/scripts/*.py`. SPEC L1192 ("YAML pipelines with decision gates exist in core/skills/workflows") is wrong about the location.
3. **`core/skills/workflows` is a module (`workflows.py`), not a directory.** SPEC's proposed path `core/skills/workflows/macro_daily.yaml` (L848, L1189, L917, L959, L3481, L6370; TASK-M8-01) needs a new directory beside that module. Verified on Python 3.13: a directory `workflows/` **without** `__init__.py` leaves `import core.skills.workflows` resolving to `workflows.py`; **with** `__init__.py` it shadows the module and breaks every importer (`ui/workflows_page.py:L47`, `core/skills/__init__.py:L10`, 7 import sites in `tests/acceptance.py`).
4. **The existing parser cannot read the SPEC §3.9 YAML.** Fed the SPEC YAML verbatim, `all_workflows(root)` returns `()` (no `id` key → `_workflow` returns `None`, `workflows.py:L138`). With `id` added: the three `gate:` entries are dropped (`_step` requires `skill`, L98), all nine remaining steps get `step=0`, `decision_gates == ()`. `macro.*` ids are not in `skills-index.yaml`, so `test_05_workflow_steps_reference_real_skills` would fail if the file were placed where the loader looks.
5. **"Decision gate" means two different things.** Existing: a *human* pause (`decision_gate: true` + `decision_question`; operator clicks an answer). SPEC §3.9: an *automatic* check (`gate: data_ok | bounds_ok | verdict_filter`) with fail-closed/HALT side effects. They share a word, not a mechanism.
6. **A "skill" is a subprocess CLI script.** `run_skill` launches `python <script> <argv>` in a fresh run directory with env-only credentials. SPEC "skills" `macro.pit_snapshot` … `macro.run_record` are in-process functions over shared state (pinned `knowledge_utc`, per-book counters). They do not fit the subprocess model.
7. **No scheduler, no app-start hook, no alert store, no run log exists.** The only background loop is `EngineRuntime._loop` (armed only). `main.main(page)` runs once per Flet session (once per browser tab in web mode).
8. **The QUANTGEN directory is not a git repository** (`git rev-parse` fails). SPEC requires `git_hash` in every run record and artifact (L1238, L3508, L5312).

## A. File-by-file

### A.1 `config.py` (paths, env, credentials) — the parts this subsystem uses

| Symbol | Line | Value / behaviour |
|---|---|---|
| `_clean(name) -> str` | L33-40 | `os.getenv`, strip; strips one pair of matching quotes; returns `""` for `<placeholder>` values |
| `_present(name) -> bool` | L43-44 | `bool(_clean(name))` |
| `_DEFAULT_SKILLS_ROOT` | L50-52 | `Path.home()/"Downloads"/"claude-trading-skills-main"/"claude-trading-skills-main"` |
| `skills_root() -> Path` | L55-58 | env `NEXTGEN_SKILLS_ROOT` else default |
| `skills_root_valid(root=None) -> bool` | L61-63 | `<root>/skills-index.yaml` is a file and `<root>/skills` is a dir |
| `skill_python() -> str` | L67-69 | env `NEXTGEN_SKILL_PYTHON` else `sys.executable` |
| `SKILL_TIMEOUT_SECONDS: float` | L72 | env `NEXTGEN_SKILL_TIMEOUT` else `300`; evaluated at import (a non-numeric value raises `ValueError` at import → app does not start) |
| `runs_dir() -> Path` | L75-77 | env `NEXTGEN_RUNS_DIR` else `~/.nextgen/runs` |
| `SKILL_CREDENTIALS: dict[str, tuple[str, ...]]` | L84-89 | `{"fmp": ("FMP_API_KEY",), "finviz": ("FINVIZ_API_KEY",), "alpaca": ("ALPACA_API_KEY","ALPACA_SECRET_KEY"), "fxmacrodata": ("FXMACRODATA_API_KEY",)}` |
| `KEYLESS_INTEGRATIONS: frozenset` | L92-95 | `{"local_calculation","public_csv","coingecko","binance_funding","yfinance","websearch"}` |
| `FILE_INPUT_INTEGRATIONS: frozenset` | L98-101 | `{"prices_json","user_input","chart_image","mt5_local_files","news_events_json","catalyst_events_json","profiles_json"}` |
| `skill_credential_present(integration_id) -> bool` | L104-108 | all env vars of that integration present; unknown id → `False` |
| `skill_env() -> dict[str,str]` | L111-123 | `dict(os.environ)` + cleaned provider keys + `setdefault("PYTHONIOENCODING","utf-8")`, `setdefault("PYTHONUTF8","1")` |
| `trading_dir() -> Path` | L236-238 | env `NEXTGEN_TRADING_DIR` else `~/.nextgen/trading` (`rules.json`, `engine.json`) |
| `ficc_cache_dir() -> Path` | L334-336 | env `NEXTGEN_FICC_CACHE` else `~/.nextgen/ficc_cache` |
| `skill_provider_status() -> list[dict]` | L212-228 | presence-only rows `{id,label,ready,vars,note}` |

`load_dotenv()` runs at import (L26-30). No macro artifact directory exists yet (SPEC L797, L4126: "gains the macro artifact directory (proposed)").

### A.2 `core/skills/__init__.py`

Re-exports (L4-19): `Entrypoint, skill_entrypoints (alias of entrypoints.entrypoints), is_runnable, primary, Integration, SkillMeta, all_skills, by_id (= index.by_id), categories, Readiness, State, evaluate, summarize, RunHandle, RunResult, Status, describe_args, run_skill, RunRecord, latest_for_skill, recent, record, Step, WorkflowMeta, all_workflows`.
`reload_all() -> None` (L22-29): calls `index.reload()`, `workflows.reload()`, `entrypoints.reload()`, `readiness.reload()` (NOT `params.reload()`; `params` is keyed on mtime+size so it self-invalidates).
The function `entrypoints` is deliberately exported as `skill_entrypoints` so it does not shadow the submodule (L2-3).

### A.3 `core/skills/workflows.py` — YAML parser only

Loader: `<root>/workflows/*.yaml`, sorted by filename, `yaml.safe_load`, `encoding="utf-8"`.

```python
@dataclass(frozen=True)
class Step:            # L33-43
    step: int; name: str; skill: str
    optional: bool = False
    consumes: tuple[str, ...] = (); produces: tuple[str, ...] = ()
    decision_gate: bool = False; decision_question: str = ""; name_ja: str = ""

@dataclass(frozen=True)
class Artifact:        # L46-51
    id: str; produced_by_step: Optional[int] = None
    required: bool = True; downstream_hints: tuple[str, ...] = ()

@dataclass(frozen=True)
class WorkflowMeta:    # L54-82
    id: str; display_name: str; cadence: str = ""; estimated_minutes: Optional[int] = None
    difficulty: str = ""; api_profile: str = ""; when_to_run: str = ""; when_not_to_run: str = ""
    required_skills: tuple[str, ...] = (); optional_skills: tuple[str, ...] = ()
    steps: tuple[Step, ...] = (); artifacts: tuple[Artifact, ...] = ()
    manual_review: tuple[str, ...] = (); journal_destination: str = ""; source: Optional[Path] = None
    @property skill_ids -> tuple[str, ...]        # ordered unique step.skill
    @property decision_gates -> tuple[Step, ...]  # steps with decision_gate True
```

Public API: `all_workflows(root: Path | None = None) -> tuple[WorkflowMeta, ...]` (L178); `by_id(workflow_id, root=None) -> Optional[WorkflowMeta]` (L182); `reload() -> None` (L189). `_load` is `@lru_cache(maxsize=4)` keyed on `str(root)` (L165).

Parsing rules (binding for anything that reuses this loader):
- File skipped silently (`None`) when: YAML error, top level not a dict, or no `id` (L134-139).
- Step skipped silently when not a dict or no `skill` key (L98). `step` → `int(raw.get("step") or 0)`, non-int → 0 (L100-103). Steps sorted by `step` (stable) (L157).
- `name` falls back to the skill id (L106). `_clean` collapses all whitespace runs to one space (L93-94) — folded `>-` scalars become one line.
- `estimated_minutes` non-int → `None`. `required` defaults `True`. `_tup` accepts str or list.
- Missing `workflows/` directory → `()`.

Observed YAML shape (11 files in `<root>/workflows/`; key → count):
- top: `schema_version, id, display_name, display_name_ja, cadence, estimated_minutes, target_users, difficulty, api_profile, when_to_run(_ja), when_not_to_run(_ja), required_skills, optional_skills, artifacts, steps, manual_review(_ja), journal_destination` (all 11); `prerequisite_workflows` (4), `manual_inputs` (1), `final_outputs` (1).
- step: `step, name, name_ja, skill, produces, decision_gate` (67/67); `consumes` (44); `decision_question(_ja)` (30); `optional` (22); `depends_on` (7).
- artifact: `id, produced_by_step, required` (77/77); `downstream_hints` (23); `schema_id` (6).
- **Parsed but ignored by the parser:** `schema_version, display_name_ja, target_users, *_ja (except name_ja), prerequisite_workflows, manual_inputs, final_outputs, step.depends_on, artifact.schema_id`.
- Enumerations seen: `cadence ∈ {daily, weekly, monthly, ad-hoc}`; `api_profile ∈ {no-api-basic, fmp-required, mixed}`; `difficulty ∈ {beginner, intermediate, advanced}`.
- **Step kinds: exactly one** — "run skill `<id>`". Modifiers: `optional`, `decision_gate`. There is no `gate:` step, no `run:`/command step, no condition, no loop, no schedule field that anything executes (`cadence` is display text).

### A.4 `core/skills/index.py` — `skills-index.yaml` → typed metadata

```python
@dataclass(frozen=True) class Integration: id: str; type: str = ""; requirement: str = "required"; note: str = ""   # L24-33
    @property blocking -> bool      # requirement == "required"
@dataclass(frozen=True) class SkillMeta:   # L36-59
    id; display_name; category=""; status=""; summary=""; timeframe=""; difficulty=""
    integrations: tuple[Integration, ...] = (); inputs=(); outputs=(); workflows=()
    @property directory -> Path     # config.skills_root()/"skills"/id   (re-read each call)
    @property skill_md -> Path      # directory/"SKILL.md"
    def integration_ids() -> tuple[str, ...]
```
`requirement` values in the index: `required | recommended | optional | not_required`. `status`: `production | beta`.
API: `all_skills(root=None) -> tuple[SkillMeta, ...]` (sorted by `display_name.casefold()`), `by_id(skill_id, root=None) -> Optional[SkillMeta]`, `categories(root=None) -> tuple[str, ...]` (sorted), `reload()`. `_load` `@lru_cache(maxsize=4)`. Any read/parse failure → `()` (L106-111). Index top-level keys: `schema_version, categories, skills`; per-skill keys ignored by the parser: `verification`, `knowledge_only`.

### A.5 `core/skills/entrypoints.py` — which script to run

`_PRIMARY: dict[str,str]` (L29-45), 15 curated entries (e.g. `"trading-skills-navigator": "recommend.py"`, `"canslim-screener": "screen_canslim.py"`).
`@dataclass(frozen=True) class Entrypoint: skill_id: str; path: Path; primary: bool = False`; props `name` (= `path.name`), `label` (stem with `_`→space).
Resolution (L89-110): candidates = `scripts/*.py` not starting with `_` or `test_`, containing a `__main__` guard and (`"argparse"` or `"sys.argv"`) in the text; preferred = `_PRIMARY[skill_id]` if present, else `scripts/<skill_id with - → _>.py`, else the single candidate; otherwise **no primary**.
API: `entrypoints(skill_id, skill_dir) -> tuple[Entrypoint, ...]` (primary first), `primary(skill_id, skill_dir) -> Optional[Entrypoint]`, `is_runnable(skill_id, skill_dir) -> bool`, `reload()`. `_candidates` `@lru_cache(maxsize=256)` keyed on the scripts dir string.

### A.6 `core/skills/params.py` — static argparse reader (`ast`, never executes the script)

```python
class Kind(str, Enum): TEXT="text"; NUMBER="number"; INTEGER="integer"; FILE="file"; DIR="dir"; CHOICE="choice"; FLAG="flag"
@dataclass(frozen=True) class Param:       # L63-95
    dest: str; flags: tuple[str, ...] = (); kind: Kind = Kind.TEXT; required: bool = False
    default: Optional[str] = None; choices: tuple[str, ...] = (); help: str = ""; nargs: Optional[str] = None
    group: Optional[str] = None; subcommand: Optional[str] = None; order: int = 0
    props: positional, flag (long flag preferred), label, wants_path
@dataclass(frozen=True) class MutexGroup: id: str; required: bool; members: tuple[str, ...] = ()
@dataclass(frozen=True) class Spec:        # L105-205
    script=""; params=(); groups=(); subcommands=(); subcommand_dest=""; subcommand_required=False; parsed=False; note=""
    for_subcommand(sub=None) -> tuple[Param, ...]
    required_params(sub=None) -> tuple[Param, ...]
    group_for(param) -> Optional[MutexGroup]
    takes_arguments: bool; needs_arguments: bool
    missing(values: dict|None = None, sub=None) -> tuple[str, ...]      # displayable names of unmet requirements
    build_argv(values: dict|None = None, sub=None) -> tuple[str, ...]   # subcommand, positionals in declaration order, then flags
```
`spec_for(path: Path) -> Spec` (L432): cached on `(path, mtime, size)` (`lru_cache(512)`); missing file → `Spec(parsed=False, note="script not found")`; unreadable → `note="could not read the script (<Exc>)"`; nothing found → `note="no argparse definition could be read from this script"`. `reload()`.
Kind inference (L230-246): `store_true/false` → FLAG; `choices` → CHOICE; name contains any of `_DIR_HINTS = ("dir","directory","folder","root")` → DIR; `type=Path` or any of `_FILE_HINTS = ("-file","_file","-json","_json","-csv","_csv","-path","_path","-yaml","_yaml","input","output")` → FILE; `int`/`float` type names → INTEGER/NUMBER; else TEXT. FLAG values emitted when text ∈ `("1","true","yes","on")`.

### A.7 `core/skills/readiness.py`

```python
class State(str, Enum): READY="ready"; MISSING_KEY="missing_key"; NEEDS_INPUT="needs_input"; DOC_ONLY="doc_only"
@dataclass(frozen=True) class Readiness:   # L76-111
    state: State; missing_credentials=(); missing_providers=(); input_integrations=(); warnings=()
    undeclared=(); required_arguments=(); arguments_unknown: bool = False
    props: reason (one line), runnable (READY or NEEDS_INPUT), blocked (MISSING_KEY or DOC_ONLY)
```
`evaluate(skill: SkillMeta) -> Readiness` (L130-206): no primary → `DOC_ONLY`; three passes (declared integrations; env vars found in script text but not declared; argparse requirements via `spec_for(primary).missing()`); precedence `MISSING_KEY` > `NEEDS_INPUT` > `READY`. Unknown integration id is treated as satisfied (L121-125). Only `requirement == "required"` blocks; others produce a `warnings` string. `summarize(skills) -> dict[State,int]`; `reload()`. Not cached per skill: each call re-evaluates (env reads are live).

### A.8 `core/skills/runner.py` — subprocess execution

```python
class Status(str):   # NOT an Enum; plain str class constants  (L79-85)
    RUNNING="running"; OK="ok"; FAILED="failed"; TIMEOUT="timeout"; CANCELLED="cancelled"; ERROR="error"

@dataclass                     # mutable; the only non-frozen dataclass in core/skills
class RunResult:               # L88-141
    run_id: str; skill_id: str; entrypoint: str; argv: tuple[str, ...]; status: str
    exit_code: Optional[int]; started_at: str; finished_at: str; duration_s: float; run_dir: Path
    stdout: str = ""; stderr: str = ""; artifacts: tuple[Path, ...] = (); error: str = ""
    diagnosis: Optional[Diagnosis] = None
    props: ok (status == "ok"), cause (Cause; UNKNOWN when diagnosis is None), headline (never the bare exit code)
    to_record() -> dict   # keys: run_id, skill_id, entrypoint, argv(list), status, exit_code, started_at, finished_at,
                          #       duration_s(round 3), run_dir(str), artifacts([basename only]), error, cause(value), headline

class RunHandle:  cancelled: bool (property); cancel() -> None      # L144-166; kills the process tree

def run_skill(entrypoint: Entrypoint, args: Sequence[str] = (), *, on_line: Optional[Callable[[str], None]] = None,
              timeout_s: Optional[float] = None, handle: Optional[RunHandle] = None) -> RunResult      # L206-313, blocking
def describe_args(entrypoint: Entrypoint, *, timeout_s: float = 20) -> str                              # L323-336, runs `--help`
```
Conventions:
- `run_id = f"{UTC %Y%m%d-%H%M%S}-{skill_id}-{uuid4().hex[:6]}"`; `run_dir = config.runs_dir()/run_id` created eagerly (L188-193).
- `argv = (config.skill_python(), str(entrypoint.path), *args)`; `cwd = run_dir`; `env = config.skill_env()`; stdout+stderr merged, `encoding="utf-8", errors="replace"`, line-buffered (L241-251).
- First two transcript lines are the runner's own: `$ <shlex.join(argv[1:])>` and `# cwd=<run_dir>` (L233-234).
- Timestamps: `datetime.now(timezone.utc).isoformat(timespec="seconds")` → `2026-08-20T23:59:26+00:00` (offset form, **not** the `Z` suffix SPEC L3507 requires).
- Timeout: `timeout_s or config.SKILL_TIMEOUT_SECONDS` (so `0` means default); on expiry `_kill` (`taskkill /F /T /PID` on Windows, `terminate()` elsewhere), `status="timeout"`, `error="exceeded {timeout_s:.0f}s timeout"`.
- Status resolution (L285-290): cancelled → `"cancelled"` / `"cancelled by operator"`; else non-zero exit → `"failed"` / `"exit code N"`.
- Artifacts: every file under `run_dir` (recursive) with suffix in `_ARTIFACT_SUFFIXES = {".json",".md",".csv",".html",".yaml",".yml",".txt",".png"}` except `transcript.log` and `run.json` (L42, L196-203). **`.jsonl` is not an artifact suffix.**
- `transcript.log` is written by `run_skill` (L316-320); `run.json` is written only by `runs.record`.
- `on_line` fires on the reader thread `skillrun-<run_id>`; exceptions inside it are swallowed.
- Redaction (`_redact`, L72-76) applied to every stored/shown line: exact match of each configured `SKILL_CREDENTIALS` value (≥ 8 chars) → `abcd…yz`; then `\b[A-Za-z0-9]{32,}\b` → masked. **Verified: an md5 or sha256 hex digest is masked** (`data_snapshot_id=d41d…7e`).
- Failure mode "could not start" (L252-261): returns `RunResult(status="error", exit_code=None, error="<Exc>: <msg>")` with **`diagnosis=None`, no `transcript.log`, `artifacts=()`**. `run_skill` never raises for process-level failures.

### A.9 `core/skills/diagnose.py` — transcript → one sentence

```python
class Cause(str, Enum):   # L28-41
    OK="ok"; NO_RESULTS="no_results"; MISSING_ARGS="missing_args"; INVALID_ARG="invalid_arg"; MISSING_INPUT="missing_input"
    MISSING_KEY="missing_key"; PLAN_LIMIT="plan_limit"; RATE_LIMIT="rate_limit"; NETWORK="network"; TIMEOUT="timeout"
    CANCELLED="cancelled"; CRASH="crash"; UNKNOWN="unknown"
@dataclass(frozen=True) class Diagnosis:  cause: Cause; headline: str; detail: str = ""; fields: tuple[str, ...] = (); excerpt: tuple[str, ...] = ()
    props: actionable (MISSING_ARGS | INVALID_ARG | MISSING_INPUT), benign (OK | NO_RESULTS)
def diagnose(*, status: str, exit_code: Optional[int], stdout: str, error: str = "") -> Diagnosis   # never raises
```
Order of checks (L176-345): cancelled → timeout → error(CRASH) → argparse "required" → exit 2 → **clean exit (exit 0, or `None` with status ok) is OK/NO_RESULTS before any transcript scan** → last traceback exception (non-provider) → 402 / 429 / missing key / legacy endpoint → self-reported demand / usage block → missing path → network → no results → CRASH → UNKNOWN. Substring tests `"402" in blob` / `"429" in blob` are unanchored (any number containing those digits on a failed run classifies as PLAN_LIMIT / RATE_LIMIT). `_REMEDY` texts are operator-facing strings (L46-57), e.g. TIMEOUT → `"Raise NEXTGEN_SKILL_TIMEOUT or narrow the run's scope."`.

### A.10 `core/skills/runs.py` — file-backed run history

```python
@dataclass(frozen=True) class RunRecord:   # L22-46
    run_id; skill_id; entrypoint; status; exit_code: Optional[int]; started_at; finished_at; duration_s: float
    run_dir: Path; artifacts: tuple[str, ...]; error: str = ""; workflow_id: str = ""
    props/methods: ok (status == "ok"), transcript() -> str   # "(transcript unavailable)" on any read error
def record(result: RunResult, *, workflow_id: str = "") -> RunRecord   # writes <run_dir>/run.json (indent 2, ensure_ascii=False); write errors swallowed
def recent(limit: int = 100) -> tuple[RunRecord, ...]                   # newest first = reverse lexical order of directory names
def by_id(run_id: str) -> Optional[RunRecord]
def latest_for_skill(skill_id: str) -> Optional[RunRecord]              # scans recent(limit=250)
```
`run.json` on disk = `RunResult.to_record()` + `workflow_id` (so it also carries `argv`, `cause`, `headline`, which `RunRecord` drops). There is **no index file, no workflow-level record and no workflow run id**: a workflow run is N unrelated run directories that share only the string `workflow_id`. `recent()` re-lists and sorts the whole runs directory on every call and skips directories without `run.json`.

### A.11 `core/skills/decisions.py` — answers read out of `decision_question`

`MAX_OPTIONS = 6`. `@dataclass(frozen=True) class Option: value: str` (+ `label`: unchanged if upper-case, else first letter capitalised). `@dataclass(frozen=True) class Choice: question: str; options: tuple[Option, ...] = (); source: str = ""` (`"vocabulary" | "enumeration" | ""`), props `closed` (`len(options) >= 2`), `values`.
`options_for(question: str) -> Choice` (L197-216): empty → `Choice("")`; **no `?` → no options** (imperatives are never turned into buttons); else token vocabulary (`A / B / C` machine tokens, swept across the sentence) then trailing prose enumeration (`A, B, or C?`, rejected when preceded by a determiner). Governing rule (L15-21): every option is a verbatim slice of the question; an open question gets a free-text answer. YAML has no `decision_options` key.

### A.12 `core/skills/insights.py` — report JSON → drawable summary

`MAX_FACTS = 8`, `MAX_COMPONENTS = 12`.
`@dataclass(frozen=True) class Component: key; label; score: float; weight: float = 0.0; signal: str = ""`; `band` = `"success"` if score ≥ 70, `"accent"` if ≥ 40, else `"error"` (**0–100 scale**).
`@dataclass(frozen=True) class Insight: skill_id=""; source: Optional[Path]=None; score: Optional[float]=None; zone=""; guidance=""; components=(); warnings=(); facts: tuple[tuple[str,str], ...]=(); quality=""; lines=()`; props `empty`, `band` (`"muted"` when score is None), `headline`.
API: `read(path, *, skill_id="") -> Optional[Insight]`; `from_transcript(text, *, skill_id="", limit=6) -> Insight`; `digest(result) -> Insight` (duck-typed: `skill_id, artifacts, diagnosis, stdout`).
Report convention read: `composite.composite_score | composite_score`, `composite.zone | zone`, `composite.exposure_guidance | exposure_guidance`, `composite.data_quality.label`, `composite.component_scores | component_scores` (value = number or `{score,label,weight}`), `components[key].signal`, `composite.active_warnings[] (label|flag)`; top-level scalars become `facts` unless the key matches `_SKIP_FACT` (L34-40: `url|uri|path|dir|file|schema|version|generated|timestamp|_at$|^id$|api_key|_key$|elapsed|runtime|^composite_score|^zone|^exposure_guidance`, case-insensitive `search`). `*_pct` numeric facts get a `%` suffix. Absent stays absent (score `None` ≠ 0). `digest` picks the newest `.json` artifact whose name has no `history` and is not `run.json`; falls back to the diagnosis sentence for a non-benign failure, then to the transcript tail.

### A.13 `core/skills/wiring.py` — hand earlier artifacts to later steps

`match(spec: Spec, produced: Mapping[str, Path], *, consumes: tuple[str, ...] = (), subcommand: Optional[str] = None) -> dict[str, str]` (dest → path). Only `Kind.FILE` flag parameters (`_ACCEPTS_PATH = (Kind.FILE,)`); score = shared non-generic tokens between the param name and the artifact id (`_GENERIC` L35-39); zero score or a tie → left blank.
`produced_by(step_produces: tuple[str, ...], artifacts: tuple[Path, ...]) -> dict[str, Path]` (artifact id → file): `.json` files only (no `history`, not `run.json`); 1 declared + 1 file → direct; otherwise best unambiguous token match; unmatched dropped.

### A.14 `ui/workflows_page.py` — the de-facto workflow engine (Flet closure)

`build_workflows_page(page: ft.Page, *, on_open_settings: Optional[Callable] = None, on_open_skill: Optional[Callable] = None) -> ft.Control`.
Per-workflow state dict (L215-229): `index, handle, running, awaiting_gate, awaiting_input, form, gate_run_button, gate_blocker, args{step→{values,argv}}, insights{step→Insight}, results{step→RunResult}, produced{artifact_id→Path}, decisions{step→answer}, collapsed:set`. In memory only; rebuilt whenever a workflow card is (re)selected.

Sequencer (pseudo-code of L406-487, L552-674):
```
start():      clear console, gate, insights, results, produced, decisions, collapsed   # NOT args
              run_from(0)
run_from(i):  if i >= len(steps): finish("workflow complete","success"); return
              meta = index.by_id(step.skill); entry = primary(...) if meta else None
              if entry is None:  log "# step N (skill) has no runnable script — skipping"; advance_after(step,i); return
              verdict = evaluate(meta)
              if not verdict.runnable:
                  if step.optional: log skip; advance_after(step,i); return
                  finish(f"step {N} blocked: {verdict.state.value}","error"); return
              spec = spec_for(entry.path); prefill = wiring.match(spec, produced, consumes=step.consumes)
              if state.args has step:            launch(step,i,entry, remembered["argv"]); return
              if spec.needs_arguments or not spec.parsed or prefill:  show_input_gate(...); return   # operator fills/approves a form
              launch(step,i,entry,())
launch():     handle = RunHandle(); page.run_thread(worker)
worker():     result = runner.run_skill(entry, argv, on_line=log, handle=handle)
              runs.record(result, workflow_id=wf.id)
              results[N] = result; insights[N] = insights.digest(result) if not empty
              produced.update(wiring.produced_by(step.produces, result.artifacts))
              if result.status != "ok" and not result.diagnosis.benign and not step.optional:
                  finish(f"step {N}: {result.headline}","error"); return
              advance_after(step,i)
advance_after(step,i):  show_gate(step,i) if step.decision_gate else run_from(i+1)
show_gate():  running=False; awaiting_gate=True; index=i+1; choice = options_for(step.decision_question)
              evidence = steps producing step.consumes (via artifacts[].produced_by_step, else steps[].produces) + this step
              closed → one button per option (records option.value); open → TextField "Your answer" + "Continue"; always "Stop here"
record_answer(answer): if answer: decisions[N]=answer; log; _persist_decision(); else log "continued without a recorded answer"
              resume(i+1)
cancel_gate(): finish("stopped at decision gate","muted")
stop():       handle.cancel(); finish("cancelled","muted")
```
Decision persistence (`_persist_decision`, L624-646): `<run_dir of that step>/decision_step{N}.json` with keys **`workflow, step, step_name, skill, question, options_offered, answer, answered_at, produces`** (`answered_at` = UTC ISO seconds, `+00:00`). Written only when the step produced a `RunResult` and the answer is non-empty.
Pre-run surface (L117-184): `when_not_to_run` as an error notice before the Run button; `when_to_run`; "Blocked: …" from `coverage(wf)`; steps needing input; gate count; `manual_review` checklist (display-only checkboxes, not interactive). Console keeps the last 400 lines (L307).

### A.15 `ui/runs_page.py`, `ui/skills_page.py`, `ui/param_form.py`, `ui/components.py`

- `build_runs_page(page) -> ft.Control`: `runs.recent(limit=200)` at build; list + detail (run id, entrypoint, workflow, exit code, started, duration, error, artifacts as chips, last 500 transcript lines, "Open run folder" via `os.startfile` on Windows / `xdg-open`). `main.navigate` rebuilds this page on every visit (`main.py:L164`).
- `build_skills_page(page, *, on_open_settings=None, focus_skill="") -> ft.Control`: single-skill run: `ParamForm` → `runner.run_skill(entry, argv, on_line=on_line, handle=handle)` in `page.run_thread` → `runs.record(result)` (no `workflow_id`) → verdict row from `result.diagnosis` (None-safe here). `_CAUSE_TOKEN` / `_ICON_FOR` map `Cause` → palette token / icon (L38-63).
- `ParamForm(page, spec, *, on_change=None, initial=None)`: `.control`, `.subcommand`, `.values()`, `.missing()`, `.argv()` (spec argv + raw box via `shlex.split`), `.preview()`, `.highlight(flags)`. Flet 0.85 helper-text split: `TextField.helper` vs `Dropdown.helper_text` handled by `_set_helper` (L51-61).
- `ui/components.py` atoms (reuse, do not re-style): `STATE_STYLE` (L18-23), `RUN_STATUS_STYLE = {"ok":("Succeeded","success"), "failed":("Failed","error"), "timeout":("Timed out","error"), "cancelled":("Cancelled","muted"), "error":("Could not start","error"), "running":("Running","accent")}` (L25-32), `colour_for(token)`, `chip(text, token="muted", *, tooltip="")`, `readiness_chip(state)`, `run_status_chip(status)` (unknown status → raw text, muted), `section(title, *, subtitle="")`, `card(content, *, on_click=None, col=None, tooltip="")`, `notice(text, token="accent", *, icon=ft.Icons.INFO_OUTLINE, action: Optional[ft.Control] = None)`, `empty_state(title, detail, *, icon, action=None)`, `key_value(label, value, *, width=132)`, `mono(text, *, size=11)`, `stat(label, value, *, token="text", tooltip="")`.

### A.16 `main.py`

- `LOCALE = "en"`; `NAV` (L74-94), 19 `(name, label, icon)` tuples in order: `macro, rates, bonds, fx, structuring, derivatives, etf, crypto, lab, quant, portfolio, signals, trading, rules, workflows, skills, krx, runs, settings`.
- `main(page: ft.Page) -> None` (L97-244): dark theme; `gateway = KRXGateway()`; `rule_store = RuleStore()`; `engine = EngineRuntime(rule_store, QuoteFeed(gateway))` (L107-113); `current = {"page": "macro"}`; `cache: dict[str, ft.Control]`.
- `build(name, **kwargs)` (L124-159): FICC-style pages get `(page, on_open_settings=...)`; `workflows` gets `on_open_settings` and `on_open_skill=lambda sid: navigate("skills", focus=sid)`; `runs` gets `(page)`; fallback is Settings with `on_reload=reload_catalogue`.
- `navigate(name, *, focus="", rebuild=False)` (L161-171): **views are built once and cached**; only `runs`, `trading`, and `skills`-with-focus are rebuilt on every visit (L164). `macro` is cached.
- `reload_catalogue()` (L173-176): `reload_all()`, `cache.clear()`, `navigate("settings", rebuild=True)`.
- `page.on_resize = resize` (L236; Flet 0.85 name — `on_resized` is silently ignored; locked by `test_14`). Compact rail below `BREAKPOINTS["compact"]` = 700 px.
- Start-up order: build layout → `resize()` → `navigate("macro")` (L243-244). **No start-up check of any kind, no scheduler, no shutdown hook.** Entry: `ft.run(main, assets_dir="assets")` (L248). `ft.run` also accepts `before_main: Callable[[Page], Any]` (verified signature) — unused today.

### A.17 `.claude/launch.json`, `.claude/run_web.py`

- `launch.json`: `"quantgen-web"` → `python .claude/run_web.py`, `port: 8552`, `autoPort: true`. A second configuration `"godseye-dev"` (`npm run dev --prefix C:/Users/whydi/OneDrive/Desktop/GODSEYE`, port 4173) belongs to an unrelated project; leave it alone.
- `run_web.py`: `sys.path.insert(0, ROOT); os.chdir(ROOT)`; `app = ft.run(main.main, export_asgi_app=True, assets_dir=<ROOT>/assets)`; `uvicorn.run(app, host="127.0.0.1", port=int(os.environ.get("PORT","8552")), log_level="info")`. Dev-only preview launcher. In this mode `main.main(page)` runs **per browser session**, so each tab builds its own `KRXGateway`, `RuleStore` and `EngineRuntime` over the same `~/.nextgen/trading/*.json` files.

## B. Cross-file flows

### B.1 Call graph

```
main.main ─► build_workflows_page ─► workflows.all_workflows ─► config.skills_root()/workflows/*.yaml
                    │                index.by_id ─► config.skills_root()/skills-index.yaml
                    │                entrypoints.primary ─► <root>/skills/<id>/scripts/*.py   (text scan)
                    │                readiness.evaluate ─► config.SKILL_CREDENTIALS, os.environ, params.spec_for
                    │                params.spec_for (ast) ─► wiring.match
                    └─ page.run_thread(worker) ─► runner.run_skill ─► subprocess (cwd = run dir, env = config.skill_env())
                                                   ├─ diagnose.diagnose          └─ writes transcript.log
                                                   runs.record ─► run.json
                                                   insights.digest ─► ui.charts.insight_chart
                                                   wiring.produced_by ─► state["produced"]
                                                   decisions.options_for ─► gate buttons ─► decision_step{N}.json
main.navigate("runs") ─► build_runs_page ─► runs.recent(200) ─► RunRecord.transcript()
main.reload_catalogue ─► core.skills.reload_all
Settings page ─► index.all_skills, readiness.summarize, config.runs_dir(), config.skill_python(), config.SKILL_TIMEOUT_SECONDS
```
Importers of `core.skills` outside the package: `main.py`, `ui/{charts,components,param_form,runs_page,settings_page,skills_page,workflows_page}.py`, `tests/acceptance.py`. Nothing in `core/ficc`, `core/quant`, `core/engine`, `core/rules` or `data/` imports it, and it imports none of them (only `config`).

### B.2 One workflow end to end: `market-regime-daily`

Source: `<skills_root>/workflows/market-regime-daily.yaml` (107 lines). Header: `cadence: daily`, `estimated_minutes: 15`, `difficulty: beginner`, `api_profile: no-api-basic`, `when_not_to_run` = "Do not use this output as a standalone buy/sell signal…", `required_skills: [market-breadth-analyzer, uptrend-analyzer, exposure-coach]`, `optional_skills: [market-top-detector, macro-regime-detector]`, `journal_destination: trader-memory-core`.

| step | skill | optional | consumes | produces | gate |
|---|---|---|---|---|---|
| 1 | `market-breadth-analyzer` | – | – | `market_breadth_report` | false |
| 2 | `uptrend-analyzer` | – | – | `uptrend_report` | false |
| 3 | `market-top-detector` | true | – | `top_risk_report` | false |
| 4 | `exposure-coach` | – | the three reports | `exposure_decision` | **true**: "Given today's breadth, uptrend participation, and top risk, is new swing trade risk allowed, restricted, or cash-priority?" |

Run: Workflows page → card → "Run workflow". Steps 1–3 launch with `()` argv (or pause at an input gate if the script needs arguments). Step 4: `wiring.match` pre-fills `--breadth` and `--uptrend` (and `--top-risk` if step 3 produced a file) with the JSON paths the earlier steps wrote; the operator sees the filled form and presses "Run this step". After step 4 the gate shows the three evidence panels and three buttons `Allowed | Restricted | Cash-priority` (enumeration source), plus "Stop here".
On disk (real example, `~/.nextgen/runs/20260820-235926-exposure-coach-0cc185/`): `transcript.log`, `run.json` (`workflow_id: "market-regime-daily"`, `argv` with the two upstream paths, `artifacts: ["exposure_posture_2026-08-20_235926.json", "exposure_posture_2026-08-20_235926.md"]` — basenames, the files are under `reports/`), `reports/…`, `decision_step4.json` (`options_offered: ["allowed","restricted","cash-priority"]`, `answer: "cash-priority"`). Steps 1–3 each have their own sibling run directory. Nothing links the four except `workflow_id` and adjacent timestamps. `manual_review` and `journal_destination` are display-only.

### B.3 Persistence locations

| Path | Writer | Content |
|---|---|---|
| `~/.nextgen/runs/<run_id>/transcript.log` | `runner._write_transcript` | redacted merged stdout/stderr |
| `~/.nextgen/runs/<run_id>/run.json` | `runs.record` | `to_record()` + `workflow_id` |
| `~/.nextgen/runs/<run_id>/decision_step{N}.json` | `ui/workflows_page._persist_decision` | gate answer |
| `~/.nextgen/runs/<run_id>/**` | the skill script | its own reports (relative to cwd) |
| `~/.nextgen/trading/{rules.json, engine.json, safety.json, practice_checklist.json}` | `core/rules/store`, `core/engine/runtime` | atomic `tempfile.mkstemp` + `os.replace` (`store.py:L226-229`, `runtime.py:L380-384`) |
| `~/.nextgen/ficc_cache/*.json` | `core/ficc/data`, `core/quant/history` | 6 h read-through cache |
| `~/.nextgen/{kis_token.json, dart_corp_codes.json}` | `data/krx/*` (hard-coded `Path.home()`, not via `config`) | token / corp codes |
| `~/.nextgen/{prefs.json, policy_events.jsonl}` | no writer in this repo (left by an earlier build) | — |
| `qa/acceptance_results.json` (repo) | `tests/run_all.py` | test results |

State on this machine: 497 directories under `~/.nextgen/runs`, 154 with `run.json` (workflow_id: 111 none, 32 `market-regime-daily`, 11 `multi-asset-opportunity-daily`), 1 decision file.

### B.4 Env vars read by this subsystem

`NEXTGEN_SKILLS_ROOT`, `NEXTGEN_SKILL_PYTHON`, `NEXTGEN_SKILL_TIMEOUT` (300), `NEXTGEN_RUNS_DIR`, `FMP_API_KEY`, `FINVIZ_API_KEY`, `ALPACA_API_KEY`, `ALPACA_SECRET_KEY`, `FXMACRODATA_API_KEY`; child-only: `PYTHONIOENCODING=utf-8`, `PYTHONUTF8=1`; launcher: `PORT` (8552). `.env.example` documents none of the four `NEXTGEN_SKILL*`/`NEXTGEN_RUNS_DIR` variables (the Settings page template lists `NEXTGEN_SKILLS_ROOT` only).

## C. Tests

Runner: `python tests/run_all.py` → 266 checks (`cockpit` 47, `engine` 89, `ui` 4, `quant` 53, `ficc` 56, `expansion` 17), all PASS in `qa/acceptance_results.json`; ≈155 s total, cockpit ≈12.5 s. A test is a zero-argument function that raises on failure; no pytest fixtures.

Registration of new tests (the only mechanism): create `tests/<name>.py` exposing `tests() -> list[tuple[str, Callable]]` (existing idiom: `sorted((n, v) for n, v in globals().items() if n.startswith("test_") and callable(v))`, or an explicit list as in `expansion_acceptance.py:L306`), then in `tests/run_all.py` add the import (L30-35) and one line in `tests()` (L38-44) with a group prefix. `run_all.py` forces stdout/stderr to UTF-8, writes `qa/acceptance_results.json`, exits 1 on any failure. Hermetic convention used elsewhere: `tests/ficc_acceptance.py::_no_network()` (L30-41) swaps the two socket-opening functions for one that raises and sets `config.FICC_CACHE_TTL_SECONDS = 0`.

`tests/acceptance.py` (group `cockpit/`) — coverage of this subsystem:

| Test | Asserts |
|---|---|
| `test_01_skills_index_parses` | `len(all_skills()) >= 60`, every skill has id and display_name |
| `test_02_workflows_parse` | `len(all_workflows()) >= 8`, every workflow has steps |
| `test_03_…one_primary`, `test_04_curated_primaries_still_exist` | entrypoint resolution; every `_PRIMARY` script exists |
| `test_05_workflow_steps_reference_real_skills` | **every `step.skill` of every loaded workflow is in the skills index** |
| `test_06`, `test_07`, `test_07b` | readiness states; missing key names the env var; undeclared credentials detected from code (uses `importlib.reload(config)`) |
| `test_08_no_broker_order_path` | none of `order_cash, order-cash, place_order, submit_order, TTTC0802U, TTTC0801U, VTTC0802U` in `runtime_py()` (= `core/**`, `data/**`, `ui/**`, `main.py`, `config.py`), case-insensitive raw text |
| `test_09_no_account_credentials_requested` | none of `KIS_ACCOUNT, CANO, ACNT_PRDT_CD` in the same files |
| `test_10`, `test_11` | `_redact` masks a configured key; leaves `market_breadth_2026-08-18_152347.json` intact |
| `test_12_skill_env_never_leaks_into_a_record` | `"env" not in RunResult.to_record()` |
| `test_13` | Settings page source contains no `kis_credentials()`, `opendart_key()`, `_clean(` |
| `test_14`, `test_15` | `page.on_resize =` present in `main.py`; `"cache[name] = build("` present in `main.py` |
| `test_16`, `test_17` | every runtime file is UTF-8; `acceptance.py`/`run_all.py` never call `read_text()` without an encoding |
| `test_18` | no `eodhd` / `quartr` in code |
| `test_19` | real subprocess run of `futures-position-sizer`; `run.json` + `transcript.log` exist; `runs.by_id` finds it |
| `test_20` | bad `NEXTGEN_SKILL_PYTHON` → `status == "error"`, non-empty `error` |
| `test_23`–`test_28` | argparse reading: required flags, mutex groups, subcommand scoping, composed argv accepted by the real parser (subprocess), no READY skill needs arguments, ≤ 4 unparsed scripts |
| `test_29`–`test_31`, `test_43`, `test_44` | `diagnose` classification and headlines (one real subprocess in `test_29`) |
| `test_32` | no `run_skill(x, ())` / `run_skill(x, [])` literal in any `ui/*.py` (AST) |
| `test_33`–`test_36` | every gate option is a verbatim slice of its question; exposure gate offers `["Allowed","Restricted","Cash-priority"]`; four named open questions stay open; checklist / imperative are not options |
| `test_37` | every `consumes` id has a producer |
| `test_38`, `test_39`, `test_46` | `insights.read` shape; missing score is `None`/`"muted"`; a failed step is summarised by its diagnosis |
| `test_40`, `test_41`, `test_45` | `wiring.match`: fills `breadth`/`uptrend`, leaves ties and non-FILE params blank |
| `test_42` | `ui/workflows_page.py` has a function named `show_gate` whose body calls `options_for` and `_digest` (AST) |

`tests/flet_api_guard.py` (group `ui/`, scans **every** `ui/*.py`): `test_page_methods_exist` (every `page.<m>()` call must be a public attribute of `ft.Page`; variable must be literally named `page`), `test_control_keywords_exist` (kwargs of `ft.<Control>(…)` for `_CHECKED_CONTROLS` = `Dropdown, TextField, Button, IconButton, Text, Container, Row, Column, ResponsiveRow, AlertDialog, SnackBar, Icon, Divider, VerticalDivider, AnimatedSwitcher, Image, Checkbox, ExpansionTile, ProgressRing, ProgressBar, FilePicker, ListTile, Switch, Slider, Card, Stack, Tabs, Tab, Badge, Tooltip`), `test_control_attribute_assignments_exist` (`var.attr = …` where `var` was assigned once from `ft.<Control>(…)`), `test_theme_tokens_referenced_by_ui_exist` (`pal.<token>` ∈ `bg, surface, surface_2, border, text, muted, accent, accent_soft, success, error, on_accent`). `ft.Banner` and `ft.DataTable` are not in `_CHECKED_CONTROLS`, so their kwargs are unchecked.

Not hermetic (contrary to README L366-369): the whole `cockpit/` group needs the external skills repository on disk (`test_01`: ≥ 60 skills), and `test_19/20/26/29` spawn real subprocesses and create directories in the real `config.runs_dir()` (four per suite run; three have no `run.json`).

## D. Extension points for v2

### D.1 What SPEC asks of this subsystem (verbatim anchors)

- §3.9 YAML (SPEC L1191-1245): `name: macro_daily`; `runs: [after_close: KRX, after_close: NYSE]`; `run_mode: live` (`live | backtest | replay`, also L4198); ordered entries: `skill: macro.pit_snapshot` → `gate: data_ok` → `skill: macro.lag_audit` → `skill: macro.vol_and_overlays` → `skill: macro.build_artifacts` → `gate: bounds_ok` → `gate: verdict_filter` → `skill: macro.engine_feed` → `skill: macro.forward_books` → `skill: macro.forward_monitor` → `skill: macro.brief` → `skill: macro.run_record`.
- Start bound: "the run starts no earlier than close_print_bound_utc + 10 min (06:40:30Z for KRX today)" (L1194-1195; T-CLOSE-01 workflow clause from M8).
- "Acting steps" = `pit_snapshot` through `verdict_filter` (L1240-1241). An error there "blocks engine_feed for that run: the books carry their weights, build_artifacts writes a fail_closed artifact, and every book the step serves counts a failed decision (book counter +1; OPS HALT run_error at the limit, R-19 rule 4)". `build_artifacts`: "always written, also when a gate failed" (L1221). "A forward_monitor error is re-run for each skipped decision at the next successful run." (L1244-1245).
- Run record (L1237-1240): append `{run_id, market, session_date, decision_utc, knowledge_utc, started_utc, finished_utc, step results with errors, git_hash, config_hash, data_snapshot_id, late}` to `run_log.jsonl`; "a step that raises still writes its record (status = error) and raises RUN_ERROR (page)".
- Missed decisions (L1246-1247): "On app start and at every scheduled run, macro.missed_decisions compares the calendar's expected decisions with run_log.jsonl; each missing decision, and each decision whose run record has status = error in an acting step, raises MISSED_DECISION (severity page) and the books carry their weights (§8.8)."
- `late` (L5311): artifact `generated_at_utc` after the opening of that market's next session; forward books carry previous weights; late artifact is display-only.
- One artifact per decision: "a later run for the same decision is a replay, never a second forward decision" (L1199-1200).
- Alert sinks (L1248-1250): "a Macro-page banner (always; page alerts persist until acknowledged), an OS notification, an optional e-mail skill." Governance events → `governance_events.jsonl` ("append-only, hash-chained; one §6.6 record per line, verified at app start, T-OBS-05"); appender owned by `core/rules` (L4096).
- Alert object (schema inside `macro_state`, L3625-3629): required `alert_id, code, severity, component, first_seen_utc, count`; `severity ∈ {"info","warn","page"}`; optional `series_id, books[], escalated, ack_utc`. Codes named in SPEC for this area: `RUN_ERROR`, `MISSED_DECISION`, `VERDICT_INTEGRITY`, `GOVERNANCE_LOG_BROKEN` (all severity page).
- Tests owned here: T-OBS-02 (skipped scheduled run → MISSED_DECISION at next app start, books carry weights), T-OBS-03 (page alerts persist until acknowledged), T-OBS-04 (exception in each acting step → status = error, RUN_ERROR, engine_feed blocked, counters +1, HALT at limit, counts for MISSED_DECISION; forward_monitor re-evaluated), T-OBS-05 (chain verified at app start; hand-edited row → GOVERNANCE_LOG_BROKEN) (L5677-5681); I-01 (L5688); T-RO-01 static scan "including core/skills scripts and the commands of every workflow YAML" (TASK-M0-01); TASK-M8-01, -05, -06.
- Tech-fund programme (`R3_TF_neural_link.md`, incl. §13 XS-01..22): no item touches the workflow engine, run log, alert sinks or app start. Its screens/weights reach the daily run only through the step functions other subsystems own.

### D.2 Recommended shape (minimum that satisfies D.1)

Do **not** route `macro_daily` through `runner.run_skill` / `ui/workflows_page._pipeline`. Reasons are items 1-6 of §0 plus: transcripts would mask md5 values; state would live in a Flet closure; `test_05` would fail.

Build one small in-process pipeline runner in `core/` with no Flet import:

```python
# proposed new module (one file), e.g. core/skills/pipeline.py
@dataclass(frozen=True) class PipelineStep: kind: str  # "skill" | "gate"
                                            name: str  # "macro.pit_snapshot" | "data_ok"
@dataclass(frozen=True) class Pipeline: name: str; runs: tuple[...]; run_mode: str; steps: tuple[PipelineStep, ...]; source: Path
def load_pipeline(path: Path) -> Pipeline                      # yaml.safe_load, encoding="utf-8"; unknown key or unknown step name -> raise (fail closed)
STEP_REGISTRY: dict[str, Callable[[ctx], None]]                # "macro.*" -> function living in the package SPEC names
GATE_REGISTRY: dict[str, Callable[[ctx], None]]                # "data_ok" | "bounds_ok" | "verdict_filter"
ACTING_STEPS = everything from "macro.pit_snapshot" through "verdict_filter"   # SPEC L1240-1241
def run_pipeline(p: Pipeline, *, market: str, session_date, clock=..., ...) -> dict   # the run record; never raises past run_record
def append_run_record(record: dict, path: Path) -> None        # one JSON line, UTF-8, append
def missed_decisions(expected: Iterable[(market, session_date, decision_utc)], run_log_rows: Iterable[dict]) -> list[...]   # pure
```
Design constraints that follow from the existing code:
- **Registries, not dynamic import.** The YAML names steps; Python maps names to functions. A name with no registry entry must raise at load (the existing parser's "skip silently" behaviour is the wrong default for an acting pipeline).
- **Clock injection** as in `EngineRuntime(clock=…)` (`runtime.py:L68, L84`) so T-OBS-02 / T-CLOSE-01 are hermetic.
- **`run_record` in `finally`.** SPEC needs the record written when a step raises; implement as the runner's own epilogue, with `macro.run_record` listed in YAML for fidelity.
- **Atomic writes** for any rewritten JSON state (alert store) with the existing `tempfile.mkstemp(dir=…, suffix=".tmp")` + `os.replace` idiom. JSONL logs are append-only (open `"a"`, `encoding="utf-8"`, one `json.dumps(..., ensure_ascii=False)` + `"\n"`).
- **Timestamps** must be `…Z` (SPEC L3507). Do not copy `runner.py`'s `isoformat(timespec="seconds")` (`+00:00`).
- **Run id**: the existing format `"%Y%m%d-%H%M%S"-<name>-<6 hex>` (`runner.py:L189-190`) is reusable.
- **Frozen dataclasses + tuples** for all metadata, matching every sibling module; only a result object in flight may be mutable.

YAML location — two workable options (owner/coordinator picks; see Ambiguity 1):
- (a) SPEC path `core/skills/workflows/macro_daily.yaml` as a **data-only directory with no `__init__.py`**, plus one guard test asserting `not (core/skills/workflows/__init__.py).exists()` and `from core.skills.workflows import Step` still works.
- (b) a non-colliding path (e.g. `core/skills/pipelines/macro_daily.yaml`). SPEC marks the path "proposed" at every mention.
Either way the file must not be placed under `<skills_root>/workflows/` (foreign repository; `test_05` would fail; the parser would mangle it).

### D.3 Reuse rather than duplicate

| Need | Already exists — reuse |
|---|---|
| Path / env override helper | `config._clean`, and the `runs_dir()/trading_dir()/ficc_cache_dir()` pattern for the new macro artifact directory |
| Background work from a page | `page.run_thread(worker)` (21 call sites across 17 pages); no other threading idiom in `ui/` |
| Banner, chips, tiles, key/value rows | `ui.components.notice(text, token, icon=…, action=…)`, `chip`, `stat`, `key_value`, `section`, `empty_state` |
| Run status vocabulary on screen | `ui.components.RUN_STATUS_STYLE` / `run_status_chip` |
| Showing macro runs on the Runs page with zero UI change | write `<config.runs_dir()>/<run_id>/run.json` with the `RunRecord` keys (`run_id, skill_id, entrypoint, status, exit_code, started_at, finished_at, duration_s, run_dir, artifacts, error, workflow_id`) and a `transcript.log`; `runs.recent()` will list it. Status must be one of the six `RUN_STATUS_STYLE` keys (note `"error"` is labelled "Could not start") |
| Human decision gates (if any macro step ever needs one) | `decisions.options_for`; the `decision_step{N}.json` key set |
| Read-only scan (T-RO-01) | extend `tests/acceptance.py::test_08` / `test_09` and their helpers `runtime_py()`, `_code_only()`; do not write a second scanner |
| Atomic JSON persistence | `core/rules/store.py:L216-231`, `core/engine/runtime.py:L364-386` |
| Process-tree kill, redaction | `runner._kill`, `runner._redact` (only if a subprocess is ever involved) |

Do not reuse for v2 artifacts: `insights.Component.band` (0–100 thresholds; v2 multipliers are in [0, 1]); `runner._ARTIFACT_SUFFIXES` (no `.jsonl`); `runs.RunRecord` as the macro run record (it has none of `market, session_date, decision_utc, knowledge_utc, git_hash, config_hash, data_snapshot_id, late`).

### D.4 App-start hook, scheduling, alert sinks — where they attach

- **Missed-decision check + governance-chain verification at app start:** inside `main.main(page)` after `engine` is built (L113) and before/after the first `navigate` (L244), run via `page.run_thread` so the first paint is not blocked; or `ft.run(main, before_main=…)`. Must be guarded to run **once per process** (module-level flag/lock): in web mode `main()` runs per session. The check itself is the pure `missed_decisions(...)` above; `main.py` only wires it.
- **Scheduled runs:** nothing exists. Smallest viable: a process-singleton daemon thread using the `EngineRuntime._loop` idiom (`threading.Event.wait(timeout)`), started from the same guarded hook, that fires `run_pipeline` when `now >= close_print_bound_utc + 10 min` for a market with no run-log row for that decision; plus a "Run macro_daily now" button on the Macro page (`page.run_thread`). The app is a desktop app that is often closed at the close — that is exactly the case MISSED_DECISION covers.
- **Macro-page banner:** the Macro view is cached (`main.py:L164-167`), so a banner built at construction never refreshes. Either pass the page a banner host that a callback updates and call it from `navigate("macro")`, or add `"macro"` to the rebuild set (this discards a loaded sheet — worse). Page-severity alerts must survive restarts (T-OBS-03) → a persisted alert store (e.g. `<macro_dir>/alerts.json`, atomic write) with `ack_utc`; banner action = `ft.Button("Acknowledge", …)` via `notice(action=…)`.
- **OS notification:** Flet 0.85.2 exposes no notification API (`dir(ft)` has no `*notif*`), and no notifier package is installed or listed in `requirements.txt`. Implement as a best-effort sink that degrades with a label (banner remains the guaranteed sink).
- **E-mail skill:** none exists; SPEC says "optional". Skip unless the owner asks.
- **New `ui/*.py` code** is linted by the Flet guard automatically: name the page variable `page`, the palette `pal`, use only real `ft.Page` methods (`run_thread`, `show_dialog`, `pop_dialog`, `update`, …) and real control kwargs (`Dropdown(on_select=…)`, `TextField(helper=…)`, `Dropdown(helper_text=…)`).

### D.5 Naming collisions to avoid

| Word | Existing meaning | v2 meaning |
|---|---|---|
| `core.skills.workflows` | parser **module** | SPEC wants a **directory** of the same name |
| "decision gate" / `decision_gate` | human pause with a question | automatic `gate:` check |
| "skill" | external subprocess CLI | in-process `macro.*` function |
| `Artifact` (`workflows.py`) | declared workflow output id | JSON artifacts `macro_state`, `overlay_decision`, … |
| `RunRecord`, `runs.record`, `run.json` | one subprocess run | one `macro_daily` run row in `run_log.jsonl` |
| `decisions` (`core/skills/decisions.py`), engine `Decision` | gate answer options; evaluator verdict | the daily decision per market |
| `by_id` | three functions: `index.by_id` (re-exported as `core.skills.by_id`), `workflows.by_id`, `runs.by_id` | — |
| `insights` | two modules: `core/skills/insights.py`, `core/ficc/insights.py` (and `core/quant/insights.py`) | — |
| `State` (`readiness`), `Status` (`runner`), `EngineMode`/`HaltReason` (`core/engine/state.py`: `DISARMED/ARMED/HALTED`; reasons `operator, stale_data, no_data, provider_error, limit_breach, unknown_state`) | skill readiness; run status; single-engine state | per-book runtime state with `halt.class ∈ {RISK, OPS}` and `reason_code` |
| `Status.ERROR` = "could not start the process" | — | SPEC run-record `status = error` = a step raised |

## E. Gotchas

1. **External dependency for the baseline.** 47 `cockpit/` checks pass only because the skills repository exists at the default path on this machine. A build agent that moves or cannot see `~/Downloads/claude-trading-skills-main/...` loses them; this is unrelated to v2 work and must not be "fixed" by editing tests.
2. **Tests write to the real home directory.** Each `run_all.py` adds 4 directories to `~/.nextgen/runs` (343 of 497 are orphans without `run.json`). `runs.recent()` re-lists and sorts the whole directory on every Skills-detail render (`latest_for_skill` → `recent(250)`) and every Runs visit.
3. **`importlib.reload(config)` in tests** (`test_07b`, `test_10`, `test_20`) re-runs `load_dotenv()` and re-evaluates module constants. Any new module-level constant in `config.py` derived from env is re-read mid-suite; `test_10` pops `FMP_API_KEY` without restoring a pre-existing process value.
4. **Latent defect — workflow UI hangs on a start failure.** `ui/workflows_page.py:L475` evaluates `result.diagnosis.benign`; on the `Status.ERROR` path `diagnosis is None` (`runner.py:L252-261`) → `AttributeError` in the worker thread, chip stays "Running". (`skills_page` is None-safe.)
5. **Latent defect — stale inputs on re-run.** `start()` (L665-674) clears `produced` but not `state["args"]`; a second "Run workflow" in the same detail view relaunches each remembered step with the **previous run's** argv, including upstream report paths from the earlier run (`run_from` L433-436).
6. **Latent defect — Stop does not stop an optional step's successors.** After `stop()`, the worker of a cancelled *optional* step falls through to `advance_after` and launches the next step; for a required step it overwrites the "cancelled" chip with an error chip (L475-479, L659-663).
7. **A gate on a skipped step is not persisted.** `advance_after` still opens the gate when the step was skipped; `_persist_decision` returns silently when there is no `RunResult` (L625-627). "Stop here" and an empty "Continue" also leave no file.
8. **`run.json` artifacts are basenames** (`to_record`, `runner.py:L137`); files under `reports/` cannot be re-located from the record alone.
9. **`RunResult.stderr` is always `""`** (stderr is merged into stdout).
10. **Redaction masks any 32+ alphanumeric run**, so md5/sha256 digests printed to a skill transcript become `abcd…yz`. Artifact files are untouched.
11. **`shlex.join` quoting is POSIX** even on Windows (transcript header shows single-quoted `C:\…` paths); cosmetic, but do not parse it back.
12. **Windows specifics:** `taskkill /F /T` for cancellation/timeout; `os.startfile` for "Open run folder"; cp949 is the default console/file encoding on this machine — every `read_text`/`write_text`/`open` must pass `encoding="utf-8"` (`test_16`, `test_17` enforce it for runtime files and two test files); `run_all.py` reconfigures stdout.
13. **`page.update()` is called from non-UI threads** (`on_line` runs on the `skillrun-*` reader thread, workers on `page.run_thread`), each wrapped in `try/except`. New background code should follow the same guarded pattern.
14. **README drift:** README says "229 checks" (L347) and "245 checks" (L379); actual 266. README says the suite is hermetic (L366-369); the cockpit group is not. `decisions.py` docstring says 24 gates; actual 30. Module docstrings, remedy strings and env names still say NEXTGEN.
15. **`config.SKILL_TIMEOUT_SECONDS` and friends are `float(_clean(...) or default)` at import** — a malformed env value stops the app at import with `ValueError`.
16. **`workflows._load` / `index._load` are `lru_cache`d on the root string**; edits to YAML on disk are invisible until `reload_all()` (Settings → "Reload catalogue").
17. **`.claude/launch.json` carries an unrelated project's configuration** (`godseye-dev`).
18. **`prep/readlines.py` is broken** (the helper named in the task brief): line 4 contains a literal newline inside a string literal → `SyntaxError`. Long spec lines were printed with an inline script instead.

## Ambiguities (source silent or contradictory) and the conservative reading

1. **Workflow file path** — SPEC L848/L1189/L917/L959/L3481/L6370 say `core/skills/workflows/macro_daily.yaml`, L1192 asserts such YAMLs already exist there; in the repo that name is a module and YAMLs are external. *Conservative:* treat the path as "proposed" (SPEC's own word); use a data-only directory with no `__init__.py` plus a guard test, or a non-colliding directory; never the external repository.
2. **YAML schema** — SPEC's `name / runs / run_mode / steps[{skill|gate}]` differs from the existing `id / steps[{step, name, skill, decision_gate, …}]`. *Conservative:* a separate loader that rejects unknown keys and unknown step names; the existing parser and the 11 external workflows stay untouched.
3. **`macro.*` "skills"** — SPEC L917 says "Macro skills"; TASK-M8-06 says "macro.run_record and macro.missed_decisions skills". Nothing says they are subprocess scripts or index entries. *Conservative:* in-process functions in a registry; not added to `skills-index.yaml`; no new CLI surface.
4. **Location of `run_log.jsonl`, `governance_events.jsonl`, `cards/verdicts.jsonl`, `<artifact_dir>`** — SPEC only says `config.py` "gains the macro artifact directory (proposed)" (L797, L4126). No name, default or env var. *Conservative:* one `config.macro_dir()` following the existing pattern (env override, default under `~/.nextgen/`), all logs under it, never under the repo and never inside `runs_dir()`; env-var prefix (`NEXTGEN_` vs `QUANTGEN_`) is an owner choice — existing path overrides all use `NEXTGEN_`.
5. **`git_hash`** — required in run records and artifacts (L1238, L3508); a change between decisions is a governance event (L5312); the repo is not under git. *Conservative:* record an explicit sentinel (e.g. `"unversioned"`) plus a deterministic source-tree hash in `config_hash`-like form; never fabricate a commit id; flag to the owner (verdict-integrity rule (iii) at L3487 cannot be satisfied without real commits → such cards stay in the specification book).
6. **Scheduler semantics** — `runs: [after_close: KRX, after_close: NYSE]` with no statement of what triggers a run when the desktop app is closed, and `data.ingest.retries_min: [1, 5, 15, 60]` / `decision_deadline: next_session_open_minus_30min` (L4201) imply a run that may wait hours. *Conservative:* never block the UI thread; one attempt per invocation, re-invoked by the in-app timer until the deadline; a run not completed before the next session open is `late` (display-only); a decision with no row is MISSED_DECISION; books carry weights in both cases.
7. **Multiple sessions (web mode)** — SPEC assumes one app instance. *Conservative:* process-singleton scheduler and start-up check; at most one run row per (market, session_date) in live mode, later runs are replays (L1199-1200).
8. **OS notification mechanism and e-mail skill** — unspecified; no capability in Flet 0.85.2 or installed packages. *Conservative:* banner + persisted alert store are mandatory; OS notification best-effort with labelled degradation; e-mail not built.
9. **T-RO-01 scope "core/skills scripts and the commands of every workflow YAML"** (TASK-M0-01) — there are no scripts under `core/skills` and workflow YAMLs contain no commands; the scripts are in a foreign repository. *Conservative:* scan the QUANTGEN tree (extend `test_08`/`test_09`) and every pipeline YAML in the repo; report the external repository as out of scope rather than fail on code QUANTGEN does not own.
10. **Run-record `status` vocabulary** — SPEC names only `status = error`. *Conservative:* `ok | error` per step and per run, plus `late: bool`; do not overload `runner.Status` strings beyond what the Runs page already renders.
11. **Whether human gates survive in `macro_daily`** — SPEC title says "decision gates", content defines only automatic gates; owner decisions are "listed" by `macro.brief` (L1236). *Conservative:* no operator click is required for the pipeline to complete; nothing a click does can raise exposure.
12. **JSON Schema validation for `bounds_ok`** — SPEC L3506 requires draft 2020-12 with a `$id` registry; `jsonschema` is not installed and not in `requirements.txt`/`pyproject.toml`. *Conservative:* an acting-field validation failure (including "validator unavailable") fails closed; adding the dependency is an owner-visible change to `requirements.txt` and `pyproject.toml`.
