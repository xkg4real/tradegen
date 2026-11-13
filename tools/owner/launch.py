"""Owner-only preparation and a process-local command interface.

    python -m tools.owner.launch setup-account --state STATE.json --reviewed-head HASH --state-root ROOT --head-root HEAD_ROOT
    python -m tools.owner.launch setup-history --window WINDOW.json --state-root ROOT --head-root HEAD_ROOT
    python -m tools.owner.launch setup-history --window WINDOW.json --protocol PROTOCOL.json --history-storage POLICY.json --state-root ROOT --head-root HEAD_ROOT
    python -m tools.owner.launch export-driver --profile PROFILE.json --program PROGRAM.json --protocol PROTOCOL.json --window WINDOW.json --state-root ROOT --head-root HEAD_ROOT
    python -m tools.owner.launch export-manifest --repo REPOSITORY

The explicit state root must match TRADEGEN_HOME. Setup is one-time initialization,
not recovery or adoption of an existing chain. A reviewed anchor digest is an
operator input; matching its bytes does not authenticate the underlying account.
Keep exported driver identities/manifests in private files. No command signs,
activates a session, loads credentials, or constructs a live venue transport.

OwnerRuntime/serve retain the actual Coordinator and PreparedSession in one
process. They are the command boundary for a reviewed local launcher; they do not
accept import paths, code snippets or serialized replacements for runtime objects.
The current shipped coordinator supports rehearsal only because production
continuous held-position completeness has not yet been established.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import re
import sys
from threading import Lock, Thread
from typing import Callable

from core.isolation import state_root
from execution_accounts.baseline import restore_state
from execution_accounts.baseline_store import CheckpointStore
from execution_control.store import GENESIS
from execution_launch.baseline_head import BaselineHead, BaselineHeadError, CheckpointChain
from execution_launch.coordinator import Coordinator, compose_driver, history_head_name, read_history_storage
from execution_launch.deployment import export_manifest
from execution_launch.driver import DeploymentWindow
from execution_launch.live_history import HistoryChain
from execution_launch.history_storage import HistoryStoragePolicy, policy_digest
from execution_launch.strategy import ForwardProtocol, parse_protocol, protocol_json
from execution_launch.workflow import MAX_CONFIG_BYTES, read_file

_CODE = re.compile(r"[A-Z][A-Z0-9_]{0,95}")
_HASH = re.compile(r"[0-9a-f]{64}")
_MAX_COMMAND = 4096
_FIXED_ERROR_MODULES = frozenset({__name__, "execution_launch.coordinator", "execution_launch.deployment",
    "execution_launch.workflow", "execution_launch.profile", "execution_launch.driver",
    "execution_launch.live_history", "execution_launch.baseline_head", "execution_launch.instrument_refresh",
    "execution_accounts.baseline", "execution_accounts.baseline_store", "execution_accounts.instrument_terms",
    "execution_launch.history_storage", "execution_launch.strategy"})


class OwnerOperationError(ValueError):
    """Fixed diagnostic codes only."""


def _require(ok, code):
    if not ok:
        raise OwnerOperationError(code)


def _code(exc):
    value = str(exc)
    return value if (isinstance(exc, ValueError) and type(exc).__module__ in _FIXED_ERROR_MODULES
                     and _CODE.fullmatch(value)) else "OWNER_OPERATION_REFUSED"


def _aware(value):
    return type(value) is datetime and value.utcoffset() is not None


def _time(value):
    try:
        out = datetime.fromisoformat(value)
        _require(_aware(out), "OWNER_TIME_REQUIRED")
        return out
    except (ValueError, TypeError, OverflowError):
        raise OwnerOperationError("OWNER_TIME_REQUIRED") from None


def _object(raw):
    def pairs(rows):
        result = {}
        for key, value in rows:
            _require(key not in result, "OWNER_JSON_DUPLICATE_KEY")
            result[key] = value
        return result

    def invalid(_):
        raise OwnerOperationError("OWNER_JSON_INVALID")
    try:
        result = json.loads(raw, object_pairs_hook=pairs, parse_float=invalid, parse_constant=invalid)
        _require(type(result) is dict, "OWNER_JSON_INVALID")
        return result
    except OwnerOperationError:
        raise
    except (ValueError, TypeError, UnicodeError, RecursionError):
        raise OwnerOperationError("OWNER_JSON_INVALID") from None


def read_window(path: str) -> DeploymentWindow:
    body = _object(read_file(path, MAX_CONFIG_BYTES))
    _require(set(body) == {"deployment_id", "start", "end"}, "OWNER_WINDOW_SCHEMA_INVALID")
    _require(type(body["deployment_id"]) is str and
             re.fullmatch(r"[A-Za-z][A-Za-z0-9_.:-]{0,95}", body["deployment_id"]),
             "OWNER_WINDOW_SCHEMA_INVALID")
    window = DeploymentWindow(deployment_id=body["deployment_id"], start=_time(body["start"]),
                              end=_time(body["end"]))
    _require(window.start < window.end <= window.start + timedelta(days=1), "OWNER_WINDOW_INVALID")
    return window


def _root(explicit: Path) -> Path:
    _require(isinstance(explicit, Path) and explicit.is_absolute(), "OWNER_EXPLICIT_STATE_ROOT_REQUIRED")
    actual = state_root().absolute()
    _require(actual == explicit, "OWNER_STATE_ROOT_MISMATCH")
    return actual


def _empty_head(head: BaselineHead):
    # A partially created directory is evidence of an interrupted/previous setup.
    # Never infer a clean GENESIS just because its lock or record is missing.
    _require(not head._dir.exists(), "OWNER_EXISTING_HEAD_REFUSED")
    try:
        head.read()
    except BaselineHeadError as exc:
        _require(str(exc) == "HEAD_NOT_INITIALIZED", "OWNER_EXISTING_HEAD_REFUSED")
    else:
        raise OwnerOperationError("OWNER_EXISTING_HEAD_REFUSED")


def setup_account(*, state_path: str, reviewed_head: str, state_directory: Path,
                  head_directory: Path, now: datetime) -> dict:
    """Seed a genuinely reviewed, fresh anchor and its separate head, once.

    Crash between the two writes is deliberately not repaired automatically. A
    pre-existing head or checkpoint is never replaced, even when its bytes match.
    Review/source authenticity is the owner's responsibility at this boundary.
    """
    _require(type(reviewed_head) is str and _HASH.fullmatch(reviewed_head), "OWNER_REVIEWED_HEAD_REQUIRED")
    _require(_aware(now), "OWNER_TIME_REQUIRED")
    root = _root(state_directory)
    state = restore_state(read_file(state_path, MAX_CONFIG_BYTES), expected_head=reviewed_head)
    _require(timedelta(0) <= now - state.asof <= timedelta(seconds=30), "OWNER_ANCHOR_STALE_OR_FUTURE")
    store = CheckpointStore(root=root)
    head = BaselineHead(root=head_directory, name="account-baseline", chain=CheckpointChain(store))
    _empty_head(head)
    store.seed(state, expected_head=reviewed_head)
    head.initialize_reviewed_head(reviewed_head)
    _require(head.read() == reviewed_head, "OWNER_SETUP_READBACK_REFUSED")
    store.load(expected_head=reviewed_head)
    return {"command": "setup-account", "initialized": True, "sequence": state.sequence,
            "reviewed_head": reviewed_head, "source_authenticated": False, "execution_ready": False}


def setup_history(*, window: DeploymentWindow, state_directory: Path,
                  head_directory: Path, now: datetime, protocol: ForwardProtocol | None = None,
                  storage_policy: HistoryStoragePolicy | None = None) -> dict:
    """Initialize only an empty window, with explicit paired protocol/policy for v3.

    Legacy fixed-window callers omit both. This does not bind a driver or adopt
    a journal; the actual history binding later verifies the same policy again.
    """
    _require((protocol is None) == (storage_policy is None), "OWNER_HISTORY_POLICY_PROTOCOL_REQUIRED")
    if protocol is not None:
        _require(type(protocol) is ForwardProtocol, "OWNER_HISTORY_POLICY_PROTOCOL_REQUIRED")
        protocol_json(protocol)  # strict protocol validation, including the supported universe scope
        _require(type(storage_policy) is HistoryStoragePolicy and protocol.history_storage_sha256 is not None
                 and policy_digest(storage_policy) == protocol.history_storage_sha256,
                 "OWNER_HISTORY_STORAGE_MISMATCH")
    _require(type(window) is DeploymentWindow and _aware(now) and _aware(window.start)
             and _aware(window.end) and now < window.start < window.end,
             "OWNER_HISTORY_WINDOW_ALREADY_STARTED_OR_INVALID")
    root = _root(state_directory)
    head = BaselineHead(root=head_directory, name=history_head_name(window),
                        chain=HistoryChain(root=root, window=window, storage_policy=storage_policy))
    _empty_head(head)
    head.initialize_reviewed_head(GENESIS)
    _require(head.read() == GENESIS, "OWNER_SETUP_READBACK_REFUSED")
    return {"command": "setup-history", "initialized": True,
            "history_head_name": history_head_name(window), "execution_ready": False}


@dataclass(frozen=True, kw_only=True)
class PreparationInputs:
    """Actual, current objects from the reviewed planner; never a stored session."""
    selected_plan: object
    inputs: object
    selection_seed_hex: str
    expires_at: datetime | None = None


class OwnerRuntime:
    """Local lifecycle for one actual coordinator, with no authority of its own.

    start() is the only method that starts a worker. prepare() consumes an explicit
    planner callback's current inputs and retains the Coordinator's actual session.
    Control requests remain serialized by the coordinator. This object cannot
    authorize an entry, invent a review, or resume a stopped coordinator.
    """
    def __init__(self, coordinator: Coordinator, *, preparation_provider: Callable | None = None):
        _require(type(coordinator) is Coordinator and
                 (preparation_provider is None or callable(preparation_provider)), "OWNER_RUNTIME_REQUIRED")
        self._coordinator, self._preparation_provider = coordinator, preparation_provider
        self._lock, self._thread, self._failure = Lock(), None, ""

    def _run(self):
        try:
            self._coordinator.run()
        except Exception as exc:
            with self._lock:
                self._failure = _code(exc)
            self._coordinator.stop()

    def status(self) -> dict:
        status = self._coordinator.status()
        with self._lock:
            alive = self._thread is not None and self._thread.is_alive()
            failure = self._failure
        return {"command": "status", "phase": status.phase, "worker_running": alive,
                "strategy_stopped": status.strategy_stopped, "new_entry_blocked": status.new_entry_blocked,
                "account_source": status.account_source, "account_asof":
                    None if status.account_asof is None else status.account_asof.isoformat(),
                "instrument_source": status.instrument_source, "instrument_asof":
                    None if status.instrument_asof is None else status.instrument_asof.isoformat(),
                "published_units": status.published_units, "outstanding_order_count":
                    sum(order.status in ("RESERVED", "DISPATCHING", "ACKNOWLEDGED", "UNKNOWN", "PARTIAL",
                                         "CANCEL_REQUESTED") for order in status.orders),
                "missed_slots": status.missed_slots, "missed_boundaries": status.missed_boundaries,
                "reasons": list(status.reasons), "risk_reasons": list(status.risk_reasons),
                "worker_failure": failure, "execution_ready": False}

    def bootstrap(self) -> dict:
        self._coordinator.bootstrap()
        return {**self.status(), "command": "bootstrap"}

    def prepare(self) -> dict:
        _require(self._preparation_provider is not None, "OWNER_CURRENT_PREPARATION_INPUTS_REQUIRED")
        value = self._preparation_provider()
        _require(type(value) is PreparationInputs, "OWNER_CURRENT_PREPARATION_INPUTS_REQUIRED")
        prepared = self._coordinator.prepare(selected_plan=value.selected_plan, inputs=value.inputs,
            selection_seed_hex=value.selection_seed_hex, expires_at=value.expires_at)
        return {"command": "prepare", "session_id": prepared.session_id,
                "prepared_at": prepared.prepared_at.isoformat(), "expires_at": prepared.expires_at.isoformat(),
                "record_digest": prepared.record_digest, "owner_activation_performed": False,
                "execution_ready": False}

    def start(self) -> dict:
        with self._lock:
            _require(self._thread is None, "OWNER_RUNTIME_ALREADY_STARTED")
            self._thread = Thread(target=self._run, name="tradegen-owner-coordinator", daemon=False)
            self._thread.start()
        return {**self.status(), "command": "run"}

    def stop(self) -> dict:
        self._coordinator.stop()
        return {**self.status(), "command": "stop", "venue_orders_cancelled": False}

    def refresh_terms(self) -> dict:
        asof = self._coordinator.refresh_instrument_rules()
        return {"command": "refresh-terms", "instrument_asof": asof.isoformat(), "execution_ready": False}

    def disarm(self, *, timeout: float = 1.0) -> dict:
        return {"command": "disarm", **asdict(self._coordinator.disarm(timeout=timeout)), "execution_ready": False}

    def close(self, *, timeout: float = 1.0) -> dict:
        _require(type(timeout) in (int, float) and 0 <= timeout <= 5, "OWNER_CLOSE_TIMEOUT_INVALID")
        closed = self._coordinator.close(timeout=timeout)
        return {**self.status(), "command": "close", "closed": closed, "venue_orders_cancelled": False}

    def command(self, name: str) -> dict:
        _require(type(name) is str and name in {"status", "bootstrap", "prepare", "run", "stop", "disarm", "close",
                                              "refresh-terms"},
                 "OWNER_COMMAND_INVALID")
        methods = {"status": self.status, "bootstrap": self.bootstrap, "prepare": self.prepare,
                   "run": self.start, "stop": self.stop, "disarm": self.disarm, "close": self.close,
                   "refresh-terms": self.refresh_terms}
        return methods[name]()


def serve(runtime: OwnerRuntime, *, stream, emit: Callable[[dict], None]) -> None:
    """Bounded line commands for an already reviewed local launcher; EOF closes it.

    The caller owns the input/output streams. No socket, import, shell command,
    credential prompt or serialized PreparedSession is accepted.
    """
    _require(type(runtime) is OwnerRuntime and callable(getattr(stream, "readline", None)) and callable(emit),
             "OWNER_CONSOLE_REQUIRED")
    try:
        while True:
            line = stream.readline(_MAX_COMMAND + 1)
            if not line:
                break
            try:
                _require(type(line) is str and len(line) <= _MAX_COMMAND, "OWNER_COMMAND_TOO_LARGE")
                name = line.strip()
                emit(runtime.command(name))
                if name == "close":
                    break
            except Exception as exc:
                emit({"command": "refused", "execution_ready": False, "reasons": [_code(exc)]})
                if len(line) > _MAX_COMMAND:
                    break
    finally:
        emit({**runtime.close(timeout=1.0), "command": "console-exit"})


def _arguments(argv):
    _require(type(argv) in (list, tuple) and all(type(v) is str for v in argv), "OWNER_ARGUMENTS_INVALID")
    if tuple(argv) in ((), ("--help",), ("-h",)):
        return "help", {}
    required = {
        "setup-account": {"state", "reviewed-head", "state-root", "head-root"},
        "setup-history": {"window", "state-root", "head-root"},
        "export-driver": {"profile", "program", "protocol", "window", "state-root", "head-root"},
        "export-manifest": {"repo"},
    }
    optional = {"setup-history": {"protocol", "history-storage"}, "export-driver": {"history-storage"}}
    command, *rest = argv
    _require(command in required and len(rest) % 2 == 0, "OWNER_ARGUMENTS_INVALID")
    allowed = required[command] | optional.get(command, set())
    values = {}
    for index in range(0, len(rest), 2):
        key, value = rest[index:index+2]
        _require(key.startswith("--") and key[2:] in allowed and key[2:] not in values
                 and value and not value.startswith("--"), "OWNER_ARGUMENTS_INVALID")
        values[key[2:]] = value
    _require(required[command] <= set(values), "OWNER_ARGUMENTS_REQUIRED")
    if command == "setup-history":
        _require(("protocol" in values) == ("history-storage" in values), "OWNER_HISTORY_POLICY_PROTOCOL_REQUIRED")
    return command, values


def main(argv=None) -> int:
    try:
        command, args = _arguments(sys.argv[1:] if argv is None else argv)
        if command == "help":
            print(__doc__)
            return 0
        if command == "export-manifest":
            report = export_manifest(repo_root=Path(args["repo"]))
        else:
            root = _root(Path(args["state-root"]))
            head_root = Path(args["head-root"])
            if command == "setup-account":
                report = setup_account(state_path=args["state"], reviewed_head=args["reviewed-head"],
                    state_directory=root, head_directory=head_root, now=datetime.now(timezone.utc))
            else:
                window = read_window(args["window"])
                if command == "setup-history":
                    protocol = (parse_protocol(read_file(args["protocol"], MAX_CONFIG_BYTES))
                                if "protocol" in args else None)
                    storage_policy = (read_history_storage(protocol, args["history-storage"])
                                      if protocol is not None else None)
                    report = setup_history(window=window, state_directory=root, head_directory=head_root,
                        now=datetime.now(timezone.utc), protocol=protocol, storage_policy=storage_policy)
                else:
                    prepared = compose_driver(profile_path=args["profile"], program_path=args["program"],
                        protocol_path=args["protocol"], window=window,
                        clock=lambda: datetime.now(timezone.utc), head_root=head_root,
                        history_storage_path=args.get("history-storage"))
                    # Exact identity schema consumed by the detached review signer.
                    report = asdict(prepared.identity)
        print(json.dumps(report, sort_keys=True, ensure_ascii=True))
        return 0
    except Exception as exc:
        print(json.dumps({"execution_ready": False, "reasons": [_code(exc)]}, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
